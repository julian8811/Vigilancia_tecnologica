"""Search router — preview external sources and import results.

Uses the connector layer (app/connectors/) for all external API calls so
retries, rate-limit backoff, and polite-pool behaviour are applied
consistently.  The previous implementation made raw httpx calls that
lacked retries and surfaced cryptic 429/504 exceptions to users.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, require_min_role, verify_project_org
from app.core.config import settings
from app.core.errors import AppError
from app.core.permissions import Role
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(tags=["búsqueda"])

_require_analyst = require_min_role(Role.ANALYST)

# ── Sources supported by the search preview ─────────────────────────

_SEARCH_SOURCES = frozenset({
    "openalex",
    "semantic_scholar",
    "lens",
    "crossref",
    "arxiv",
    "europe_pmc",
})


class SearchPreviewRequest(BaseModel):
    query: str
    source: str = "openalex"
    project_id: str | None = None
    limit: int = 20


class SearchResultItem(BaseModel):
    title: str
    authors: list[str] = []
    year: int | None = None
    doi: str | None = None
    source: str = ""
    abstract: str | None = None
    url: str | None = None


class SearchPreviewResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    source: str = ""


class CollectFromSearchRequest(BaseModel):
    results: list[dict[str, Any]]
    source: str = "openalex"


# ── Helpers ──────────────────────────────────────────────────────────


def _connector_result_to_item(doc: dict, source: str) -> SearchResultItem:
    """Map a connector-normalised dict to a SearchResultItem."""
    return SearchResultItem(
        title=doc.get("title", ""),
        authors=doc.get("authors") or [],
        year=doc.get("publication_year"),
        doi=doc.get("doi"),
        source=source,
        abstract=doc.get("abstract"),
        url=doc.get("url"),
    )


class SearchError(AppError):
    """Raised for user-visible search failures.

    Inherits from ``AppError`` so the global app_error_handler
    wraps it in ``{"detail": "..."}`` — the SPA reads ``err.detail``.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


# ── Preview endpoint ─────────────────────────────────────────────────


@router.post("/search/preview", response_model=SearchPreviewResponse)
async def search_preview(
    request: SearchPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_analyst),
) -> SearchPreviewResponse:
    """Preview search results from external sources. Analyst+.

    Supported *source* values: ``openalex``, ``semantic_scholar``, ``lens``.
    """
    import httpx

    if request.source not in _SEARCH_SOURCES:
        raise SearchError(
            400,
            f"Fuente desconocida: '{request.source}'. "
            f"Usá una de: {', '.join(sorted(_SEARCH_SOURCES))}.",
        )

    results: list[SearchResultItem] = []

    try:
        if request.source == "openalex":
            from app.connectors.openalex import OpenAlexConnector

            connector = OpenAlexConnector(timeout=30.0)
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "openalex"))
            finally:
                await connector.close()

        elif request.source == "semantic_scholar":
            from app.connectors.semantic_scholar import SemanticScholarConnector

            connector = SemanticScholarConnector(
                api_key=settings.SEMANTIC_SCHOLAR_API_KEY or None,
                timeout=30.0,
            )
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "semantic_scholar"))
            finally:
                await connector.close()

        elif request.source == "lens":
            if not settings.LENS_API_TOKEN:
                raise SearchError(
                    503,
                    "Lens.org no está configurado. "
                    "Agregá LENS_API_TOKEN en las variables de entorno del servicio Render. "
                    "Más info: https://docs.lens.org/",
                )

            from app.connectors.lens import LensConnector

            connector = LensConnector(
                api_token=settings.LENS_API_TOKEN,
                timeout=60.0,
            )
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "lens"))
            finally:
                await connector.close()

        elif request.source == "crossref":
            from app.connectors.crossref import CrossrefConnector

            connector = CrossrefConnector(timeout=30.0)
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "crossref"))
            finally:
                await connector.close()

        elif request.source == "arxiv":
            from app.connectors.arxiv import ArxivConnector

            connector = ArxivConnector(timeout=45.0)
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "arxiv"))
            finally:
                await connector.close()

        elif request.source == "europe_pmc":
            from app.connectors.europe_pmc import EuropePMCConnector

            connector = EuropePMCConnector(timeout=30.0)
            try:
                async for doc in connector.fetch(request.query, max_results=request.limit):
                    results.append(_connector_result_to_item(doc, "europe_pmc"))
            finally:
                await connector.close()

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        source = request.source

        if status == 429:
            raise SearchError(
                502,
                f"{source} nos está frenando por exceso de consultas (HTTP 429). "
                "Esperá unos segundos y volvé a intentar.",
            )
        if status in (503, 504):
            raise SearchError(
                502,
                f"{source} no está respondiendo (HTTP {status}). "
                "Puede ser una caída temporal del servicio externo.",
            )
        raise SearchError(
            502,
            f"Error al consultar {source} (HTTP {status}). "
            "El servicio externo devolvió un error inesperado.",
        )

    except httpx.TimeoutException:
        raise SearchError(
            502,
            f"{request.source} tardó demasiado en responder. "
            "Probá con una consulta más corta o con otra fuente.",
        )

    except httpx.ConnectError:
        raise SearchError(
            502,
            f"No se pudo conectar a {request.source}. "
            "Verificá tu conexión o intentá más tarde.",
        )

    except SearchError:
        raise

    except Exception as exc:
        logger.exception("search_preview_unexpected_error", source=request.source)
        raise SearchError(
            500,
            f"Error inesperado al consultar {request.source}: {exc}",
        )

    logger.info("search_preview_completed", source=request.source, total=len(results))
    return SearchPreviewResponse(
        results=results,
        total=len(results),
        source=request.source,
    )


# ── Collect endpoint ─────────────────────────────────────────────────


@router.post("/projects/{project_id}/collect-from-search", status_code=201)
async def collect_from_search(
    project_id: uuid.UUID,
    request: CollectFromSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_analyst),
    _: User = Depends(verify_project_org),
) -> dict:
    """Import manually selected search results as documents. Analyst+."""
    from datetime import datetime, UTC
    from app.models.document import Document

    inserted = 0
    for item in request.results:
        title = item.get("title", "Sin título")
        doi = item.get("doi")
        abstract = item.get("abstract") or item.get("abstract", "")
        authors = item.get("authors", [])
        url = item.get("url")

        # Check for duplicate DOI
        if doi:
            from sqlalchemy import select
            existing = await db.execute(
                select(Document).where(Document.project_id == project_id, Document.doi == doi)
            )
            if existing.scalar_one_or_none():
                continue

        doc = Document(
            project_id=project_id,
            title=title[:500],
            doi=doi,
            abstract=abstract,
            authors=authors,
            url=url,
            source_name=request.source,
            document_type="paper",
            processing_status="pending",
        )
        db.add(doc)
        inserted += 1

    await db.commit()
    logger.info("collect_from_search_completed", project_id=str(project_id), inserted=inserted)
    return {"message": f"{inserted} documentos importados", "inserted": inserted}
