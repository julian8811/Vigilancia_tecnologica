"""Celery task for collecting documents from external sources (OpenAlex etc.).

Follows the same ``AsyncTask`` pattern as ``graph_tasks.py`` — each task
runs in its own async event loop and uses the worker's dedicated DB engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select

from worker.app import app as celery_app
from worker.tasks.graph_tasks import AsyncTask, worker_session_factory

logger = logging.getLogger(__name__)

# Maximum documents to fetch per collection run
MAX_RESULTS_PER_RUN = 500

# Batch size for DB inserts
BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_checksum(doc: dict) -> str:
    """MD5 hash of the document *content* for deduplication.

    Uses the same fields that define a document's identity: title, abstract,
    authors, and DOI.
    """
    raw = "|".join([
        doc.get("title", "") or "",
        doc.get("abstract", "") or "",
        "|".join(doc.get("authors", []) or []),
        doc.get("doi", "") or "",
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_search_query(strategy: Any) -> str:
    """Construct an OpenAlex search query from a project's SearchStrategy.

    Priority: ``boolean_queries`` > ``keywords_en + keywords_es``.
    Falls back to ``"*"`` when the strategy has no keywords defined.
    """
    if strategy.boolean_queries and strategy.boolean_queries.strip():
        return strategy.boolean_queries.strip()[:500]

    parts: list[str] = []
    if strategy.keywords_en and strategy.keywords_en.strip():
        parts.append(strategy.keywords_en.strip())
    if strategy.keywords_es and strategy.keywords_es.strip():
        parts.append(strategy.keywords_es.strip())

    if parts:
        return " ".join(parts)[:500]

    return "*"


def _is_source_selected(strategy: Any, source_name: str) -> bool:
    """Check whether *source_name* appears in the strategy's selected sources."""
    raw = strategy.sources_selected or ""
    return source_name in [s.strip().lower() for s in raw.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@celery_app.task(base=AsyncTask, bind=True, name="collect_from_source")
async def collect_from_source(self, run_id: str) -> dict:
    """Execute document collection from an external source.

    Reads a ``CollectionRun`` record, resolves the associated project and
    search strategy, instantiates the appropriate connector, fetches
    documents, deduplicates against existing project documents, and batch-
    inserts new ones.

    Parameters
    ----------
    run_id : str
        UUID of the ``CollectionRun`` to execute.
    """
    run_uuid = uuid.UUID(run_id)
    logger.info("collect_from_source_started", run_id=run_id)

    async with worker_session_factory() as db:
        try:
            # ── 1. Resolve the CollectionRun ─────────────────────────────
            from app.models.collection_run import CollectionRun

            run = await db.get(CollectionRun, run_uuid)
            if run is None:
                logger.error("collection_run_not_found", run_id=run_id)
                return {"error": f"CollectionRun {run_id} not found", "status": "failed"}

            # ── 2. Mark as running ───────────────────────────────────────
            run.status = "running"
            run.started_at = datetime.now(UTC)
            await db.flush()
            logger.info("collection_run_started", run_id=run_id, source=run.source_name)

            # ── 3. Resolve project + search strategy ─────────────────────
            from app.models.search_strategy import SearchStrategy
            from app.models.project import SurveillanceProject

            project = await db.get(SurveillanceProject, run.project_id)
            if project is None:
                raise RuntimeError(f"Project {run.project_id} not found for run {run_id}")

            # SearchStrategy is a one-to-one — load it directly
            result = await db.execute(
                select(SearchStrategy).where(SearchStrategy.project_id == run.project_id)
            )
            strategy = result.scalar_one_or_none()
            if strategy is None:
                raise RuntimeError(f"Project {run.project_id} has no SearchStrategy")

            # ── 4. Validate source selection ─────────────────────────────
            if not _is_source_selected(strategy, run.source_name):
                raise RuntimeError(
                    f"Source '{run.source_name}' is not in project's sources_selected "
                    f"({strategy.sources_selected})"
                )

            # ── 5. Build query & instantiate connector ───────────────────
            query = _build_search_query(strategy)
            logger.info(
                "collection_query_built",
                run_id=run_id,
                source=run.source_name,
                query=query[:200],
            )

            if run.source_name == "openalex":
                from worker.connectors.openalex import OpenAlexConnector

                connector = OpenAlexConnector()
            else:
                raise ValueError(f"Unsupported source: {run.source_name}")

            # ── 6. Pre-load existing docs for dedup ──────────────────────
            from app.models.document import Document

            existing_result = await db.execute(
                select(Document).where(Document.project_id == run.project_id)
            )
            existing_docs = existing_result.scalars().all()

            existing_source_keys: set[tuple[str, str]] = {
                (d.source_name, d.source_id)
                for d in existing_docs
                if d.source_name and d.source_id
            }
            existing_dois: set[str] = {
                d.doi.lower()
                for d in existing_docs
                if d.doi
            }
            existing_checksums: set[str] = {
                d.checksum
                for d in existing_docs
                if d.checksum
            }

            logger.info(
                "collection_dedup_loaded",
                existing_docs=len(existing_docs),
                existing_source_keys=len(existing_source_keys),
                existing_dois=len(existing_dois),
            )

            # ── 7. Fetch & dedup ─────────────────────────────────────────
            docs_found = 0
            docs_inserted = 0
            new_documents: list[Document] = []

            try:
                async for raw_doc in connector.fetch(query, max_results=MAX_RESULTS_PER_RUN):
                    docs_found += 1

                    # 7a. Dedup by (source_name, source_id)
                    source_key = (raw_doc["source_name"], raw_doc["source_id"])
                    if source_key in existing_source_keys:
                        continue

                    # 7b. Dedup by DOI
                    doc_doi = raw_doc.get("doi")
                    if doc_doi and doc_doi.lower() in existing_dois:
                        continue

                    # 7c. Compute & dedup by checksum
                    checksum = _compute_checksum(raw_doc)
                    if checksum in existing_checksums:
                        continue

                    # ── All dedup checks passed — insert ─────────────────
                    document = Document(
                        project_id=run.project_id,
                        title=raw_doc.get("title"),
                        source_name=raw_doc["source_name"],
                        source_id=raw_doc.get("source_id"),
                        doi=doc_doi,
                        abstract=raw_doc.get("abstract"),
                        authors=raw_doc.get("authors"),
                        institutions=raw_doc.get("institutions"),
                        publication_year=raw_doc.get("publication_year"),
                        language=raw_doc.get("language"),
                        url=raw_doc.get("url"),
                        document_type=raw_doc.get("document_type", "paper"),
                        checksum=checksum,
                    )
                    new_documents.append(document)
                    docs_inserted += 1

                    # Track in-memory so subsequent iterations see what
                    # we've already inserted (same run cross-dedup).
                    existing_source_keys.add(source_key)
                    if doc_doi:
                        existing_dois.add(doc_doi.lower())
                    existing_checksums.add(checksum)

                    # 7d. Batch flush
                    if len(new_documents) >= BATCH_SIZE:
                        db.add_all(new_documents)
                        await db.flush()
                        logger.info(
                            "collection_batch_inserted",
                            batch_size=len(new_documents),
                            docs_found=docs_found,
                            docs_inserted=docs_inserted,
                        )
                        new_documents.clear()

                # ── Flush remaining ─────────────────────────────────────
                if new_documents:
                    db.add_all(new_documents)
                    await db.flush()
                    logger.info(
                        "collection_final_batch_inserted",
                        batch_size=len(new_documents),
                    )

            finally:
                await connector.close()

            # ── 8. Mark completed ────────────────────────────────────────
            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            run.docs_found = docs_found
            run.docs_inserted = docs_inserted
            run.metadata_json = {
                "query": query[:500],
                "source": run.source_name,
                "max_results": MAX_RESULTS_PER_RUN,
            }
            await db.flush()

            logger.info(
                "collect_from_source_completed",
                run_id=run_id,
                docs_found=docs_found,
                docs_inserted=docs_inserted,
            )

            return {
                "status": "completed",
                "docs_found": docs_found,
                "docs_inserted": docs_inserted,
            }

        except Exception as exc:
            logger.exception("collect_from_source_failed", run_id=run_id)
            try:
                from app.models.collection_run import CollectionRun

                run = await db.get(CollectionRun, run_uuid)
                if run:
                    run.status = "failed"
                    run.error_message = str(exc)[:2000]
                    run.finished_at = datetime.now(UTC)
                    await db.flush()
            except Exception:
                logger.exception("collection_run_status_update_failed", run_id=run_id)

            return {"error": str(exc), "status": "failed"}
