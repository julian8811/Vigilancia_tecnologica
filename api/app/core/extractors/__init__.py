"""Text extractors for supported document formats."""

from __future__ import annotations

from app.core.extractors.pdf import PDFExtractionResult, PDFExtractor

__all__ = [
    "PDFExtractionResult",
    "PDFExtractor",
]
