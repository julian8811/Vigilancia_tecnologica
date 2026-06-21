"""Analysis schemas — technologies, trends, actors, opportunities."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Technology ──────────────────────────────────────────────

class TechnologyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None = None
    category: str | None = None
    trl_level: int | None = None
    confidence: float | None = None
    evidence_score: float | None = None
    created_at: datetime


class TechnologyListResponse(BaseModel):
    items: list[TechnologyResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ── Trend ──────────────────────────────────────────────────

class TrendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None = None
    momentum: str | None = None
    trend_type: str | None = None
    growth_signal: str | None = None
    created_at: datetime


class TrendListResponse(BaseModel):
    items: list[TrendResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ── Actor ─────────────────────────────────────────────────

class ActorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    actor_type: str | None = None
    country: str | None = None
    relevance: float | None = None
    created_at: datetime


class ActorListResponse(BaseModel):
    items: list[ActorResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ── Opportunity ──────────────────────────────────────────

class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None = None
    opportunity_type: str | None = None
    potential: str | None = None
    effort: str | None = None
    priority: str | None = None
    created_at: datetime


class OpportunityListResponse(BaseModel):
    items: list[OpportunityResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ── Analysis Run ──────────────────────────────────────────

class AnalysisRunRequest(BaseModel):
    topic: str
    objective: str | None = None
    country: str | None = None


class AnalysisRunResponse(BaseModel):
    message: str
    technologies_found: int = 0
    trends_found: int = 0
    actors_found: int = 0
    opportunities_found: int = 0
    status: str = "completed"
