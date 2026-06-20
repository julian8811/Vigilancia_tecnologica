"""Analysis schemas — technologies, trends, actors, opportunities."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TechnologyResponse(BaseModel):
    """Extracted technology read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None = None
    confidence: float | None = None
    category: str | None = None
    trl_level: int | None = None
    evidence_score: float | None = None
    created_at: datetime


class TrendResponse(BaseModel):
    """Identified trend read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None = None
    momentum: str | None = None
    trend_type: str | None = None
    growth_signal: str | None = None
    evidence: dict | None = None
    created_at: datetime


class ActorResponse(BaseModel):
    """Key actor read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    actor_type: str | None = None
    relevance: float | None = None
    country: str | None = None
    created_at: datetime


class OpportunityResponse(BaseModel):
    """Identified opportunity read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None = None
    opportunity_type: str | None = None
    potential: str | None = None
    effort: str | None = None
    priority: str | None = None
    recommended_actions: dict | None = None
    related_documents: list[str] | None = None
    related_nodes: list[str] | None = None
    created_at: datetime


class AnalysisRunResponse(BaseModel):
    """Response returned after triggering an analysis extraction run."""
    message: str
    status: str = "queued"
