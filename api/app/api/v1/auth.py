"""Auth router — registration, login, and password management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_audit_context, get_current_active_user, get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    audit_context: AuditContext = Depends(get_audit_context),
) -> TokenResponse:
    """Register a new user account.

    Rate-limited to 5 attempts per minute per client IP. The auth_service
    also logs every attempt with the email for downstream brute-force
    detection (see auth_service.login / register).
    """
    service = AuthService(db, audit_context=audit_context)
    return await service.register(body)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    audit_context: AuditContext = Depends(get_audit_context),
) -> TokenResponse:
    """Authenticate and return a JWT.

    Rate-limited to 5 attempts per minute per client IP. Repeated failures
    are logged with the attempted email and source IP — alert on this in
    production.
    """
    service = AuthService(db, audit_context=audit_context)
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
    audit_context: AuditContext = Depends(get_audit_context),
) -> dict:
    """Change the current user's password."""
    # The audit context needs the actor's org even though the change
    # is initiated by an authenticated user. Carry it over so the
    # row has the same shape as login_success.
    audit_context.actor_id = current_user.id
    audit_context.organization_id = current_user.organization_id
    service = AuthService(db, audit_context=audit_context)
    await service.change_password(current_user, request)
    return {"detail": "Contraseña actualizada exitosamente"}
