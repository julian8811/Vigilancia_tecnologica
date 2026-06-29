"""Auth schemas — registration, login, refresh, and logout."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    """Payload for creating a new user account."""
    email: EmailStr
    name: str
    password: str
    organization_slug: str | None = Field(
        None, description="Slug of an existing organisation to join, or omitted for personal account",
    )


class LoginRequest(BaseModel):
    """Payload for authentication."""
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    """Payload for changing the current user's password."""
    old_password: str
    new_password: str


class SessionResponse(BaseModel):
    """Response for login, register, refresh, and /auth/me.

    The JWT itself is **not** in the body — it travels in an
    httpOnly cookie set by the response. The body carries the user
    profile plus the current CSRF token (when known) so the SPA
    can populate its first ``X-CSRF-Token`` header on a fresh
    client. The body is informational; the cookie is the source of
    truth.
    """

    model_config = ConfigDict(from_attributes=True)

    user: UserResponse
    csrf_token: str | None = None


class LogoutResponse(BaseModel):
    """Response for /auth/logout."""

    detail: str = "Sesión cerrada"
