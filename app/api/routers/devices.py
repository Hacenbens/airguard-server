import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Path, Query, status

from ..deps import DeviceAuth, History, Record
from ..schemas import DEVICE_ID, Created, DetectionRecordOut, DeviceOut, TelemetryIn, TelemetryOut

router = APIRouter(prefix="/devices", tags=["devices"])
log = structlog.get_logger()

DeviceId = Annotated[str, Path(pattern=DEVICE_ID)]
Limit = Annotated[int, Query(ge=1, le=10_000)]
Since = Annotated[str | None, Query(description="ISO timestamp, e.g. 2026-11-22T10:00:00")]


@router.post("/{device_id}/telemetry", response_model=Created, status_code=status.HTTP_201_CREATED,
             dependencies=[DeviceAuth], summary="Store one telemetry sample (LilyGO)")
async def post_telemetry(device_id: DeviceId, body: TelemetryIn, use_case: Record):
    data = body.model_dump(mode="json", exclude_none=True)
    ts = data.pop("ts", None)
    rec = await asyncio.to_thread(use_case.execute, device_id, data, ts)
    log.info("telemetry.stored", device_id=device_id, **data)
    return {"id": rec.id, "ts": rec.ts}


@router.get("/{device_id}/telemetry", response_model=list[TelemetryOut], summary="Latest telemetry, newest first")
async def get_telemetry(device_id: DeviceId, history: History, limit: Limit = 100, since: Since = None):
    return [TelemetryOut.of(r) for r in await asyncio.to_thread(history.telemetry, device_id, limit, since)]


@router.get("/{device_id}/detections", response_model=list[DetectionRecordOut],
            summary="Latest vision results, newest first")
async def get_detections(device_id: DeviceId, history: History, limit: Limit = 100, since: Since = None):
    return [DetectionRecordOut.of(r) for r in await asyncio.to_thread(history.detections, device_id, limit, since)]


@router.get("", response_model=list[DeviceOut], summary="Devices seen so far")
async def list_devices(history: History):
    return await asyncio.to_thread(history.devices)
