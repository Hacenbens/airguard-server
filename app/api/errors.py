"""Map domain errors to HTTP responses in one place (routes stay free of try/except)."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ..domain.errors import DomainError, ImageTooLarge, InvalidImage

STATUS = {
    InvalidImage: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ImageTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        code = STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return JSONResponse({"detail": str(exc)}, status_code=code)
