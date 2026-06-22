"""Organization schemas — request/response for tenant management."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    """Payload for creating a new organisation."""
    name: str
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    type: str | None = Field(None, description="university | company | research_group | consultancy | government | other")
    website: str | None = None
    country: str | None = None


class OrganizationUpdate(BaseModel):
    """Payload for updating an existing organisation (all fields optional)."""
    name: str | None = None
    slug: str | None = Field(None, pattern=r"^[a-z0-9-]+$")
    type: str | None = None
    website: str | None = None
    country: str | None = None


class OrganizationResponse(BaseModel):
    """Organisation read model returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    type: str | None = None
    website: str | None = None
    country: str | None = None
    created_at: datetime
    updated_at: datetime
