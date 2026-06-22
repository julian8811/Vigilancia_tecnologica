"""Corpus schemas — corpus entry and summary models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CorpusEntry(BaseModel):
    """A single document entry in the corpus."""
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    title: str | None = None
    file_type: str | None = None
    file_path: str | None = None
    text_path: str | None = None
    processing_status: str
    in_corpus: bool = False


class CorpusSummary(BaseModel):
    """Corpus summary for a project."""
    project_id: uuid.UUID
    total_documents: int
    extracted_documents: int
    pending_documents: int
    failed_documents: int
    corpus_ready: bool
    corpus_path: str | None = None
    corpus_size_bytes: int | None = None
    entries: list[CorpusEntry] = Field(default_factory=list)
    last_rebuild_at: datetime | None = None
