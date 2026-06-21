"""Collection runner — calls the worker's collection logic directly, no Celery.

Requires PYTHONPATH to include apps/api and apps/worker so imports work.
Limited to 25 docs per run for Vercel 10s timeout.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

logger = get_logger(__name__)

MAX_RESULTS_PER_RUN = 25
BATCH_SIZE = 10


async def run_collection(db: AsyncSession, run_id: str) -> None:
    """Execute document collection synchronously (replaces Celery task).

    This runs the worker's collection logic directly using the API's
    database session. It imports the worker's connectors at runtime.
    """
    run_uuid = uuid.UUID(run_id)
    logger.info("collection_started", run_id=run_id)

    try:
        from app.models.collection_run import CollectionRun
        from app.models.document import Document
        from app.models.project import SurveillanceProject
        from app.models.search_strategy import SearchStrategy
        from app.core.config import settings
        from worker.connectors.openalex import OpenAlexConnector
        from worker.connectors.semantic_scholar import SemanticScholarConnector
        from worker.connectors.lens import LensConnector
        from worker.connectors.web import WebScraperConnector, _parse_urls
        from worker.tasks.collection_tasks import (
            _build_search_query,
            _compute_checksum,
            _is_source_selected,
        )

        # Resolve run
        run = await db.get(CollectionRun, run_uuid)
        if run is None:
            logger.error("collection_run_not_found", run_id=run_id)
            return

        run.status = "running"
        run.started_at = datetime.now(UTC)
        await db.flush()

        # Resolve project + strategy
        project = await db.get(SurveillanceProject, run.project_id)
        if project is None:
            raise RuntimeError(f"Project {run.project_id} not found")

        result = await db.execute(
            select(SearchStrategy).where(SearchStrategy.project_id == run.project_id)
        )
        strategy = result.scalar_one_or_none()
        if strategy is None:
            raise RuntimeError(f"Project {run.project_id} has no SearchStrategy")

        if not _is_source_selected(strategy, run.source_name):
            raise RuntimeError(f"Source '{run.source_name}' not selected")

        query = _build_search_query(strategy)

        # Instantiate connector
        if run.source_name == "openalex":
            connector = OpenAlexConnector()
        elif run.source_name == "semantic_scholar":
            connector = SemanticScholarConnector(api_key=settings.SEMANTIC_SCHOLAR_API_KEY or None)
        elif run.source_name == "lens":
            if not settings.LENS_API_TOKEN:
                raise ValueError("LENS_API_TOKEN not configured")
            connector = LensConnector(api_token=settings.LENS_API_TOKEN)
        elif run.source_name == "web":
            connector = WebScraperConnector()
            urls = _parse_urls(strategy.scrape_urls)
            if not urls:
                raise ValueError("No URLs configured")
        else:
            raise ValueError(f"Unsupported source: {run.source_name}")

        # Pre-load existing docs for dedup
        existing_result = await db.execute(
            select(Document).where(Document.project_id == run.project_id)
        )
        existing_docs = existing_result.scalars().all()

        existing_source_keys = {(d.source_name, d.source_id) for d in existing_docs if d.source_name and d.source_id}
        existing_dois = {d.doi.lower() for d in existing_docs if d.doi}
        existing_checksums = {d.checksum for d in existing_docs if d.checksum}

        docs_found = 0
        docs_inserted = 0
        new_documents: list[Document] = []

        try:
            if run.source_name == "web":
                doc_stream = connector.scrape_urls(urls)
            else:
                doc_stream = connector.fetch(query, max_results=MAX_RESULTS_PER_RUN)

            async for raw_doc in doc_stream:
                docs_found += 1

                source_key = (raw_doc["source_name"], raw_doc["source_id"])
                if source_key in existing_source_keys:
                    continue

                doc_doi = raw_doc.get("doi")
                if doc_doi and doc_doi.lower() in existing_dois:
                    continue

                checksum = _compute_checksum(raw_doc)
                if checksum in existing_checksums:
                    continue

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

                existing_source_keys.add(source_key)
                if doc_doi:
                    existing_dois.add(doc_doi.lower())
                existing_checksums.add(checksum)

                if len(new_documents) >= BATCH_SIZE:
                    db.add_all(new_documents)
                    await db.flush()
                    new_documents.clear()

            if new_documents:
                db.add_all(new_documents)
                await db.flush()

        finally:
            await connector.close()

        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        run.docs_found = docs_found
        run.docs_inserted = docs_inserted
        run.metadata_json = {"query": query[:500], "source": run.source_name}
        await db.flush()
        await db.commit()

        logger.info("collection_completed", run_id=run_id, docs_found=docs_found, docs_inserted=docs_inserted)

    except Exception as exc:
        logger.exception("collection_failed", run_id=run_id)
        try:
            from app.models.collection_run import CollectionRun

            run_obj = await db.get(CollectionRun, run_uuid)
            if run_obj:
                run_obj.status = "failed"
                run_obj.error_message = str(exc)[:2000]
                run_obj.finished_at = datetime.now(UTC)
                await db.flush()
        except Exception:
            pass
