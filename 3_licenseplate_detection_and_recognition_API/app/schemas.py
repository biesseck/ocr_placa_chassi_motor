from pydantic import BaseModel
from typing import List, Optional


class PlateResult(BaseModel):
    text: str
    confidence: Optional[float] = None
    bbox_xyxy: List[float]
    annotated_image: Optional[bytes] = None # base64-encoded annotated image
    pred_placa: Optional[str] = None


class PredictResponse(BaseModel):
    num_plates: int
    plates: List[PlateResult]