"""Crossref API connector — fetches scholarly works from crossref.org.

Crossref indexes 150M+ works with rich metadata (DOI, title, authors,
abstract, references, funding).  No API key is required for polite use.

API docs: https://api.crossref.org/
Polite pool: mailto in User-Agent (+50 req/s).
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

from app.connectors.base import BaseConnector

logger = get_logger(__name__)

BASE_URL = "https://api.crossref.org"
DEFAULT_TIMEOUT = 30.0
MAX_CONCURRENT = 5
BATCH_SLEEP = 0.2
PER_PAGE = 100
RETRY_ATTEMPTS = 3

_retry_dec = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
    ),
    reraise=True,
)


def _extract_authors(authors_list: list[dict]) -> list[str]:
    """Extract author names from Crossref author list."""
    names: list[str] = []
    for a in authors_list or []:
        given = a.get("given", "")
        family = a.get("family", "")
        full = f"{given} {family}".strip()
        if full:
            names.append(full)
        elif "name" in a:
            names.append(a["name"])
    return names


class CrossrefConnector(BaseConnector):
    """Connector for the Crossref REST API.

    Usage::

        connector = CrossrefConnector()
        async for doc in connector.fetch("machine learning", max_results=50):
            print(doc["title"])
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_concurrent: int = MAX_CONCURRENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "VigilaGraph/1.0 (https://vigilagraph-web.onrender.com)"},
        )

    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Yield normalized documents from Crossref."""
        fetched = 0
        offset = 0

        while fetched < max_results:
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                data = await self._fetch_page(query, offset)

            items = (data.get("message") or {}).get("items") or []
            if not items:
                break

            for work in items:
                if fetched >= max_results:
                    break
                yield self._normalize_work(work)
                fetched += 1

            offset += len(items)

        logger.info("crossref_fetch_complete", total_fetched=fetched, query=query[:100])

    @_retry_dec
    async def _fetch_page(self, query: str, offset: int) -> dict:
        params: dict[str, str | int] = {
            "query": query,
            "rows": PER_PAGE,
            "offset": offset,
            "sort": "relevance",
        }
        url = f"{self.base_url}/works"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _normalize_work(self, work: dict) -> dict:
        title = (work.get("title") or [""])[0]
        doi = work.get("DOI")
        abstract = work.get("abstract")

        authors = _extract_authors(work.get("author") or [])

        pub_year: int | None = None
        created = work.get("created", {}).get("date-parts", [[None]])[0]
        if created and created[0]:
            pub_year = int(created[0])

        url = doi if doi else (work.get("URL") or "")
        if url and not url.startswith("http"):
            url = f"https://doi.org/{url}"

        return {
            "source_name": "crossref",
            "source_id": doi or str(work.get("id", "")),
            "title": title,
            "doi": doi.lower() if doi else None,
            "abstract": abstract,
            "authors": authors,
            "institutions": [],
            "publication_year": pub_year,
            "language": None,
            "url": url,
            "document_type": "paper",
        }

    async def close(self) -> None:
        await self._client.aclose()
