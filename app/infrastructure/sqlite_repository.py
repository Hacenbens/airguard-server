"""SQLite implementation of the repositories. One connection, shared behind a lock.

Tables keep a few indexed columns plus a JSON payload, so new telemetry fields
need no migration.
"""
import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.models import Box, DetectionRecord, DetectionResult, DeviceSummary, TelemetryRecord
from ..domain.ports import DetectionRepository, DeviceRepository, TelemetryRepository

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS telemetry_device_ts ON telemetry(device_id, ts);

CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    cigarette INTEGER NOT NULL,
    confidence REAL NOT NULL,
    boxes TEXT NOT NULL,
    image_w INTEGER NOT NULL,
    image_h INTEGER NOT NULL,
    inference_ms REAL NOT NULL,
    model TEXT NOT NULL,
    frame_path TEXT
);
CREATE INDEX IF NOT EXISTS detections_device_ts ON detections(device_id, ts);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class SqliteRepository(DetectionRepository, TelemetryRepository, DeviceRepository):
    """One SQLite database serving the three repository ports."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._lock = threading.Lock()

    def close(self) -> None:
        self._conn.close()

    def _write(self, sql: str, args: tuple) -> int:
        with self._lock, self._conn:
            return self._conn.execute(sql, args).lastrowid

    def _read(self, sql: str, args: tuple) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, args).fetchall()

    # --- telemetry -------------------------------------------------------
    def add_telemetry(self, device_id: str, ts: str, data: dict[str, Any]) -> int:
        return self._write("INSERT INTO telemetry(device_id, ts, payload) VALUES (?,?,?)",
                           (device_id, ts, json.dumps(data)))

    def list_telemetry(self, device_id: str, limit: int, since: str | None) -> list[TelemetryRecord]:
        rows = self._read("SELECT id, ts, payload FROM telemetry WHERE device_id=? AND ts>=? ORDER BY ts DESC LIMIT ?",
                          (device_id, since or "", limit))
        return [TelemetryRecord(r["id"], device_id, r["ts"], json.loads(r["payload"])) for r in rows]

    # --- detections ------------------------------------------------------
    def add_detection(self, device_id: str, ts: str, result: DetectionResult, frame_path: str | None) -> int:
        return self._write(
            "INSERT INTO detections(device_id, ts, cigarette, confidence, boxes, image_w, image_h, inference_ms,"
            " model, frame_path) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (device_id, ts, int(result.cigarette), result.confidence, json.dumps([asdict(b) for b in result.boxes]),
             *result.image_size, result.inference_ms, result.model, frame_path))

    def list_detections(self, device_id: str, limit: int, since: str | None) -> list[DetectionRecord]:
        rows = self._read("SELECT * FROM detections WHERE device_id=? AND ts>=? ORDER BY ts DESC LIMIT ?",
                          (device_id, since or "", limit))
        return [
            DetectionRecord(
                r["id"], device_id, r["ts"],
                DetectionResult(bool(r["cigarette"]), r["confidence"], [Box(**b) for b in json.loads(r["boxes"])],
                                (r["image_w"], r["image_h"]), r["inference_ms"], r["model"]),
                r["frame_path"])
            for r in rows
        ]

    # --- devices ---------------------------------------------------------
    def list_devices(self) -> list[DeviceSummary]:
        rows = self._read(
            "SELECT device_id, MAX(ts) AS last_seen, SUM(kind='t') AS telemetry_count, SUM(kind='d') AS detection_count"
            " FROM (SELECT device_id, ts, 't' AS kind FROM telemetry"
            "       UNION ALL SELECT device_id, ts, 'd' FROM detections)"
            " GROUP BY device_id ORDER BY last_seen DESC", ())
        return [DeviceSummary(**dict(r)) for r in rows]
