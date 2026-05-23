from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import json
 
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
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


@app.post("/predict-image")
async def predict_image(file: UploadFile = File(...)):
    image_bytes = await file.read()

    save_to_bucket(image_bytes, filename=file.filename)

    preds = pipeline.predict_from_bytes(image_bytes)

    if not preds or preds[0].annotated_image is None:
        raise HTTPException(status_code=404, detail="No annotated image")

    img_bytes = base64.b64decode(preds[0].annotated_image)

    return Response(content=img_bytes, media_type="image/jpeg")


@app.post("/predict", response_model=PredictResponse)
async def predict(request: Request, file: UploadFile = File(...)):
    global pipeline

    if pipeline is None:
        raise HTTPException(status_code=500, detail="Model pipeline not initialized")

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    filename = file.filename
    if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
        base_name = filename.rsplit('.', 1)[0]
    else:
        base_name = filename
    base_name = f"{timestamp}_{base_name}"

    user_info = extract_user_info(request, filename)

    try:
        preds = pipeline.predict_from_bytes(image_bytes)

        pred_img_bytes = None
        if len(preds) > 0:
            pred_img_bytes = base64.b64decode(preds[0].annotated_image)
        
        save_to_bucket(base_name, image_bytes, pred_img_bytes, user_info)

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


def extract_user_info(request: Request, filename: str) -> dict:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else "unknown"
    
    return {
        "ip_address": client_ip,
        "country": request.headers.get("X-AppEngine-Country", "unknown"),
        "state_region": request.headers.get("X-AppEngine-Region", "unknown"),
        "city": request.headers.get("X-AppEngine-City", "unknown"),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "original_filename": filename,
        "ocr_processed_at": datetime.now(timezone.utc).isoformat()
    }


def save_to_bucket(base_name, image_bytes, annotated_image_bytes=None, user_info={}):
    client = storage.Client()
    bucket = client.get_bucket('vistoria-ocr-received-imgs')

    final_image_filename = f"{base_name}.jpg"
    final_annotated_image_filename = f"{base_name}_annotated.jpg"
    final_json_filename = f"{base_name}.json"

    image_blob = bucket.blob(f"received_imgs/{final_image_filename}")
    image_blob.upload_from_string(image_bytes, content_type='image/jpeg')

    if not annotated_image_bytes is None:
        annotated_image_blob = bucket.blob(f"received_imgs/{final_annotated_image_filename}")
        annotated_image_blob.upload_from_string(annotated_image_bytes, content_type='image/jpeg')

    json_string = json.dumps(user_info, indent=4, ensure_ascii=False)

    json_blob = bucket.blob(f"received_imgs/{final_json_filename}")
    json_blob.upload_from_string(json_string, content_type='application/json')