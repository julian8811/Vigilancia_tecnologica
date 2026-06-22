"""Search router — preview external sources and import results."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, verify_project_org
from app.core.config import settings
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(tags=["búsqueda"])


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


class CollectFromSearchRequest(BaseModel):
    results: list[dict[str, Any]]
    source: str = "openalex"


@router.post("/search/preview", response_model=SearchPreviewResponse)
async def search_preview(
    request: SearchPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SearchPreviewResponse:
    """Preview search results from an external source without importing them."""
    import httpx

    results: list[SearchResultItem] = []

    try:
        if request.source == "openalex":
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.openalex.org/works",
                    params={
                        "search": request.query,
                        "per_page": min(request.limit, 50),
                        "sort": "relevance_score:desc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for work in data.get("results", [])[: request.limit]:
                    authors = []
                    for a in work.get("authorships") or []:
                        author = a.get("author") or {}
                        if author.get("display_name"):
                            authors.append(author["display_name"])

                    results.append(SearchResultItem(
                        title=work.get("title", ""),
                        authors=authors,
                        year=work.get("publication_year"),
                        doi=work.get("doi"),
                        source="openalex",
                        abstract=work.get("abstract", ""),
                        url=work.get("doi") or "",
                    ))

        elif request.source == "semantic_scholar":
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": request.query,
                        "limit": min(request.limit, 50),
                        "fields": "title,authors,year,externalIds",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for paper in data.get("data", [])[: request.limit]:
                    authors = [a.get("name", "") for a in paper.get("authors") or [] if a.get("name")]
                    ext_ids = paper.get("externalIds") or {}
                    results.append(SearchResultItem(
                        title=paper.get("title", ""),
                        authors=authors,
                        year=paper.get("year"),
                        doi=ext_ids.get("doi"),
                        source="semantic_scholar",
                        url=f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                    ))

    except Exception as exc:
        logger.error("search_preview_failed", source=request.source, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Búsqueda fallida: {exc}")

    logger.info("search_preview_completed", source=request.source, total=len(results))
    return SearchPreviewResponse(results=results, total=len(results))


@router.post("/projects/{project_id}/collect-from-search", status_code=201)
async def collect_from_search(
    project_id: uuid.UUID,
    request: CollectFromSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> dict:
    """Import manually selected search results as documents."""
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
