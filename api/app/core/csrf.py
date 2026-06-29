"""CSRF double-submit middleware.

The web app's auth flow issues three cookies: ``vg_access`` and
``vg_refresh`` are httpOnly, but ``vg_csrf`` is intentionally
**not** httpOnly so the SPA can read it via ``document.cookie`` and
echo its value in an ``X-CSRF-Token`` header on every mutating
request. This middleware enforces that contract for state-changing
methods under ``/api/v1/``:

* Safe methods (``GET``, ``HEAD``, ``OPTIONS``) are never blocked.
* The bootstrap auth endpoints (``/api/v1/auth/login``,
  ``/api/v1/auth/register``, ``/api/v1/auth/refresh``) are exempt
  because they are the only way a fresh client can obtain the
  ``vg_csrf`` cookie.
* Every other ``POST/PUT/PATCH/DELETE`` under ``/api/v1/`` must
  carry a matching ``X-CSRF-Token`` header and ``vg_csrf`` cookie,
  otherwise we return 403 with ``{"detail": "CSRF validation failed"}``.

Order in ``main.py`` is: ``RequestID → SecurityHeaders → CORS → CSRF``.
The CSRF check sits AFTER CORS so the ``Access-Control-*`` headers
are already attached to our 403 response (preflights are exempt by
the OPTIONS rule, not by CORS bypass).
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Methods that never modify server state — exempt from CSRF checks.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths under /api/v1/ that bootstrap a fresh session and therefore
# cannot require a CSRF token (the client does not have one yet).
# Order matters: longer prefixes must be checked first.
_EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
})


def _is_exempt(path: str) -> bool:
    return path in _EXEMPT_PATHS


def _is_under_api(path: str) -> bool:
    return path.startswith("/api/v1/")


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforce the double-submit CSRF contract on mutating /api/v1/ routes."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Only enforce under /api/v1/. Other routes (/health, /docs,
        #    /openapi.json) are out of scope.
        if not _is_under_api(request.url.path):
            return await call_next(request)

        # 2. Safe methods bypass the check entirely.
        if request.method.upper() in _SAFE_METHODS:
            return await call_next(request)

        # 3. Bootstrap auth endpoints are exempt so a fresh client can
        #    obtain its first vg_csrf cookie.
        if _is_exempt(request.url.path):
            return await call_next(request)

        # 4. For every other mutating request, the cookie and the
        #    header must BOTH be present and equal.
        cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
        header_token = request.headers.get("X-CSRF-Token")

        if not cookie_token or not header_token or cookie_token != header_token:
            logger.warning(
                "csrf_validation_failed",
                path=request.url.path,
                method=request.method,
                has_cookie=bool(cookie_token),
                has_header=bool(header_token),
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )

        return await call_next(request)
