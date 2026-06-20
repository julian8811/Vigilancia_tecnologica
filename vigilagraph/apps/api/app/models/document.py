"""Document and DocumentChunk models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
except ImportError:
    Vector = None  # type: ignore[assignment,misc]


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="paper | patent | webpage | report | standard | thesis | book | dataset | manual_upload | other",
    )
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="External ID from OpenAlex / Semantic Scholar / Lens")
    source_name: Mapped[str] = mapped_column(
        String(50), server_default="manual_upload", nullable=False,
        comment="manual_upload | openalex | semantic_scholar | lens | web",
    )
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, comment="List of author strings")
    institutions: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, comment="List of institution strings")
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="html | pdf | markdown | docx | json",
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Path in S3 object storage",
    )
    text_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Path to extracted text in corpus",
    )
    checksum: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="MD5 hash for deduplication",
    )
    processing_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
        comment="pending | extracting | extracted | failed",
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped["SurveillanceProject"] = relationship(
        "SurveillanceProject", back_populates="documents", lazy="selectin",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Document {self.title!r} project={self.project_id!r}>"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped["Vector | None"] = mapped_column(
        Vector(1536), nullable=True,
        comment="OpenAI text-embedding-ada-002 embedding (1536 dims)",
    )

    # ── Relationships ─────────────────────────────────────────────
    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id!r} idx={self.chunk_index}>"
