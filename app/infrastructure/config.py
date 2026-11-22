from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repository root (server/)


class Settings(BaseSettings):
    """All configuration comes from env vars or server/.env (see .env.example)."""

    environment: Literal["dev", "production"] = "dev"
    device_api_key: str = Field(min_length=16)  # shared secret sent by the devices in X-API-Key

    db_path: Path = ROOT / "data" / "airguard.db"

    model_path: Path = ROOT / "models" / "airguard_yolov8n_ep25.pt"
    model_imgsz: int = Field(960, ge=320, le=1920)
    detect_threshold: float = Field(0.25, gt=0, lt=1)  # confidence above which "cigarette = yes"
    max_image_bytes: int = 2_000_000

    # keep frames sent by the camera to grow the dataset: none | positive | all
    save_frames: Literal["none", "positive", "all"] = "positive"
    frames_dir: Path = ROOT / "data" / "frames"

    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8")
