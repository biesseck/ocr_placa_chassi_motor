from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.inference import PlatePipeline
from app.schemas import PlateResult, PredictResponse

from google.cloud import storage


pipeline: PlatePipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    model_path = os.getenv("DETECTOR_MODEL_PATH", "models/license-plate-finetune-v1l.pt")
    pipeline = PlatePipeline(detector_model_path=model_path)
    yield


app = FastAPI(title="Plate OCR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=[
    #     "http://localhost:5173",
    #     "http://127.0.0.1:5173",
    #     "http://192.168.1.0:5173",
    #     "https://yourdomain.com",
    # ],
    # allow_credentials=True,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
async def predict(file: UploadFile = File(...)):
    global pipeline

    if pipeline is None:
        raise HTTPException(status_code=500, detail="Model pipeline not initialized")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    save_to_bucket(image_bytes, filename=file.filename)

    try:
        preds = pipeline.predict_from_bytes(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {e}") from e

    return PredictResponse(
        num_plates=len(preds),
        plates=[
            PlateResult(
                text=p.text,
                confidence=p.confidence,
                bbox_xyxy=p.bbox_xyxy,
                annotated_image=p.annotated_image,
                pred_placa=p.pred_placa,
            )
            for p in preds
        ],
    )


@app.post("/predict-image")
async def predict_image(file: UploadFile = File(...)):
    image_bytes = await file.read()

    save_to_bucket(image_bytes, filename=file.filename)

    preds = pipeline.predict_from_bytes(image_bytes)

    if not preds or preds[0].annotated_image is None:
        raise HTTPException(status_code=404, detail="No annotated image")

    img_bytes = base64.b64decode(preds[0].annotated_image)

    return Response(content=img_bytes, media_type="image/jpeg")


def save_to_bucket(image_bytes, filename):
    client = storage.Client()
    bucket = client.get_bucket('vistoria-ocr-received-imgs')
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
        base_name = filename.rsplit('.', 1)[0]
    else:
        base_name = filename

    final_filename = f"{base_name}_{timestamp}.jpg"

    blob = bucket.blob(f"received_imgs/{final_filename}")
    blob.upload_from_string(image_bytes, content_type='image/jpeg')