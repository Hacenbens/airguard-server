"""AirGuard backend - composition root: the only place that knows every layer.

Run (from the repository root, venv active):
    uvicorn app.main:app --host 0.0.0.0 --port 8000
Docs (dev only): http://localhost:8000/docs

Layers (dependencies point inwards only):
    api/            HTTP: routes, schemas, auth, error mapping      -> application
    application/    use cases                                       -> domain
    domain/         entities, business rules, ports (interfaces)    -> nothing
    infrastructure/ SQLite, YOLO, filesystem, config, logging       -> domain (implements ports)

New feature: domain model/port if needed -> use case -> router in api/routers/ -> wire it below.
"""
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass

import structlog
from fastapi import FastAPI

from .api.errors import register_error_handlers
from .api.middleware import register_middleware
from .api.routers import devices, system, vision
from .application.use_cases import DetectCigarette, QueryHistory, RecordTelemetry
from .infrastructure.config import Settings
from .infrastructure.frame_store import FileFrameStore
from .infrastructure.logging import configure_logging
from .infrastructure.sqlite_repository import SqliteRepository, utc_now
from .infrastructure.yolo_detector import YoloDetector

settings = Settings()
configure_logging(settings.environment)
log = structlog.get_logger()


@dataclass
class Container:
    settings: Settings
    repo: SqliteRepository
    detect: DetectCigarette
    record: RecordTelemetry
    history: QueryHistory


def build_container(s: Settings) -> Container:
    repo = SqliteRepository(s.db_path)
    engine = YoloDetector(s.model_path, s.model_imgsz)
    frames = FileFrameStore(s.frames_dir, s.save_frames)
    return Container(
        settings=s,
        repo=repo,
        detect=DetectCigarette(engine, repo, frames, utc_now, s.detect_threshold, s.max_image_bytes),
        record=RecordTelemetry(repo, utc_now),
        history=QueryHistory(repo, repo, repo),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = await asyncio.to_thread(build_container, settings)
    log.info("startup", model=settings.model_path.name, db=str(settings.db_path), threshold=settings.detect_threshold)
    yield
    app.state.container.repo.close()


prod = settings.environment == "production"
app = FastAPI(
    title="AirGuard API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if prod else "/docs",
    redoc_url=None if prod else "/redoc",
    openapi_url=None if prod else "/openapi.json",
)
register_middleware(app)
register_error_handlers(app)

API = "/api/v1"
app.include_router(system.router)
app.include_router(vision.router, prefix=API)
app.include_router(devices.router, prefix=API)
