"""SearchStrategy model — keyword and source configuration per project."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SearchStrategy(Base):
    __tablename__ = "search_strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), unique=True, nullable=False,
    )
    keywords_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[str | None] = mapped_column(Text, nullable=True)
    excluded_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources_selected: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="openalex | semantic_scholar | lens | web",
    )
    boolean_queries: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped["SurveillanceProject"] = relationship(
        "SurveillanceProject", back_populates="search_strategy", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SearchStrategy project={self.project_id!r}>"
