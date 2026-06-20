"""SurveillanceProject schemas — request/response for project CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Payload for creating a new surveillance project.

    If ``slug`` is omitted it is auto-generated from ``title``.
    """
    name: str
    slug: str | None = Field(None, pattern=r"^[a-z0-9-]+$")
    topic: str | None = None
    description: str | None = None
    surveillance_type: str | None = Field(
        None, description="tecnologica | cientifica | competitiva | patentaria | normativa | mercado | academica | mixta",
    )
    language: str = "es"
    objective: str | None = None
    scope: str | None = None
    country_focus: str | None = None


class ProjectUpdate(BaseModel):
    """Payload for updating an existing project (all fields optional)."""
    name: str | None = None
    slug: str | None = Field(None, pattern=r"^[a-z0-9-]+$")
    topic: str | None = None
    description: str | None = None
    surveillance_type: str | None = None
    language: str | None = None
    status: str | None = None
    objective: str | None = None
    scope: str | None = None
    country_focus: str | None = None


class ProjectResponse(BaseModel):
    """Full project read model returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    topic: str | None = None
    description: str | None = None
    surveillance_type: str | None = None
    language: str
    status: str
    organization_id: uuid.UUID
    created_by: uuid.UUID | None = None
    objective: str | None = None
    scope: str | None = None
    country_focus: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated project list wrapper."""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
