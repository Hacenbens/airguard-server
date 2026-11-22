"""Run from the repository root:  python -m pytest -q"""
import os
from pathlib import Path

import pytest

KEY = "test-key-0123456789abcdef"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("airguard")
    os.environ.update(DEVICE_API_KEY=KEY, DB_PATH=str(tmp / "t.db"), SAVE_FRAMES="all", FRAMES_DIR=str(tmp / "frames"))
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


H = {"X-API-Key": KEY, "X-Device-Id": "totem1"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_auth_required(client):
    assert client.post("/api/v1/vision/detect", content=b"x", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/api/v1/devices/totem1/telemetry", json={}).status_code == 422  # header missing


def test_detect_rejects_garbage(client):
    r = client.post("/api/v1/vision/detect", content=b"not an image", headers=H)
    assert r.status_code == 422


def test_detect_real_image(client):
    img = Path(__file__).parent / "fixtures" / "cigarette.jpg"
    r = client.post("/api/v1/vision/detect", content=img.read_bytes(),
                    headers={**H, "Content-Type": "image/jpeg"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"cigarette", "confidence", "boxes", "inference_ms"}
    assert all(0 <= b["x1"] <= b["x2"] <= 1 for b in body["boxes"])
    d = client.get("/api/v1/devices/totem1/detections").json()
    assert len(d) == 1 and d[0]["frame_path"]  # SAVE_FRAMES=all


def test_telemetry_roundtrip(client):
    r = client.post("/api/v1/devices/totem1/telemetry", headers=H,
                    json={"gas_raw": 1830, "fan_pwm": 60, "state": "filtration", "mode": "sensors", "co2_ppm": 640})
    assert r.status_code == 201, r.text
    rows = client.get("/api/v1/devices/totem1/telemetry").json()
    assert rows[0]["gas_raw"] == 1830 and rows[0]["co2_ppm"] == 640  # unknown field kept


def test_telemetry_validation(client):
    r = client.post("/api/v1/devices/totem1/telemetry", headers=H, json={"gas_raw": 99999, "state": "bogus"})
    assert r.status_code == 422


def test_devices_list(client):
    devs = client.get("/api/v1/devices").json()
    assert devs[0]["device_id"] == "totem1" and devs[0]["telemetry_count"] >= 1
