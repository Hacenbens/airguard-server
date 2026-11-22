"""FastAPI dependencies: hand the use cases (built once in main.py) to the routes."""
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ..application.use_cases import DetectCigarette, QueryHistory, RecordTelemetry


def _container(request: Request):
    return request.app.state.container


def require_device_key(request: Request, x_api_key: Annotated[str, Header()]) -> None:
    if not secrets.compare_digest(x_api_key, _container(request).settings.device_api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid API key")


def get_detect(request: Request) -> DetectCigarette:
    return _container(request).detect


def get_record(request: Request) -> RecordTelemetry:
    return _container(request).record


def get_history(request: Request) -> QueryHistory:
    return _container(request).history


DeviceAuth = Depends(require_device_key)
Detect = Annotated[DetectCigarette, Depends(get_detect)]
Record = Annotated[RecordTelemetry, Depends(get_record)]
History = Annotated[QueryHistory, Depends(get_history)]
