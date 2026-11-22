"""Filesystem implementation of FrameStore: keeps camera frames to grow the dataset."""
from pathlib import Path
from typing import Literal

from ..domain.ports import FrameStore

Policy = Literal["none", "positive", "all"]


class FileFrameStore(FrameStore):
    def __init__(self, root: Path, policy: Policy):
        self._root, self._policy = root, policy

    def save(self, device_id: str, ts: str, image: bytes, positive: bool) -> str | None:
        if self._policy == "none" or (self._policy == "positive" and not positive):
            return None
        d = self._root / device_id / ("positive" if positive else "negative")
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{ts.replace(':', '-')}.jpg"
        p.write_bytes(image)
        return str(p)
