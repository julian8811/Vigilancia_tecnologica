"""Corpus service — manages the local file corpus for Graphify processing."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, UTC
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.corpus import CorpusEntry, CorpusSummary

logger = get_logger(__name__)


class CorpusService:
    """Manages the local corpus folder used as input for Graphify.

    The corpus lives at ``{STORAGE_LOCAL_PATH}/corpora/{project_id}/`` and
    contains one subdirectory per document with the extracted text and
    metadata.  Graphify reads this folder to build the knowledge graph.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.project_repo = ProjectRepository(db)
        self._base_path = Path(settings.STORAGE_LOCAL_PATH) / "corpora"

    # ── Public API ────────────────────────────────────────────────

    async def summary(self, project_id: uuid.UUID, org_id: uuid.UUID) -> CorpusSummary:
        """Return a summary of the current corpus state for a project."""
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        docs, total = await self.doc_repo.list_by_project(project_id, page=1, page_size=10000)
        corpus_path = self._corpus_path(project_id)
        corpus_exists = corpus_path.exists()

        # Count by status
        extracted = sum(1 for d in docs if d.processing_status == "extracted")
        pending = sum(1 for d in docs if d.processing_status == "pending")
        failed = sum(1 for d in docs if d.processing_status == "failed")

        # Corpus entries
        entries = []
        for doc in docs:
            in_corpus = False
            if corpus_exists and doc.id:
                doc_dir = corpus_path / str(doc.id)
                in_corpus = doc_dir.exists() and (doc_dir / "text.md").exists()
            entries.append(
                CorpusEntry(
                    document_id=doc.id,
                    title=doc.title,
                    file_type=doc.file_type,
                    file_path=doc.file_path,
                    text_path=doc.text_path,
                    processing_status=doc.processing_status,
                    in_corpus=in_corpus,
                )
            )

        # Corpus size
        corpus_size = 0
        if corpus_exists:
            for f in corpus_path.rglob("*"):
                if f.is_file():
                    corpus_size += f.stat().st_size

        # Last rebuild from metadata file
        last_rebuild = None
        meta_path = corpus_path / ".corpus_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                last_rebuild_str = meta.get("last_rebuild_at")
                if last_rebuild_str:
                    last_rebuild = datetime.fromisoformat(last_rebuild_str)
            except (json.JSONDecodeError, OSError):
                pass

        return CorpusSummary(
            project_id=project_id,
            total_documents=total,
            extracted_documents=extracted,
            pending_documents=pending,
            failed_documents=failed,
            corpus_ready=corpus_exists and extracted > 0,
            corpus_path=str(corpus_path) if corpus_exists else None,
            corpus_size_bytes=corpus_size or None,
            entries=entries,
            last_rebuild_at=last_rebuild,
        )

    async def rebuild(self, project_id: uuid.UUID, org_id: uuid.UUID) -> CorpusSummary:
        """Rebuild the corpus folder from extracted documents.

        For each extracted document:
          1. Create ``{corpus_path}/{doc_id}/``
          2. Download the extracted text from S3 (or use local copy)
          3. Write ``text.md``
          4. Write ``metadata.json`` with title, type, etc.
        """
        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        docs, total = await self.doc_repo.list_by_project(project_id, page=1, page_size=10000)
        extracted_docs = [d for d in docs if d.processing_status == "extracted" and d.text_path]

        corpus_path = self._corpus_path(project_id)
        corpus_path.mkdir(parents=True, exist_ok=True)

        # Remove existing content (keep .corpus_meta.json)
        for item in corpus_path.iterdir():
            if item.name != ".corpus_meta.json":
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        from app.core.storage import StorageService
        storage = StorageService()

        added = 0
        for doc in extracted_docs:
            try:
                doc_dir = corpus_path / str(doc.id)
                doc_dir.mkdir(parents=True, exist_ok=True)

                # Download extracted text from S3
                text_content = await storage.download_file(doc.text_path)
                (doc_dir / "text.md").write_text(text_content, encoding="utf-8")

                # Write metadata
                meta = {
                    "document_id": str(doc.id),
                    "title": doc.title,
                    "file_type": doc.file_type,
                    "processing_status": doc.processing_status,
                    "checksum": doc.checksum,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                if doc.metadata_json:
                    meta.update(doc.metadata_json)
                (doc_dir / "metadata.json").write_text(
                    json.dumps(meta, indent=2, default=str), encoding="utf-8",
                )

                added += 1
            except Exception:
                logger.exception(
                    "corpus_rebuild_doc_failed",
                    project_id=project_id,
                    document_id=doc.id,
                )

        # Write corpus metadata
        corpus_meta = {
            "project_id": str(project_id),
            "last_rebuild_at": datetime.now(UTC).isoformat(),
            "total_documents": total,
            "extracted_included": added,
        }
        (corpus_path / ".corpus_meta.json").write_text(
            json.dumps(corpus_meta, indent=2), encoding="utf-8",
        )

        logger.info(
            "corpus_rebuilt",
            project_id=project_id,
            total_docs=total,
            extracted_included=added,
        )

        return await self.summary(project_id, org_id)

    async def ready(self, project_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        """Return ``True`` when the corpus exists and has at least one document."""
        summary = await self.summary(project_id, org_id)
        return summary.corpus_ready

    async def seed_test_docs(self, project_id: uuid.UUID, org_id: uuid.UUID, count: int = 3) -> list[CorpusEntry]:
        """Seed the corpus with test documents for development/demo purposes.

        Creates placeholder extracted documents directly in the corpus folder
        without going through S3 upload.  Only works in development mode.
        """
        if not settings.is_development:
            raise HTTPException(status_code=403, detail="Test seeding is only available in development mode")

        project = await self.project_repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        corpus_path = self._corpus_path(project_id)
        corpus_path.mkdir(parents=True, exist_ok=True)

        sample_texts = [
            (
                "Artificial Intelligence in Healthcare",
                "Machine learning algorithms are revolutionizing medical diagnosis. "
                "Deep learning models can detect anomalies in medical imaging with "
                "accuracy exceeding human experts. Natural language processing enables "
                "automated analysis of clinical notes and research literature.",
            ),
            (
                "Quantum Computing Advances",
                "Recent breakthroughs in quantum error correction have brought us closer "
                "to fault-tolerant quantum computers. Superconducting qubits and trapped "
                "ion systems continue to lead in qubit count and coherence times. "
                "Quantum supremacy demonstrations show exponential speedup for specific problems.",
            ),
            (
                "Blockchain for Supply Chain",
                "Distributed ledger technology is transforming supply chain management. "
                "Smart contracts enable automated verification of goods movement and "
                "payment settlement. RFID integration with blockchain provides end-to-end "
                "product traceability from manufacturing to delivery.",
            ),
            (
                "Renewable Energy Storage",
                "Grid-scale battery storage is becoming economically viable for renewable "
                "energy integration. Solid-state batteries promise higher energy density "
                "and improved safety over lithium-ion. Hydrogen storage offers seasonal "
                "energy balancing for solar and wind power.",
            ),
            (
                "Synthetic Biology Innovations",
                "CRISPR-Cas9 gene editing continues to advance therapeutic applications. "
                "Synthetic gene circuits enable programmable cellular behavior for "
                "biomanufacturing. Metabolic engineering of microorganisms produces "
                "sustainable chemicals and materials.",
            ),
        ]

        created = []
        for i in range(min(count, len(sample_texts))):
            title, text = sample_texts[i]
            doc_id = uuid.uuid4()
            doc_dir = corpus_path / str(doc_id)
            doc_dir.mkdir(parents=True, exist_ok=True)

            # Write text
            (doc_dir / "text.md").write_text(text, encoding="utf-8")

            # Write metadata
            meta = {
                "document_id": str(doc_id),
                "title": title,
                "file_type": "txt",
                "processing_status": "extracted",
                "checksum": None,
                "is_test_doc": True,
            }
            (doc_dir / "metadata.json").write_text(
                json.dumps(meta, indent=2, default=str), encoding="utf-8",
            )

            created.append(
                CorpusEntry(
                    document_id=doc_id,
                    title=title,
                    file_type="txt",
                    processing_status="extracted",
                    in_corpus=True,
                )
            )

        # Write/update corpus metadata
        meta_path = corpus_path / ".corpus_meta.json"
        if meta_path.exists():
            corpus_meta = json.loads(meta_path.read_text())
        else:
            corpus_meta = {}
        corpus_meta["last_rebuild_at"] = datetime.now(UTC).isoformat()
        corpus_meta["has_test_docs"] = True
        corpus_meta["test_doc_count"] = len(created)
        meta_path.write_text(json.dumps(corpus_meta, indent=2), encoding="utf-8")

        logger.info("corpus_seeded_with_test_docs", project_id=project_id, count=len(created))
        return created

    # ── Internal helpers ──────────────────────────────────────────

    def _corpus_path(self, project_id: uuid.UUID) -> Path:
        """Return the local corpus folder for a project."""
        return self._base_path / str(project_id)
