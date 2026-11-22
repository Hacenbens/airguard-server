"""Business entities. Pure Python: no FastAPI, no database, no ML library."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Box:
    """Detected object, coordinates normalised to 0-1."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


@dataclass(frozen=True)
class RawDetection:
    """What a detector engine returns, before any business decision."""
    boxes: list[Box]
    image_size: tuple[int, int]
    inference_ms: float
    model: str


@dataclass(frozen=True)
class DetectionResult:
    cigarette: bool
    confidence: float  # best box confidence, 0 if none
    boxes: list[Box]
    image_size: tuple[int, int]
    inference_ms: float
    model: str

    @classmethod
    def decide(cls, raw: RawDetection, threshold: float) -> "DetectionResult":
        """Business rule: a cigarette is present if one box reaches the threshold."""
        best = max((b.confidence for b in raw.boxes), default=0.0)
        return cls(best >= threshold, best, raw.boxes, raw.image_size, raw.inference_ms, raw.model)


@dataclass(frozen=True)
class DetectionRecord:
    id: int
    device_id: str
    ts: str
    result: DetectionResult
    frame_path: str | None


@dataclass(frozen=True)
class TelemetryRecord:
    id: int
    device_id: str
    ts: str
    data: dict[str, Any] = field(default_factory=dict)  # open schema: new sensors need no migration


@dataclass(frozen=True)
class DeviceSummary:
    device_id: str
    last_seen: str
    telemetry_count: int
    detection_count: int
