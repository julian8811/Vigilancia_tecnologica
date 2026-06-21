"""Documents router — upload, list, get, delete, reprocess, and classify documents."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, verify_project_org
from app.core.storage import StorageService
from app.models.user import User
from app.schemas.document import (
    AddUrlRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.models.document import Document
from sqlalchemy import select
from app.services.ai_service import classify_document_batch

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


def _get_service(db: AsyncSession) -> DocumentService:
    """Return a fresh ``DocumentService`` instance for the request."""
    storage = StorageService()
    return DocumentService(db, storage)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    document_type: str | None = Query(None, description="Filter by document type (paper, patent, webpage, ...)"),
    processing_status: str | None = Query(None, description="Filter by processing status (pending, extracting, extracted, failed)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> DocumentListResponse:
    """List documents for a project (scoped to the user's organisation)."""
    service = _get_service(db)
    return await service.list_documents(
        project_id,
        current_user.organization_id,
        page=page,
        page_size=page_size,
        document_type=document_type,
        processing_status=processing_status,
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> DocumentUploadResponse:
    """Upload a PDF (or other supported document) to a project.

    The file is validated, checksummed, deduplicated, stored in S3, and
    (for PDFs) text-extracted automatically.
    """
    service = _get_service(db)
    return await service.upload_pdf(project_id, current_user.organization_id, file)


@router.post("/add-url", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_url_document(
    project_id: uuid.UUID,
    body: AddUrlRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> DocumentResponse:
    """Add a URL as a document source for a project.

    The URL is stored with ``processing_status='pending'``. Actual web
    fetching will be handled by a Celery worker (future change).
    """
    service = _get_service(db)
    return await service.add_url(project_id, current_user.organization_id, body)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> DocumentResponse:
    """Return a single document (org-bound via its project)."""
    service = _get_service(db)
    return await service.get_document(document_id, current_user.organization_id)


@router.delete("/{document_id}")
async def delete_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> dict:
    """Delete a document, its S3 files, and its chunks."""
    service = _get_service(db)
    await service.delete_document(document_id, current_user.organization_id)
    return {"detail": "Document deleted"}


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> DocumentResponse:
    """Reset a document's processing status to ``pending`` for reprocessing."""
    service = _get_service(db)
    return await service.reprocess_document(document_id, current_user.organization_id)


@router.post("/classify")
async def classify_documents_endpoint(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> dict:
    """Auto-classify documents by type using AI analysis of abstracts."""
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .where(Document.abstract.isnot(None))
        .limit(50)
    )
    docs = result.scalars().all()
    if not docs:
        return {"classified": 0, "total": 0}

    classified = await classify_document_batch(
        [(str(d.id), d.abstract or "", d.title or "") for d in docs]
    )
    for doc_id, doc_type in classified:
        doc = await db.get(Document, uuid.UUID(doc_id))
        if doc:
            doc.document_type = doc_type
    await db.flush()

    logger.info("documents_classified", project_id=project_id, count=len(classified))
    return {"classified": len(classified), "total": len(docs)}
