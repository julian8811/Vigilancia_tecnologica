"""Auth router — registration, login, refresh, and logout.

Tokens are delivered via httpOnly cookies (`vg_access`, `vg_refresh`)
on the `Set-Cookie` header — never in the response body. The
double-submit CSRF token (`vg_csrf`) lives in a **non-httpOnly**
cookie so the SPA can read it and echo it in the `X-CSRF-Token`
header on mutating requests.

Note: per-endpoint @limiter.limit is removed (slowapi's decorator
breaks body binding on FastAPI 0.115). The global default_limits
still applies. Per-IP rate limiting is on the roadmap.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_audit_context, get_current_active_user, get_db
from app.core.config import settings
from app.core.security import (
    clear_csrf_cookie,
    clear_session_cookies,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    rotate_csrf_cookie,
    set_session_cookies,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    SessionResponse,
)
from app.schemas.user import UserResponse
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["autenticación"])


def _build_session(user: User, csrf_token: str | None = None) -> SessionResponse:
    return SessionResponse(
        user=UserResponse.model_validate(user),
        csrf_token=csrf_token,
    )


def _new_tokens(user: User) -> tuple[str, str]:
    subject = str(user.id)
    return create_access_token(subject), create_refresh_token(subject)


def _client_info(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


def _set_session_and_csrf(response: Response, user: User) -> str:
    """Set the session cookies + a fresh CSRF cookie, return the token.

    The token is returned so the caller can include it in the
    response body (the SPA uses the body to populate its first
    X-CSRF-Token header before the cookie is set on subsequent
    requests). On the first response the SPA also receives a
    Set-Cookie for vg_csrf — the body's value is just a convenience.
    The token is also echoed as the ``X-CSRF-Token`` response
    header so the SPA has two ways to learn it.
    """
    access, refresh = _new_tokens(user)
    set_session_cookies(response, access_token=access, refresh_token=refresh)
    token = rotate_csrf_cookie(response)
    response.headers["X-CSRF-Token"] = token
    return token


@router.post("/register", response_model=SessionResponse, status_code=201)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit_context: AuditContext = Depends(get_audit_context),
) -> SessionResponse:
    """Register a new user account. Sets the session cookies on success."""
    service = AuthService(db, audit_context=audit_context)
    user = await service.register_user(body)
    csrf_token = _set_session_and_csrf(response, user)
    logger.info("user_registered", user_id=str(user.id), email=user.email)
    return _build_session(user, csrf_token)


@router.post("/login", response_model=SessionResponse)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit_context: AuditContext = Depends(get_audit_context),
) -> SessionResponse:
    """Authenticate. Sets the session cookies on success."""
    service = AuthService(db, audit_context=audit_context)
    user, outcome = await service.login_user(body)
    if user is None:
        logger.info("login_failed", email=body.email, reason=outcome)
        raise HTTPException(status_code=401, detail="Correo o contraseña inválidos")

    csrf_token = _set_session_and_csrf(response, user)
    logger.info("login_success", user_id=str(user.id), email=user.email)
    return _build_session(user, csrf_token)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Issue a fresh access + refresh token pair."""
    from uuid import UUID

    from app.repositories.user_repository import UserRepository

    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        clear_session_cookies(response)
        clear_csrf_cookie(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError:
        clear_session_cookies(response)
        clear_csrf_cookie(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        clear_session_cookies(response)
        clear_csrf_cookie(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        clear_session_cookies(response)
        clear_csrf_cookie(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    csrf_token = _set_session_and_csrf(response, user)
    return _build_session(user, csrf_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    """Clear the session cookies. Idempotent — safe to call twice."""
    clear_session_cookies(response)
    clear_csrf_cookie(response)
    return LogoutResponse()


@router.get("/me", response_model=UserResponse)
async def me(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the currently authenticated user's profile.

    The current CSRF token is echoed in the ``X-CSRF-Token``
    response header so the SPA can grab it on the very first /me
    call before the next mutating request (the cookie is also set
    — the header is just a convenience for the SPA bootstrap path).
    The response body keeps the flat user shape for backward
    compatibility with the existing API contract.
    """
    from app.core.security import get_csrf_cookie

    csrf_token = get_csrf_cookie(request)
    if csrf_token:
        response.headers["X-CSRF-Token"] = csrf_token
    return UserResponse.model_validate(current_user)


@router.post("/change-password", status_code=200)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    audit_context: AuditContext = Depends(get_audit_context),
) -> dict:
    """Change the current user's password."""
    audit_context.actor_id = current_user.id
    audit_context.organization_id = current_user.organization_id
    service = AuthService(db, audit_context=audit_context)
    await service.change_password(current_user, request)
    return {"detail": "Contraseña actualizada exitosamente"}
