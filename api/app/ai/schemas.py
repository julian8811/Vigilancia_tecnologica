"""Pydantic schemas for structured AI analysis outputs."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ── Search Strategy ──────────────────────────────────────────

class KeywordSuggestion(BaseModel):
    keyword: str = Field(description="Keyword or phrase")
    language: str = Field(description="es | en")
    category: str = Field(description="main | synonym | technical | commercial | scientific")


class SearchStrategyOutput(BaseModel):
    keywords_es: list[str] = Field(description="Keywords in Spanish")
    keywords_en: list[str] = Field(description="Keywords in English")
    synonyms: list[str] = Field(description="Technical synonyms")
    boolean_queries: list[str] = Field(description="Boolean search queries for APIs")
    excluded_terms: list[str] = Field(description="Terms to exclude")
    recommended_sources: list[str] = Field(description="Recommended source names")
    rationale: str = Field(description="Why this strategy was designed this way")


# ── Technology Extraction ────────────────────────────────────

class Technology(BaseModel):
    name: str = Field(description="Technology name")
    description: str = Field(description="Brief description")
    category: str = Field(description="Technology category")
    application: str = Field(description="Application area")
    evidence: str = Field(description="Textual evidence from document")
    confidence: float = Field(ge=0, le=1, default=0.5, description="Confidence score")


class TechnologyList(BaseModel):
    technologies: list[Technology]


# ── Trend Analysis ──────────────────────────────────────────

class Trend(BaseModel):
    name: str = Field(description="Trend name")
    description: str = Field(description="What this trend is about")
    trend_type: str = Field(description="emerging | growing | stable | declining | uncertain")
    growth_signal: str = Field(description="Evidence that supports this trend direction")
    documents_count: int = Field(default=1, description="Number of documents supporting it")
    impact: str = Field(description="Potential impact (high | medium | low)")


class TrendList(BaseModel):
    trends: list[Trend]


# ── Actor Extraction ───────────────────────────────────────

class Actor(BaseModel):
    name: str = Field(description="Actor name")
    actor_type: str = Field(description="author | institution | company | government | research_group | startup | ngo | funder")
    country: str | None = Field(default=None, description="Country")
    role: str = Field(description="Role or contribution in the field")
    evidence: str = Field(description="Evidence from the corpus")
    relevance: str = Field(description="high | medium | low")


class ActorList(BaseModel):
    actors: list[Actor]


# ── Opportunity Detection ──────────────────────────────────

class Opportunity(BaseModel):
    title: str = Field(description="Opportunity title")
    description: str = Field(description="Detailed description")
    opportunity_type: str = Field(
        description="research | commercial | technology_transfer | patent | funding | partnership | product_development | education | policy",
    )
    evidence: str = Field(description="Evidence supporting this opportunity")
    difficulty: str = Field(description="low | medium | high")
    impact: str = Field(description="low | medium | high")
    priority: str = Field(description="low | medium | high | critical")


class OpportunityList(BaseModel):
    opportunities: list[Opportunity]


# ─── Document Classification ────────────────────────────────

class DocumentClassification(BaseModel):
    relevant: bool = Field(description="Whether the document is relevant to the surveillance topic")
    relevance_score: float = Field(ge=0, le=1, default=0.5)
    category: str = Field(description="Document category")
    summary: str = Field(description="One-sentence summary")
    topics: list[str] = Field(description="Main topics discussed")


# ── Graph Node Enrichment ──────────────────────────────────

class GraphEnrichment(BaseModel):
    node_type: str = Field(description="technology | application | actor | trend | product | method | ...")
    summary: str = Field(description="Brief summary of what this node represents")
    relevance_score: float = Field(ge=0, le=1, default=0.5)
    trl_level: int | None = Field(default=None, ge=1, le=9, description="Technology Readiness Level 1-9")
