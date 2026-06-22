"""Lens.org API connector — fetches scholarly works and patents.

Lens.org requires a registered API token.  This first iteration targets the
scholarly search endpoint only; patent search can be added later as a
separate connector or mode.

API docs: https://docs.lens.org/
"""

from __future__ import annotations

import asyncio
from structlog import get_logger
from typing import Any, AsyncGenerator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.connectors.base import BaseConnector

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.lens.org"
DEFAULT_TIMEOUT = 60.0  # Lens responses can be slower
MAX_CONCURRENT = 1       # 10 req/min base tier → be very conservative
BATCH_SLEEP = 6.0        # seconds between requests (≤ 10 req/min)
PAGE_SIZE = 200          # practical page size
RETRY_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Retry strategy
# ---------------------------------------------------------------------------

_retry_dec = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
    ),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_doi(external_ids: list[dict]) -> str | None:
    """Return the DOI value from Lens external_ids list, normalized to URL."""
    for item in external_ids or []:
        if isinstance(item, dict) and item.get("type", "").lower() == "doi":
            value = item.get("value") or ""
            if value:
                return value if value.lower().startswith("http") else f"https://doi.org/{value}"
    return None


def _extract_url(source_urls: list[dict]) -> str | None:
    """Return the first HTML landing page URL from Lens source_urls."""
    for item in source_urls or []:
        if isinstance(item, dict) and item.get("type", "").lower() == "html":
            url = item.get("url")
            if url:
                return url
    return None


def _extract_authors(authors: list[dict]) -> list[str]:
    """Build display names from Lens author first/last name fields."""
    names: list[str] = []
    for author in authors or []:
        if not isinstance(author, dict):
            continue
        parts = [
            author.get("first_name", ""),
            author.get("last_name", ""),
        ]
        name = " ".join(p.strip() for p in parts if p and p.strip())
        if name:
            names.append(name)
    return names


def _extract_institutions(authors: list[dict]) -> list[str]:
    """Collect unique institution names from Lens authorships."""
    institutions: list[str] = []
    for author in authors or []:
        if not isinstance(author, dict):
            continue
        for aff in author.get("affiliations") or []:
            if not isinstance(aff, dict):
                continue
            name = aff.get("name")
            if name and str(name) not in institutions:
                institutions.append(str(name))
    return institutions


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class LensConnector(BaseConnector):
    """Connector for the Lens.org scholarly search API.

    Usage::

        connector = LensConnector(api_token="eyJ...")
        async for doc in connector.fetch("crispr", max_results=200):
            print(doc["title"])
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_token:
            raise ValueError("LensConnector requires a non-empty api_token")

        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "User-Agent": "VigilaGraph/1.0 (mailto:julian@example.com)",
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )

    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Yield normalized documents from Lens.org scholarly search."""
        fetched = 0
        offset = 0
        pages = 0

        while fetched < max_results:
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                data = await self._fetch_page(query, offset)

            records = data.get("data") or []
            if not records:
                break

            pages += 1
            logger.info(
                "lens_page_fetched",
                page=pages,
                count=len(records),
                offset=offset,
            )

            for record in records:
                if fetched >= max_results:
                    break
                yield self._normalize_record(record)
                fetched += 1

            offset += len(records)
            total = data.get("total") or 0
            if offset >= total:
                break

        logger.info(
            "lens_fetch_complete",
            total_fetched=fetched,
            pages=pages,
            query=query[:100],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_retry_dec
    async def _fetch_page(self, query: str, offset: int) -> dict:
        """POST a single page of results to the Lens scholarly endpoint."""
        body: dict[str, Any] = {
            "query": {"match": {"title": query}},
            "size": PAGE_SIZE,
            "from": offset,
            "include": [
                "lens_id",
                "external_ids",
                "title",
                "abstract",
                "authors",
                "year_published",
                "languages",
                "source_urls",
            ],
        }

        url = f"{self.base_url}/scholarly/search"
        logger.debug("lens_request", url=url, offset=offset)

        try:
            response = await self._client.post(url, json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body_text = exc.response.text[:500]
            logger.error(
                "lens_http_error",
                status=status,
                url=str(exc.request.url),
                body=body_text,
            )
            if status == 401:
                logger.error("lens_auth_failed — check LENS_API_TOKEN")
            elif status == 429:
                logger.warning("lens_rate_limited — will retry with backoff")
            raise

        return response.json()

    def _normalize_record(self, record: dict) -> dict:
        """Convert a raw Lens record dict to the standard document schema."""
        lens_id: str = record.get("lens_id", "")
        doi = _extract_doi(record.get("external_ids") or [])

        title: str = record.get("title") or ""
        abstract: str | None = record.get("abstract")

        authors = _extract_authors(record.get("authors") or [])
        institutions = _extract_institutions(record.get("authors") or [])

        pub_year: int | None = record.get("year_published")

        languages = record.get("languages") or []
        language: str | None = str(languages[0]) if languages else None

        url: str = _extract_url(record.get("source_urls") or []) or f"https://www.lens.org/lens/scholar/article/{lens_id}"

        return {
            "source_name": "lens",
            "source_id": lens_id,
            "title": title,
            "doi": doi.lower() if doi else None,
            "abstract": abstract,
            "authors": authors,
            "institutions": institutions,
            "publication_year": pub_year,
            "language": language,
            "url": url,
            "document_type": "paper",
        }

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
