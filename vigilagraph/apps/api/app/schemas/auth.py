"""Auth schemas — registration, login, and token responses."""

from __future__ import annotations

from datetime import datetime

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


class TokenResponse(BaseModel):
    """JWT access-token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    """Payload for changing the current user's password."""
    old_password: str
    new_password: str
