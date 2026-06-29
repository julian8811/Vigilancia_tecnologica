"""Auth router — registration, login, refresh, and logout.

Tokens are delivered via httpOnly cookies (`vg_access`, `vg_refresh`)
on the `Set-Cookie` header — never in the response body. The body
carries only the user profile.

Flow:

  POST /auth/register   → 201, Set-Cookie: vg_access, vg_refresh, body={user}
  POST /auth/login      → 200, Set-Cookie: vg_access, vg_refresh, body={user}
  POST /auth/refresh    → 200, Set-Cookie: vg_access (rotated), body={user}
  POST /auth/logout     → 200, Set-Cookie: vg_access=; Max-Age=0, etc.
  GET  /auth/me         → 200, body={user}, no Set-Cookie
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.core.security import (
    clear_session_cookies,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
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
from app.services.auth_service import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["autenticación"])


def _build_session(user: User) -> SessionResponse:
    return SessionResponse(user=UserResponse.model_validate(user))


def _new_tokens(user: User) -> tuple[str, str]:
    subject = str(user.id)
    return create_access_token(subject), create_refresh_token(subject)


def _client_info(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/register", response_model=SessionResponse, status_code=201)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Register a new user account. Sets the session cookies on success."""
    ip, user_agent = _client_info(request)
    service = AuthService(db)
    user = await service.register_user(body)
    access, refresh = _new_tokens(user)
    set_session_cookies(response, access_token=access, refresh_token=refresh)
    logger.info("user_registered", user_id=str(user.id), email=user.email, ip=ip)
    return _build_session(user)


@router.post("/login", response_model=SessionResponse)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Authenticate. Sets the session cookies on success."""
    ip, user_agent = _client_info(request)
    service = AuthService(db)
    user, outcome = await service.login_user(body, ip=ip, user_agent=user_agent)
    if user is None:
        logger.info("login_failed", email=body.email, reason=outcome, ip=ip)
        raise HTTPException(status_code=401, detail="Correo o contraseña inválidos")

    access, refresh = _new_tokens(user)
    set_session_cookies(response, access_token=access, refresh_token=refresh)
    logger.info("login_success", user_id=str(user.id), email=user.email, ip=ip)
    return _build_session(user)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Issue a fresh access + refresh token pair.

    Reads the refresh token from the ``vg_refresh`` cookie. Both
    tokens are rotated on every call (the old refresh becomes
    useless the moment a new one is issued). On any failure the
    cookies are cleared and the caller must re-authenticate.
    """
    from uuid import UUID

    from app.repositories.user_repository import UserRepository

    refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError:
        clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="Sesión expirada")

    access, refresh = _new_tokens(user)
    set_session_cookies(response, access_token=access, refresh_token=refresh)
    return _build_session(user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    """Clear the session cookies. Idempotent — safe to call twice."""
    clear_session_cookies(response)
    return LogoutResponse()


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", status_code=200)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change the current user's password."""
    service = AuthService(db)
    await service.change_password(current_user, request)
    return {"detail": "Contraseña actualizada exitosamente"}
