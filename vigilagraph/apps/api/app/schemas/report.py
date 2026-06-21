"""Report schemas — request/response for report generation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    title: str
    report_type: str = "complete"


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    report_type: str
    status: str
    format: str | None = None
    html_path: str | None = None
    pdf_path: str | None = None
    markdown_path: str | None = None
    error_message: str | None = None
    generated_at: datetime | None = None
    created_at: datetime


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
