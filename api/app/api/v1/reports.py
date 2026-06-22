"""Reports router — CRUD, generation, and download endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, verify_project_org
from app.models.user import User
from app.schemas.report import ReportCreate, ReportListResponse, ReportResponse
from app.services.report_service import ReportService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/reports", tags=["informes"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> ReportListResponse:
    service = ReportService(db)
    items, total = await service.list_by_project(project_id, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    project_id: uuid.UUID,
    request: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> ReportResponse:
    service = ReportService(db)
    report = await service.generate(project_id, request.title, request.report_type)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> ReportResponse:
    service = ReportService(db)
    report = await service.get(report_id, project_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return ReportResponse.model_validate(report)


@router.post("/{report_id}/regenerate", response_model=ReportResponse)
async def regenerate_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> ReportResponse:
    service = ReportService(db)
    report = await service.generate(project_id, report_id=report_id)
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}")
async def delete_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> dict:
    service = ReportService(db)
    await service.delete(report_id, project_id)
    return {"detail": "Informe eliminado"}


@router.get("/{report_id}/download/{format}")
async def download_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    format: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> Response:
    service = ReportService(db)
    report = await service.get(report_id, project_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    format_lower = format.lower()
    if format_lower == "html":
        path_attr = "html_path"
        media_type = "text/html"
    elif format_lower == "markdown":
        path_attr = "markdown_path"
        media_type = "text/markdown"
    elif format_lower == "pdf":
        path_attr = "pdf_path"
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {format}")

    file_path = getattr(report, path_attr, None)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"No hay archivo {format} para este informe")

    try:
        content = Path(file_path).read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Archivo {format.upper()} no encontrado")

    return Response(content=content, media_type=media_type)
