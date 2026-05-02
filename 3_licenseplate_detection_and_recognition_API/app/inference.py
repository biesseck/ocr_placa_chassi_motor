from __future__ import annotations

import base64
from dataclasses import dataclass
from email.mime import image
from typing import List, Optional
import io

import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer


@dataclass
class PlatePrediction:
    text: str
    confidence: Optional[float]
    bbox_xyxy: List[float]
    annotated_image: Optional[str] = None # base64-encoded annotated image


class PlatePipeline:
    def __init__(self, detector_model_path='models/license-plate-finetune-v1l.pt') -> None:
        self.detector = YOLO(detector_model_path)
        self.recognizer = LicensePlateRecognizer('cct-s-v1-global-model')

    def predict_from_bytes(self, image_bytes: bytes) -> List[PlatePrediction]:
        image = self._decode_image(image_bytes)
        img_resized, scale = self.resize_with_scale(image, target_size=640)

        # Run detector
        results = self.detector.predict(
            source=img_resized,
            verbose=False,
            conf=0.6,
            iou=0.45,
            max_det=1
        )

        predictions: List[PlatePrediction] = []

        if not results:
            return predictions

        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return predictions

        boxes = result.boxes.xyxy.cpu().numpy()

        for box in boxes:
            x1, y1, x2, y2 = [int(round(v)) for v in box.tolist()]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_resized.shape[1], x2)
            y2 = min(img_resized.shape[0], y2)

            img_resized = cv2.rectangle(img_resized, (x1, y1), (x2, y2), (0,255,0), 2)

            _, buffer = cv2.imencode(".jpg", img_resized)
            encoded_resized = base64.b64encode(buffer).decode("utf-8")

            '''
            crop = img_resized[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # fast_plate_ocr often expects RGB
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

            # Adapt this call to your exact recognizer API
            rec_output = self.recognizer.run(crop_rgb)

            if isinstance(rec_output, list) and len(rec_output) > 0:
                text = str(rec_output[0])
            else:
                text = str(rec_output)
            '''
                
            predictions.append(
                PlatePrediction(
                    text='deu boa!',
                    confidence=None,
                    bbox_xyxy=[float(x1), float(y1), float(x2), float(y2)],
                    annotated_image=encoded_resized,
                )
            )

        return predictions

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image bytes")
        return image
    
    @staticmethod
    def resize_with_scale(image, target_size=640):
        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        resized_image = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
        return resized_image, scale