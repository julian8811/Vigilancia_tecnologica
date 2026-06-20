"""Report schemas — request/response for AI-generated analysis reports."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    """Payload for requesting report generation."""
    title: str
    report_type: str | None = Field(
        None, description="completo | ejecutivo | academico | empresarial | patentario | comparativo",
    )
    format: str = Field("html", description="html | pdf | markdown | docx | json")


class ReportResponse(BaseModel):
    """Report read model returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    report_type: str | None = None
    status: str
    format: str
    content: dict | None = None
    html_path: str | None = None
    pdf_path: str | None = None
    markdown_path: str | None = None
    docx_path: str | None = None
    json_path: str | None = None
    generated_at: datetime | None = None
    generated_by: uuid.UUID | None = None
    created_at: datetime


class ReportListResponse(BaseModel):
    """Paginated report list wrapper."""
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
