"""Semantic Scholar API connector — fetches academic papers.

Semantic Scholar provides a free scholarly API.  An API key is optional but
recommended for a dedicated rate-limit pool.  Without a key requests share a
common anonymous pool.

API docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import asyncio
from structlog import get_logger
from typing import AsyncGenerator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from worker.connectors.base import BaseConnector

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_TIMEOUT = 30.0
MAX_CONCURRENT_WITH_KEY = 1      # dedicated rate limit (1 req/s)
MAX_CONCURRENT_ANONYMOUS = 5     # conservative for shared pool
BATCH_SLEEP = 1.0                # seconds between requests
PAGE_SIZE = 100                  # practical page size
RETRY_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Retry strategy
# ---------------------------------------------------------------------------

_retry_dec = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
    ),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_institutions(authors: list[dict]) -> list[str]:
    """Collect unique institution names from a Semantic Scholar author list."""
    institutions: list[str] = []
    for author in authors or []:
        for aff in author.get("affiliations") or []:
            name = aff.get("name") if isinstance(aff, dict) else aff
            if name and str(name) not in institutions:
                institutions.append(str(name))
    return institutions


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class SemanticScholarConnector(BaseConnector):
    """Connector for the Semantic Scholar paper search API.

    Usage::

        connector = SemanticScholarConnector()
        async for doc in connector.fetch("artificial intelligence", max_results=200):
            print(doc["title"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        max_concurrent = (
            MAX_CONCURRENT_WITH_KEY if api_key else MAX_CONCURRENT_ANONYMOUS
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)

        headers: dict[str, str] = {
            "User-Agent": "VigilaGraph/1.0 (mailto:julian@example.com)",
        }
        if api_key:
            headers["x-api-key"] = api_key

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers,
        )

    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Yield normalized documents from Semantic Scholar."""
        fetched = 0
        offset = 0
        pages = 0

        fields = "title,abstract,authors,year,externalIds,openAccessPdf"

        while fetched < max_results:
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                data = await self._fetch_page(query, offset, fields)

            docs = data.get("data") or []
            if not docs:
                break

            pages += 1
            logger.info(
                "semantic_scholar_page_fetched",
                page=pages,
                count=len(docs),
                offset=offset,
            )

            for paper in docs:
                if fetched >= max_results:
                    break
                yield self._normalize_paper(paper)
                fetched += 1

            offset += len(docs)

        logger.info(
            "semantic_scholar_fetch_complete",
            total_fetched=fetched,
            pages=pages,
            query=query[:100],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_retry_dec
    async def _fetch_page(self, query: str, offset: int, fields: str) -> dict:
        """GET a single page of papers from Semantic Scholar."""
        params: dict[str, str | int] = {
            "query": query,
            "limit": PAGE_SIZE,
            "offset": offset,
            "fields": fields,
        }

        url = f"{self.base_url}/paper/search"
        logger.debug("semantic_scholar_request", url=url, params=params)

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:500]
            logger.error(
                "semantic_scholar_http_error",
                status=status,
                url=str(exc.request.url),
                body=body,
            )
            if status == 429:
                logger.warning("semantic_scholar_rate_limited — will retry with backoff")
            raise

        return response.json()

    def _normalize_paper(self, paper: dict) -> dict:
        """Convert a raw Semantic Scholar paper dict to the standard schema."""
        paper_id: str = paper.get("paperId", "")
        external_ids = paper.get("externalIds") or {}
        doi_raw: str | None = external_ids.get("doi")

        # Normalize DOI to full URL if it is just the identifier
        doi: str | None = None
        if doi_raw:
            doi = doi_raw if doi_raw.lower().startswith("http") else f"https://doi.org/{doi_raw}"

        title: str = paper.get("title") or ""
        abstract: str | None = paper.get("abstract")

        authors: list[str] = []
        for author in paper.get("authors") or []:
            name = author.get("name")
            if name:
                authors.append(str(name))

        institutions = _extract_institutions(paper.get("authors") or [])

        pub_year: int | None = paper.get("year")

        open_access = paper.get("openAccessPdf") or {}
        pdf_url = open_access.get("url") if isinstance(open_access, dict) else None
        url: str = pdf_url or f"https://www.semanticscholar.org/paper/{paper_id}"

        return {
            "source_name": "semantic_scholar",
            "source_id": paper_id,
            "title": title,
            "doi": doi.lower() if doi else None,
            "abstract": abstract,
            "authors": authors,
            "institutions": institutions,
            "publication_year": pub_year,
            "language": None,
            "url": url,
            "document_type": "paper",
        }

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
