"""SearchStrategy schemas — request/response for keyword configuration."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SearchStrategyCreate(BaseModel):
    """Payload for creating / replacing the search strategy for a project."""
    keywords_en: str | None = None
    keywords_es: str | None = None
    synonyms: str | None = None
    excluded_terms: str | None = None
    sources_selected: str | None = Field(
        None, description="openalex | semantic_scholar | lens | web",
    )
    boolean_queries: str | None = None
    generated_by_ai: bool = False


class SearchStrategyUpdate(BaseModel):
    """Payload for updating parts of a search strategy (all fields optional)."""
    keywords_en: str | None = None
    keywords_es: str | None = None
    synonyms: str | None = None
    excluded_terms: str | None = None
    sources_selected: str | None = None
    boolean_queries: str | None = None
    generated_by_ai: bool | None = None


class SearchStrategyResponse(BaseModel):
    """Search strategy read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    keywords_en: str | None = None
    keywords_es: str | None = None
    synonyms: str | None = None
    excluded_terms: str | None = None
    sources_selected: str | None = None
    boolean_queries: str | None = None
    generated_by_ai: bool
    created_at: datetime
    updated_at: datetime
