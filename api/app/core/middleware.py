"""Cross-cutting middleware: request ID, security headers."""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)

# Security headers applied to every response. Tune as the frontend grows.
_SECURITY_HEADERS: dict[str, str] = {
    # Block clickjacking by refusing to render in an iframe.
    "X-Frame-Options": "DENY",
    # Stop MIME-sniffing attacks.
    "X-Content-Type-Options": "nosniff",
    # Don't leak the full URL to third parties.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Disable browser features the app does not need.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    # A conservative CSP. The web app is served on a different origin
    # (NEXT_PUBLIC_FRONTEND_URL) and only talks to the API; adjust if
    # you start loading third-party assets.
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}

# HSTS only makes sense over HTTPS. We enable it always; the browser
# only honours it on secure transports.
_HSTS_HEADER = "max-age=31536000; includeSubDomains"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable X-Request-ID to every request and response.

    The ID is read from the inbound ``X-Request-ID`` header if the caller
    sent one, otherwise we generate a uuid4. The same value is bound
    to structlog's contextvars so every log line emitted while handling
    the request carries it automatically.
    """

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)

        try:
            response = await call_next(request)
        finally:
            # Clear context after the request so log lines from the next
            # request don't accidentally inherit this ID.
            structlog.contextvars.clear_contextvars()

        response.headers[self.HEADER] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response.

    Headers are added at the middleware layer so they apply uniformly to
    /docs, /openapi.json, error responses, and every API endpoint.
    """

    def __init__(self, app: ASGIApp, *, hsts: bool = True) -> None:
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        if self.hsts:
            response.headers["Strict-Transport-Security"] = _HSTS_HEADER
        return response
