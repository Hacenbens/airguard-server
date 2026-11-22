import uuid

import structlog
from fastapi import FastAPI, Request


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Tag every log line of a request with the same request_id."""
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response
