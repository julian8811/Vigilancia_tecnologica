"""PDF text extraction using PyMuPDF (``fitz``)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import fitz
from structlog import get_logger

logger = get_logger(__name__)


@dataclass
class PDFExtractionResult:
    """Structured result of a PDF text-extraction pass."""
    text: str
    metadata: dict = field(default_factory=dict)
    page_count: int = 0
    title: str | None = None


class PDFExtractor:
    """Extract text and metadata from PDF files using PyMuPDF.

    All public methods are async-safe — the CPU-bound PyMuPDF calls run in
    the default thread-pool executor.
    """

    async def extract_from_bytes(self, content: bytes) -> PDFExtractionResult:
        """Extract text from an in-memory PDF byte buffer.

        This is the primary method used during document upload (the file
        bytes are already in memory for checksumming).
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_from_bytes_sync, content)

    async def extract_from_path(self, file_path: str | Path) -> PDFExtractionResult:
        """Open a PDF from the filesystem, extract text + metadata.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            A :class:`PDFExtractionResult` with full text, PDF metadata,
            and page count.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_from_path, str(file_path))

    def _extract_from_bytes_sync(self, content: bytes) -> PDFExtractionResult:
        """Open a PDF from *content* bytes, extract, close."""
        doc = fitz.open(stream=content, filetype="pdf")
        try:
            return self._process_document(doc)
        finally:
            doc.close()

    def _extract_from_path(self, file_path: str) -> PDFExtractionResult:
        """Open a PDF file, extract, close."""
        doc = fitz.open(file_path)
        try:
            return self._process_document(doc)
        finally:
            doc.close()

    def _process_document(self, doc: fitz.Document) -> PDFExtractionResult:
        """Extract text from every page and collect metadata."""
        full_text: list[str] = []
        metadata: dict = {}

        # PDF metadata
        raw_meta = doc.metadata or {}
        metadata = {
            k: v for k, v in raw_meta.items()
            if v is not None
        }

        # Extract page text
        for page_num, page in enumerate(doc):
            try:
                page_text = page.get_text()
                if page_text:
                    full_text.append(f"\n[Page {page_num + 1}]\n{page_text}")
            except Exception:
                logger.warning("pdf_page_extraction_failed", page_num=page_num)
                full_text.append(f"\n[Page {page_num + 1} — extraction failed]\n")

        page_count = len(doc)
        title = metadata.get("title")

        logger.info(
            "pdf_extraction_complete",
            page_count=page_count,
            text_length=len("".join(full_text)),
            has_title=title is not None,
        )

        return PDFExtractionResult(
            text="".join(full_text),
            metadata=metadata,
            page_count=page_count,
            title=title,
        )
