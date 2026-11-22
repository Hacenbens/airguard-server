"""Interfaces the application needs. Infrastructure provides the implementations.

Swapping SQLite for PostgreSQL, or YOLO for an Edge Impulse model, means writing a
new class that satisfies one of these Protocols; nothing else changes.
"""
from typing import Any, Protocol

from .models import DetectionRecord, DetectionResult, DeviceSummary, RawDetection, TelemetryRecord


class DetectorEngine(Protocol):
    def detect(self, image: bytes) -> RawDetection:
        """Raise InvalidImage if the bytes are not a decodable image."""
        ...


class DetectionRepository(Protocol):
    def add_detection(self, device_id: str, ts: str, result: DetectionResult, frame_path: str | None) -> int: ...
    def list_detections(self, device_id: str, limit: int, since: str | None) -> list[DetectionRecord]: ...


class TelemetryRepository(Protocol):
    def add_telemetry(self, device_id: str, ts: str, data: dict[str, Any]) -> int: ...
    def list_telemetry(self, device_id: str, limit: int, since: str | None) -> list[TelemetryRecord]: ...


class DeviceRepository(Protocol):
    def list_devices(self) -> list[DeviceSummary]: ...


class FrameStore(Protocol):
    def save(self, device_id: str, ts: str, image: bytes, positive: bool) -> str | None:
        """Keep a frame for later labelling; return its path, or None if not kept."""
        ...


class Clock(Protocol):
    def __call__(self) -> str:
        """Current time, ISO 8601 UTC."""
        ...
