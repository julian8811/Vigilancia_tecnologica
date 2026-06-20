"""CollectionRun schemas — request/response for external-source collection runs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollectionRunResponse(BaseModel):
    """External-source collection run read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_name: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    docs_found: int = 0
    docs_inserted: int = 0
    error_message: str | None = None
    metadata_json: dict | None = None
    created_at: datetime


class CollectionRunListResponse(BaseModel):
    """Paginated collection-run list wrapper."""
    items: list[CollectionRunResponse]
    total: int
