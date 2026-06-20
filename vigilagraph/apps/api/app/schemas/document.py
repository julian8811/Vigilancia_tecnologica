"""Document schemas — request/response for document CRUD and upload."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    """Payload for creating a document record (manual or from external source)."""
    title: str | None = Field(None, description="Optional display title")
    document_type: str | None = Field(
        None, description="paper | patent | webpage | report | standard | thesis | book | dataset | manual_upload | other",
    )
    url: str | None = None
    doi: str | None = Field(None, description="External ID from OpenAlex / Semantic Scholar / Lens")
    source_id: str | None = None
    abstract: str | None = None
    authors: list[str] | None = None
    institutions: list[str] | None = None
    publication_year: int | None = None
    language: str | None = None
    checksum: str | None = None
    file_path: str | None = None
    text_path: str | None = None


class DocumentUpdate(BaseModel):
    """Payload for updating a document (all fields optional)."""
    title: str | None = None
    document_type: str | None = None
    url: str | None = None
    doi: str | None = None
    source_id: str | None = None
    abstract: str | None = None
    authors: list[str] | None = None
    institutions: list[str] | None = None
    publication_year: int | None = None
    language: str | None = None


class DocumentResponse(BaseModel):
    """Full document read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str | None = None
    document_type: str | None = None
    url: str | None = None
    doi: str | None = None
    source_id: str | None = None
    abstract: str | None = None
    authors: list[str] | None = None
    institutions: list[str] | None = None
    publication_year: int | None = None
    language: str | None = None
    file_type: str | None = None
    file_path: str | None = None
    text_path: str | None = None
    checksum: str | None = None
    processing_status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated document list wrapper."""
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadResponse(BaseModel):
    """Response returned after a document upload request."""
    message: str
    document: DocumentResponse
    text_extracted: bool = False
    text_length: int | None = None


class AddUrlRequest(BaseModel):
    """Payload for adding a URL as a document source."""
    url: str = Field(..., description="Target URL to track")
    title: str | None = Field(None, description="Optional display title")


class DocumentChunkResponse(BaseModel):
    """Document chunk read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
