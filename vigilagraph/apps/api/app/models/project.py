"""SurveillanceProject model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SurveillanceProject(Base):
    __tablename__ = "surveillance_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    surveillance_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="tecnologica | cientifica | competitiva | patentaria | normativa | mercado | academica | mixta",
    )
    language: Mapped[str] = mapped_column(String(10), default="es", nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_focus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
        comment="draft | collecting | processing | graph_ready | report_ready | archived | failed",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="projects", lazy="selectin",
    )
    search_strategy: Mapped["SearchStrategy | None"] = relationship(
        "SearchStrategy", back_populates="project", uselist=False, lazy="selectin",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan", lazy="selectin",
    )
    graph_runs: Mapped[list["GraphRun"]] = relationship(
        "GraphRun", back_populates="project", cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        # Per-organisation unique slugs
        {"comment": "Surveillance projects belonging to an organisation."},
    )

    def __repr__(self) -> str:
        return f"<SurveillanceProject {self.slug!r}>"
