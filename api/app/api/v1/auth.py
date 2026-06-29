"""Auth router — registration, login, and password management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db
from app.main import limiter
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account.

    Rate-limited to 5 attempts per minute per client IP. The auth_service
    also logs every attempt with the email for downstream brute-force
    detection (see auth_service.login / register).
    """
    service = AuthService(db)
    return await service.register(body)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return a JWT.

    Rate-limited to 5 attempts per minute per client IP. Repeated failures
    are logged with the attempted email and source IP — alert on this in
    production.
    """
    service = AuthService(db)
    return await service.login(body)


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
