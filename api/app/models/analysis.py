"""Analysis models — technologies, trends, actors, and opportunities."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime,  Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trl_level: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Technology Readiness Level 1-9",
    )
    evidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Technology {self.name!r}>"


class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    momentum: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="emerging | growing | stable | declining | uncertain",
    )
    trend_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    growth_signal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Trend {self.name!r}>"


class Actor(Base):
    __tablename__ = "actors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="author | institution | company | government | research_group | startup | ngo | funder",
    )
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Actor {self.name!r}>"


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="research | commercial | technology_transfer | patent | funding | partnership | product_development | education | policy",
    )
    potential: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="high | medium | low")
    effort: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="high | medium | low")
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    recommended_actions: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    related_documents: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, comment="UUIDs of related Document records")
    related_nodes: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, comment="UUIDs of related GraphNode records")
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Opportunity {self.title!r}>"
