import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Header, Request

from ..deps import Detect, DeviceAuth
from ..schemas import DEVICE_ID, DetectionOut

router = APIRouter(prefix="/vision", tags=["vision"], dependencies=[DeviceAuth])
log = structlog.get_logger()


@router.post(
    "/detect",
    response_model=DetectionOut,
    summary="Detect a cigarette in one camera frame",
    description="Body: the raw JPEG (`Content-Type: image/jpeg`), as sent by the ESP32-CAM.",
    openapi_extra={"requestBody": {"required": True,
                                   "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def detect(request: Request, use_case: Detect,
                 x_device_id: Annotated[str, Header(pattern=DEVICE_ID)] = "esp32cam"):
    result = await asyncio.to_thread(use_case.execute, x_device_id, await request.body())
    log.info("vision.detect", device_id=x_device_id, cigarette=result.cigarette,
             confidence=result.confidence, inference_ms=result.inference_ms)
    return DetectionOut.of(result)
