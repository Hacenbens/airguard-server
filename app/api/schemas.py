"""HTTP contracts (Pydantic): input validation + output shape, mapped from domain objects."""
from dataclasses import asdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..domain.models import DetectionRecord, DetectionResult, TelemetryRecord

DEVICE_ID = r"^[A-Za-z0-9_-]{1,32}$"


class BoxOut(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


class DetectionOut(BaseModel):
    cigarette: bool
    confidence: float = Field(description="best box confidence, 0 if none")
    boxes: list[BoxOut] = Field(description="normalised 0-1 coordinates")
    image_size: list[int]
    inference_ms: float
    model: str

    @classmethod
    def of(cls, r: DetectionResult) -> "DetectionOut":
        return cls(**asdict(r))


class DetectionRecordOut(DetectionOut):
    id: int
    device_id: str
    ts: str
    frame_path: str | None

    @classmethod
    def of(cls, rec: DetectionRecord) -> "DetectionRecordOut":
        return cls(id=rec.id, device_id=rec.device_id, ts=rec.ts, frame_path=rec.frame_path, **asdict(rec.result))


class TelemetryIn(BaseModel):
    """Sent by the LilyGO. Extra fields are accepted and stored as-is (future sensors)."""

    model_config = ConfigDict(extra="allow")

    ts: datetime | None = Field(None, description="device time; server time used if absent")
    gas_raw: int | None = Field(None, ge=0, le=4095, description="MQ sensor ADC value")
    fan_pwm: int | None = Field(None, ge=0, le=100, description="fan duty cycle, %")
    fan_rpm: int | None = Field(None, ge=0, le=20000)
    cigarette: bool | None = None
    cigarette_confidence: float | None = Field(None, ge=0, le=1)
    state: Literal["veille", "filtration", "alerte"] | None = None
    mode: Literal["sensors", "sensors_vision"] | None = Field(None, description="control mode under evaluation")


class TelemetryOut(TelemetryIn):
    id: int
    device_id: str
    ts: str

    @classmethod
    def of(cls, rec: TelemetryRecord) -> "TelemetryOut":
        return cls(id=rec.id, device_id=rec.device_id, ts=rec.ts, **rec.data)


class Created(BaseModel):
    id: int
    ts: str


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    last_seen: str
    telemetry_count: int
    detection_count: int
