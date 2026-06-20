"""CollectionRun model — tracks external-source collection runs for a project."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CollectionRun(Base):
    """Tracks a single execution of document collection from an external source.

    Mirrors the GraphRun pattern — same lifecycle of pending → running →
    completed / failed with counters, error tracking, and metadata.
    """

    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="openalex | semantic_scholar | lens | web",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
        comment="pending | running | completed | failed",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    docs_found: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Total documents returned by the source",
    )
    docs_inserted: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Documents actually inserted (after dedup)",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="Arbitrary metadata (API version, query used, pages crawled)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped["SurveillanceProject"] = relationship(
        "SurveillanceProject", back_populates="collection_runs", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CollectionRun {self.id!r} source={self.source_name!r} status={self.status!r}>"
