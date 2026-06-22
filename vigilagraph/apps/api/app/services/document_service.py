"""Document service — business logic for document upload, CRUD, and lifecycle."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.extractors.pdf import PDFExtractionResult, PDFExtractor
from app.core.storage import StorageService
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import (
    AddUrlRequest,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

logger = get_logger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = frozenset({".pdf", ".txt", ".md", ".json", ".html", ".xml"})
PDF_MAGIC = b"%PDF"


class DocumentService:
    """Encapsulates business logic for surveillance-source documents."""

    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self.db = db
        self.repo = DocumentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.storage = storage
        self.pdf_extractor = PDFExtractor()

    async def list_documents(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        document_type: str | None = None,
        processing_status: str | None = None,
    ) -> DocumentListResponse:
        """List documents for a project (with org-boundary check)."""
        project = await self._get_project_or_404(project_id, org_id)
        items, total = await self.repo.list_by_project(
            project_id,
            page=page,
            page_size=page_size,
            document_type=document_type,
            processing_status=processing_status,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return DocumentListResponse(
            items=[DocumentResponse.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def upload_pdf(
        self,
        project_id: uuid.UUID,
        org_id: uuid.UUID,
        file: UploadFile,
    ) -> DocumentUploadResponse:
        """Upload a file and create a new document.

        Flow
        1. Validate project belongs to the org
        2. Validate file extension
        3. Read all bytes (checks size limit)
        4. Validate PDF magic bytes for ``.pdf`` files
        5. Calculate MD5 checksum
        6. Reject duplicate checksums within the project
        7. Create the ``Document`` record (status = ``extracting``)
        8. Upload the original file to S3
        9. Extract text via ``PDFExtractor`` (PDF only for now)
        10. Upload extracted text to S3
        11. Mark document as ``extracted`` with paths and metadata

        If any step after #7 fails the DB session is rolled back by the
        caller's ``get_db`` dependency, so the partial document record is
        never committed.
        """
        project = await self._get_project_or_404(project_id, org_id)

        # Validate extension
        ext = self._validate_file_extension(file.filename or "unknown.pdf")

        # Read bytes (with size check)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE // (1024*1024)} MB limit")

        # Validate PDF header
        if ext == ".pdf":
            self._validate_pdf_magic(content)

        # Checksum
        checksum = hashlib.md5(content).hexdigest()

        # Dedup
        existing = await self.repo.get_by_checksum(project_id, checksum)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A document with the same content already exists in this project: '{existing.title or existing.id}'",
            )

        # Create document record (status = extracting)
        doc = Document(
            project_id=project_id,
            title=file.filename or "untitled",
            file_type=ext.lstrip("."),
            checksum=checksum,
            processing_status="extracting",
        )
        self.db.add(doc)
        await self.db.flush()

        # Upload original file to S3
        doc_id = doc.id
        file_key = f"projects/{project_id}/documents/{doc_id}/original{ext}"
        await self.storage.upload_bytes(
            content=content,
            key=file_key,
            content_type=file.content_type or "application/octet-stream",
        )
        doc.file_path = file_key

        # Extract text (PDF only for MVP)
        text_result = self._empty_extraction()
        text_extracted = False
        if ext == ".pdf":
            try:
                text_result = await self.pdf_extractor.extract_from_bytes(content)
                text_extracted = True
            except Exception:
                logger.exception("pdf_extraction_failed", document_id=doc_id)

            # Upload extracted text
            if text_result.text.strip():
                text_key = f"projects/{project_id}/documents/{doc_id}/extracted.md"
                await self.storage.upload_text(
                    content=text_result.text,
                    key=text_key,
                )
                doc.text_path = text_key
                doc.processing_status = "extracted"
            else:
                logger.warning("document_extraction_empty", document_id=doc_id)
                doc.processing_status = "extracted"
                doc.metadata_json = {"extraction_warning": "No extractable text found"}

            # Store PDF metadata
            meta = {}
            if text_result.metadata:
                meta["pdf_metadata"] = text_result.metadata
            if text_result.page_count:
                meta["page_count"] = text_result.page_count
            if text_result.title:
                meta["pdf_title"] = text_result.title
            if meta:
                doc.metadata_json = {**(doc.metadata_json or {}), **meta}
        else:
            # Non-PDF: mark as extracted with the raw content
            text_key = f"projects/{project_id}/documents/{doc_id}/content.txt"
            await self.storage.upload_text(
                content=content.decode("utf-8", errors="replace"),
                key=text_key,
            )
            doc.text_path = text_key
            doc.processing_status = "extracted"

        await self.db.flush()
        await self.db.refresh(doc)

        logger.info(
            "document_uploaded",
            document_id=doc.id,
            project_id=project_id,
            ext=ext,
            checksum=checksum,
            text_extracted=text_extracted,
        )

        return DocumentUploadResponse(
            message="Document uploaded successfully",
            document=DocumentResponse.model_validate(doc),
            text_extracted=text_extracted,
            text_length=len(text_result.text) if text_extracted else None,
        )

    async def add_url(self, project_id: uuid.UUID, org_id: uuid.UUID, body: AddUrlRequest) -> DocumentResponse:
        """Add a URL as a document source.

        Creates a document with ``document_type='webpage'`` and
        ``processing_status='pending'``.         Actual web fetching is handled asynchronously.
        """
        project = await self._get_project_or_404(project_id, org_id)

        doc = Document(
            project_id=project_id,
            title=body.title or body.url,
            file_type="html",
            checksum=None,
            processing_status="pending",
            metadata_json={"source_url": body.url, "document_type": "webpage"},
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)

        logger.info("url_added_as_document", document_id=doc.id, url=body.url)
        return DocumentResponse.model_validate(doc)

    async def get_document(self, document_id: uuid.UUID, org_id: uuid.UUID) -> DocumentResponse:
        """Return a document, verifying it belongs to the user's org.

        The org boundary check works by resolving the document's project
        and verifying the project belongs to *org_id*.
        """
        doc = await self.repo.get(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Org boundary check via project
        project = await self.project_repo.get_with_org_check(doc.project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Document not found")

        return DocumentResponse.model_validate(doc)

    async def delete_document(self, document_id: uuid.UUID, org_id: uuid.UUID) -> None:
        """Delete a document, its S3 files, and its chunks.

        S3 deletion is best-effort — the DB record is always removed.
        """
        doc = await self.repo.get(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        project = await self.project_repo.get_with_org_check(doc.project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Best-effort S3 cleanup
        s3_paths = [p for p in [doc.file_path, doc.text_path] if p]
        if s3_paths:
            try:
                await self.storage.delete_files(s3_paths)
            except Exception:
                logger.exception("s3_delete_failed", document_id=document_id, paths=s3_paths)

        await self.db.delete(doc)
        await self.db.flush()
        logger.info("document_deleted", document_id=document_id)

    async def reprocess_document(self, document_id: uuid.UUID, org_id: uuid.UUID) -> DocumentResponse:
        """Reset ``processing_status`` to ``pending`` for reprocessing.

        The actual reprocessing triggers asynchronously.
        """
        doc = await self.repo.get(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        project = await self.project_repo.get_with_org_check(doc.project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Document not found")

        doc.processing_status = "pending"
        await self.db.flush()
        await self.db.refresh(doc)

        logger.info("document_reprocess_queued", document_id=document_id)
        return DocumentResponse.model_validate(doc)

    # ── Internal helpers ──────────────────────────────────────────

    async def _get_project_or_404(self, project_id: uuid.UUID, org_id: uuid.UUID):
        """Return the project if it belongs to *org_id*, otherwise 404.

        Uses ``ProjectRepository.get_with_org_check`` for the boundary
        check so the caller never sees projects from other orgs.
        """
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @staticmethod
    def _validate_file_extension(filename: str) -> str:
        """Raise 400 if the extension is not in the allowed set.

        Returns the lower-cased extension.
        """
        ext = Path(filename).suffix.lower().strip()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        return ext

    @staticmethod
    def _validate_pdf_magic(content: bytes) -> None:
        """Raise 400 if the bytes do not start with the PDF header."""
        if not content.startswith(PDF_MAGIC):
            raise HTTPException(status_code=400, detail="Invalid PDF file: missing PDF header (%PDF)")

    @staticmethod
    def _empty_extraction() -> PDFExtractionResult:
        """Return an empty extraction result (no text found)."""
        return PDFExtractionResult(text="", metadata={}, page_count=0, title=None)
