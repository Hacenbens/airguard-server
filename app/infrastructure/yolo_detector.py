"""YOLOv8 implementation of DetectorEngine, loaded once at startup.

Blocking and CPU-bound. The lock serialises calls (the Ultralytics predictor is not
thread-safe); one camera at 1 frame / 1-2 s is fine. Many cameras -> a job queue.
"""
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from ..domain.errors import InvalidImage
from ..domain.models import Box, RawDetection
from ..domain.ports import DetectorEngine

MIN_CONF = 0.1  # boxes kept below the decision threshold, so near-misses are logged


class YoloDetector(DetectorEngine):
    def __init__(self, model_path: Path, imgsz: int):
        self._model = YOLO(str(model_path))
        self._name = model_path.name
        self._imgsz = imgsz
        self._lock = threading.Lock()
        self.detect(cv2.imencode(".jpg", np.zeros((64, 64, 3), np.uint8))[1].tobytes())  # warm-up

    def detect(self, image: bytes) -> RawDetection:
        img = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise InvalidImage("body is not a decodable JPEG/PNG image")
        h, w = img.shape[:2]
        t0 = time.perf_counter()
        with self._lock:
            r = self._model.predict(img, imgsz=self._imgsz, conf=MIN_CONF, verbose=False)[0]
        ms = (time.perf_counter() - t0) * 1000
        boxes = [
            Box(round(x1 / w, 4), round(y1 / h, 4), round(x2 / w, 4), round(y2 / h, 4), round(c, 3))
            for (x1, y1, x2, y2), c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist())
        ]
        return RawDetection(boxes, (w, h), round(ms, 1), self._name)
