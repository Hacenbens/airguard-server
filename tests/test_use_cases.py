"""Use-case tests with in-memory fakes: no YOLO, no SQLite, no HTTP. Run in milliseconds."""
import pytest

from app.application.use_cases import DetectCigarette, RecordTelemetry
from app.domain.errors import ImageTooLarge, InvalidImage
from app.domain.models import Box, RawDetection, TelemetryRecord


class FakeEngine:
    def __init__(self, confidences):
        self.confidences = confidences

    def detect(self, image):
        return RawDetection([Box(0.1, 0.1, 0.2, 0.2, c) for c in self.confidences], (640, 480), 5.0, "fake")


class FakeRepo:
    def __init__(self):
        self.detections, self.telemetry = [], []

    def add_detection(self, device_id, ts, result, frame_path):
        self.detections.append((device_id, ts, result, frame_path))
        return len(self.detections)

    def add_telemetry(self, device_id, ts, data):
        self.telemetry.append((device_id, ts, data))
        return len(self.telemetry)


class FakeFrames:
    def save(self, device_id, ts, image, positive):
        return f"/frames/{device_id}.jpg" if positive else None


def clock():
    return "2026-11-22T10:00:00.000+00:00"


def make(confidences, threshold=0.25):
    repo = FakeRepo()
    return DetectCigarette(FakeEngine(confidences), repo, FakeFrames(), clock, threshold, 1000), repo


@pytest.mark.parametrize("confs, expected", [([], False), ([0.1, 0.2], False), ([0.1, 0.25], True), ([0.9], True)])
def test_threshold_rule(confs, expected):
    uc, repo = make(confs)
    r = uc.execute("totem1", b"jpeg")
    assert r.cigarette is expected
    assert r.confidence == max(confs, default=0.0)
    assert repo.detections[0][3] == ("/frames/totem1.jpg" if expected else None)


def test_rejects_empty_and_oversized():
    uc, repo = make([0.9])
    with pytest.raises(InvalidImage):
        uc.execute("totem1", b"")
    with pytest.raises(ImageTooLarge):
        uc.execute("totem1", b"x" * 1001)
    assert repo.detections == []


def test_record_telemetry_uses_server_time_by_default():
    repo = FakeRepo()
    rec = RecordTelemetry(repo, clock).execute("totem1", {"gas_raw": 1200})
    assert rec == TelemetryRecord(1, "totem1", clock(), {"gas_raw": 1200})
    assert RecordTelemetry(repo, clock).execute("totem1", {}, "2026-01-01T00:00:00").ts == "2026-01-01T00:00:00"
