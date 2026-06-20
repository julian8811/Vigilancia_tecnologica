"""User schemas — request/response for user CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for creating a new user (admin endpoint)."""
    email: EmailStr
    name: str
    password: str
    organization_id: uuid.UUID | None = None
    role: str | None = Field(None, description="owner | admin | analyst | viewer")


class UserUpdate(BaseModel):
    """Payload for updating an existing user (all fields optional)."""
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role: str | None = None


class UserResponse(BaseModel):
    """User read model — never exposes password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    organization_id: uuid.UUID | None = None
    is_active: bool
    role: str | None = None
    created_at: datetime
    updated_at: datetime
