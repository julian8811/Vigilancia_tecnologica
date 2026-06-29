"""Application-wide exception handlers for FastAPI."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from structlog import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error with an HTTP status code and message.

    Subclasses set ``status_code`` and ``detail``; the handler returns a
    consistent ``{"detail": ...}`` envelope so the web client can read
    every error with the same code path.
    """

    def __init__(self, status_code: int = 500, detail: str = "Error interno del servidor") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _envelope(detail: str, status_code: int, **extra) -> dict:
    """Build a consistent error envelope.

    Always uses ``{"detail": ...}`` so the web client has a single field
    to read. The HTTP status code lives on the response, not in the body.
    """
    body: dict = {"detail": detail}
    body.update(extra)
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach custom exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            status_code=exc.status_code,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.detail, exc.status_code),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # FastAPI's default HTTPException already uses {"detail": ...}.
        # We re-emit it through our envelope so the body is always shaped
        # the same way regardless of source.
        detail = exc.detail if isinstance(exc.detail, str) else "Error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(detail, exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic validation errors. Surface a short summary in `detail`
        # and keep the full structured errors in `errors` for tooling.
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", [])) or "body"
        msg = first.get("msg", "datos inválidos")
        return JSONResponse(
            status_code=422,
            content=_envelope(
                f"{loc}: {msg}",
                422,
                errors=errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=str(request.url))
        return JSONResponse(
            status_code=500,
            content=_envelope("Error interno del servidor", 500),
        )
