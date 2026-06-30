"""Europe PMC API connector — fetches life-science and biomedical literature.

Europe PMC indexes 42M+ publications from PubMed, PubMed Central, preprints,
patents, and grey literature. No API key required. JSON responses.

API docs: https://europepmc.org/RestfulWebService
Rate limit: polite pool (~10 req/s).
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

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
DEFAULT_TIMEOUT = 30.0
MAX_CONCURRENT = 3
BATCH_SLEEP = 0.3
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


def _parse_authors(author_string: str | None) -> list[str]:
    """Europe PMC returns authors as a semicolon-separated string."""
    if not author_string:
        return []
    return [a.strip() for a in author_string.split(";") if a.strip()]


class EuropePMCConnector(BaseConnector):
    """Connector for the Europe PMC search API.

    Usage::

        connector = EuropePMCConnector()
        async for doc in connector.fetch("CRISPR gene editing", max_results=50):
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
        """Yield normalized documents from Europe PMC."""
        fetched = 0
        cursor = "*"

        while fetched < max_results:
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                data = await self._fetch_page(query, cursor)

            results = (data.get("resultList") or {}).get("result") or []
            if not results:
                break

            for work in results:
                if fetched >= max_results:
                    break
                yield self._normalize_result(work)
                fetched += 1

            next_cursor = (data.get("nextCursorMark") or "").strip()
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        logger.info("europe_pmc_fetch_complete", total_fetched=fetched, query=query[:100])

    @_retry_dec
    async def _fetch_page(self, query: str, cursor: str) -> dict:
        params: dict[str, str | int] = {
            "query": query,
            "pageSize": PER_PAGE,
            "resultType": "core",
            "format": "json",
            "cursorMark": cursor,
        }
        url = f"{self.base_url}/search"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _normalize_result(self, result: dict) -> dict:
        title = result.get("title", "")
        doi = result.get("doi")
        abstract = result.get("abstractText")

        authors = _parse_authors(result.get("authorString"))

        pub_year_str = result.get("pubYear")
        pub_year: int | None = None
        if pub_year_str:
            try:
                pub_year = int(pub_year_str)
            except (ValueError, TypeError):
                pass

        source = result.get("source", "")
        pmid = result.get("pmid", "")
        pmcid = result.get("pmcid", "")

        # Build URL: prefer DOI, then PMC, then PubMed
        url: str = ""
        if doi:
            url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        elif pmcid:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
        elif pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        return {
            "source_name": "europe_pmc",
            "source_id": pmid or pmcid or source,
            "title": title,
            "doi": doi.lower() if doi else None,
            "abstract": abstract or None,
            "authors": authors,
            "institutions": [],
            "publication_year": pub_year,
            "language": None,
            "url": url,
            "document_type": "paper",
        }

    async def close(self) -> None:
        await self._client.aclose()
