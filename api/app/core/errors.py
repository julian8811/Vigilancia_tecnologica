"""Application-wide exception handlers for FastAPI."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from structlog import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error with an HTTP status code and message."""

    def __init__(self, status_code: int = 500, detail: str = "Error interno del servidor") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def register_error_handlers(app: FastAPI) -> None:
    """Attach custom exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", status_code=exc.status_code, detail=exc.detail, path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor"},
        )
