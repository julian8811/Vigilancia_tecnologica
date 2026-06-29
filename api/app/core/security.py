"""JWT authentication helpers and cookie-based session management.

The app uses two JWTs, both signed with the same secret but with
distinct ``type`` claims:

* **access** token — short-lived (15 min by default), sent on every
  authenticated request. Stored in an httpOnly cookie.
* **refresh** token — long-lived (7 days by default), used only by
  ``/auth/refresh`` to mint a new access token. Rotated on every
  refresh so a stolen refresh token can only be used until the next
  legitimate refresh.

Both tokens are delivered via ``Set-Cookie`` headers by
``set_session_cookies`` in app.api.v1.auth, never in the response
body. The body carries only the user profile.

A third cookie, ``vg_csrf``, is the CSRF double-submit token. The
browser sends it on every request; the SPA echoes its value in the
``X-CSRF-Token`` header on mutating calls (see
``app.core.csrf``). Unlike the JWTs, this cookie is **not**
httpOnly — the SPA has to be able to read it.

The token-claim ``type`` lets the verifier reject cross-use (an
access token presented to ``/auth/refresh`` returns 401).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Token claims ───────────────────────────────────────────────────────

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _jti() -> str:
    """Generate a unique JWT ID. Ensures consecutive tokens differ
    even when iat/exp collide to the same second (matters for
    /auth/refresh rotation).
    """
    import uuid
    return str(uuid.uuid4())


def _decode(token: str, expected_type: str) -> dict[str, Any]:
    """Decode a JWT and assert its ``type`` claim matches *expected_type*.

    Raises ``JWTError`` for any decode failure or type mismatch.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != expected_type:
        raise JWTError(f"expected token type {expected_type!r}, got {payload.get('type')!r}")
    return payload


# ── Passwords ──────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return pwd_context.verify(plain, hashed)


# ── Tokens ─────────────────────────────────────────────────────────────


def create_access_token(subject: str, expires_delta: int | None = None) -> str:
    """Create a signed JWT access token for *subject*."""
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_delta or settings.JWT_EXPIRATION_MINUTES,
    )
    payload = {
        "sub": subject,
        "type": ACCESS_TOKEN_TYPE,
        "jti": _jti(),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return _encode(payload)


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token for *subject*."""
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    payload = {
        "sub": subject,
        "type": REFRESH_TOKEN_TYPE,
        "jti": _jti(),
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return _encode(payload)


def decode_access_token(token: str) -> dict[str, str]:
    """Decode and validate an access token. Raises JWTError on failure."""
    return _decode(token, ACCESS_TOKEN_TYPE)


def decode_refresh_token(token: str) -> dict[str, str]:
    """Decode and validate a refresh token. Raises JWTError on failure."""
    return _decode(token, REFRESH_TOKEN_TYPE)


# ── Cookies ───────────────────────────────────────────────────────────


def _cookie_attrs(max_age_seconds: int) -> dict[str, Any]:
    """Common cookie attributes.

    * httpOnly — the browser API does not expose the cookie to JS,
      so an XSS leak cannot read the token.
    * secure — sent only over HTTPS. Set via settings.COOKIE_SECURE
      so the same code works on http://localhost in dev.
    * samesite='lax' — block cross-site POSTs while allowing
      top-level navigation (so a link from an email keeps the
      session). This is the modern default for session cookies and
      is the only CSRF defence we ship today; a double-submit CSRF
      token is on the roadmap.
    """
    return {
        "max_age": max_age_seconds,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }


def set_session_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    """Attach the access + refresh cookies to *response*.

    Both cookies share the same path and security attributes; the
    only difference is their max-age (access = JWT_EXPIRATION_MINUTES
    in seconds, refresh = JWT_REFRESH_EXPIRATION_DAYS in seconds).
    """
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE,
        value=access_token,
        **_cookie_attrs(settings.JWT_EXPIRATION_MINUTES * 60),
    )
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        **_cookie_attrs(settings.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60),
    )


def clear_session_cookies(response: Response) -> None:
    """Remove the access + refresh cookies (logout)."""
    for name in (settings.ACCESS_TOKEN_COOKIE, settings.REFRESH_TOKEN_COOKIE):
        response.delete_cookie(name, path="/")


def set_access_cookie(response: Response, *, access_token: str) -> None:
    """Replace only the access cookie (used by /auth/refresh)."""
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE,
        value=access_token,
        **_cookie_attrs(settings.JWT_EXPIRATION_MINUTES * 60),
    )


def set_refresh_cookie(response: Response, *, refresh_token: str) -> None:
    """Replace only the refresh cookie (used by /auth/refresh)."""
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        **_cookie_attrs(settings.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60),
    )


# ── CSRF double-submit token ───────────────────────────────────────────


def _csrf_cookie_attrs() -> dict[str, Any]:
    """Attributes for the vg_csrf cookie.

    Unlike the JWT cookies, this one is **not** httpOnly: the SPA
    needs to read it via ``document.cookie`` and echo the value in
    the ``X-CSRF-Token`` header on every mutating request. All
    other attributes match the JWT cookies (path=/, SameSite=Lax,
    Secure follows ``settings.COOKIE_SECURE``). The max-age matches
    the refresh-token lifetime so a user stays protected across the
    SPA's normal tab-resume patterns.
    """
    return {
        "max_age": settings.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60,
        "httponly": False,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
        "path": "/",
    }


def set_csrf_cookie(response: Response, *, token: str) -> None:
    """Attach the vg_csrf cookie to *response* with the given *token*."""
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=token,
        **_csrf_cookie_attrs(),
    )


def rotate_csrf_cookie(response: Response) -> str:
    """Generate a fresh CSRF token, set the cookie, and return the token.

    ``secrets.token_urlsafe(32)`` produces a 43-char URL-safe string
    with 256 bits of entropy — large enough that guessing is
    infeasible, small enough to fit comfortably in a header.
    """
    token = secrets.token_urlsafe(32)
    set_csrf_cookie(response, token=token)
    return token


def clear_csrf_cookie(response: Response) -> None:
    """Delete the vg_csrf cookie (called on logout)."""
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


def get_csrf_cookie(request) -> str | None:
    """Read the current vg_csrf cookie value from the request, if any.

    Used by /auth/me to surface the token in the response body so
    the SPA has it before its first mutating call.
    """
    return request.cookies.get(settings.CSRF_COOKIE_NAME)
