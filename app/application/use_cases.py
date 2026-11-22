"""Use cases: what the system does, independent of how it is exposed or stored.

All methods are synchronous (the detector and SQLite block); the API layer runs
them with asyncio.to_thread().
"""
from typing import Any

from ..domain.errors import ImageTooLarge, InvalidImage
from ..domain.models import DetectionRecord, DetectionResult, DeviceSummary, TelemetryRecord
from ..domain.ports import (Clock, DetectionRepository, DetectorEngine, DeviceRepository, FrameStore,
                            TelemetryRepository)


class DetectCigarette:
    """A camera frame comes in -> decide if a cigarette is present -> keep a record."""

    def __init__(self, engine: DetectorEngine, detections: DetectionRepository, frames: FrameStore,
                 clock: Clock, threshold: float, max_image_bytes: int):
        self.engine, self.detections, self.frames, self.clock = engine, detections, frames, clock
        self.threshold, self.max_image_bytes = threshold, max_image_bytes

    def execute(self, device_id: str, image: bytes) -> DetectionResult:
        if not image:
            raise InvalidImage("empty image")
        if len(image) > self.max_image_bytes:
            raise ImageTooLarge(f"image larger than {self.max_image_bytes} bytes")
        result = DetectionResult.decide(self.engine.detect(image), self.threshold)
        ts = self.clock()
        frame_path = self.frames.save(device_id, ts, image, result.cigarette)
        self.detections.add_detection(device_id, ts, result, frame_path)
        return result


class RecordTelemetry:
    """A sensor sample comes in from a totem -> store it."""

    def __init__(self, telemetry: TelemetryRepository, clock: Clock):
        self.telemetry, self.clock = telemetry, clock

    def execute(self, device_id: str, data: dict[str, Any], ts: str | None = None) -> TelemetryRecord:
        ts = ts or self.clock()
        rid = self.telemetry.add_telemetry(device_id, ts, data)
        return TelemetryRecord(rid, device_id, ts, data)


class QueryHistory:
    """Read side: history for dashboards and the evaluation report."""

    def __init__(self, telemetry: TelemetryRepository, detections: DetectionRepository, devices: DeviceRepository):
        self._telemetry, self._detections, self._devices = telemetry, detections, devices

    def telemetry(self, device_id: str, limit: int, since: str | None) -> list[TelemetryRecord]:
        return self._telemetry.list_telemetry(device_id, limit, since)

    def detections(self, device_id: str, limit: int, since: str | None) -> list[DetectionRecord]:
        return self._detections.list_detections(device_id, limit, since)

    def devices(self) -> list[DeviceSummary]:
        return self._devices.list_devices()
