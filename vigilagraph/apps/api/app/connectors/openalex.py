"""OpenAlex API connector — fetches academic works from openalex.org.

OpenAlex is a free, open catalogue of scholarly works.  This connector
uses the REST API **without** an API key and respects the polite pool
rate limit (~10 requests/second).

API docs: https://docs.openalex.org/
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.openalex.org"
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_CONCURRENT = 10      # polite-pool limit (no API key)
BATCH_SLEEP = 0.1        # seconds between requests to stay ≤ 10 req/s
PER_PAGE = 100           # max per-page for OpenAlex
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

def reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """Rebuild OpenAlex abstract text from its ``abstract_inverted_index``.

    The inverted index maps each word to a list of 0-based positions::

        {"Hello": [0], "world": [1, 3], "from": [2]}

    Returns the reconstructed sentence ``"Hello world from world"``.
    """
    if not inverted_index:
        return None

    word_by_pos: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            word_by_pos[pos] = word

    if not word_by_pos:
        return None

    max_pos = max(word_by_pos)
    return " ".join(word_by_pos.get(i, "") for i in range(max_pos + 1)).strip()


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class OpenAlexConnector(BaseConnector):
    """Connector for the OpenAlex academic works API.

    Usage::

        connector = OpenAlexConnector()
        async for doc in connector.fetch("artificial intelligence", max_results=200):
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
            headers={"User-Agent": "VigilaGraph/1.0 (mailto:julian@example.com)"},
        )

    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Yield normalized documents from OpenAlex."""
        fetched = 0
        cursor = "*"
        pages = 0

        while cursor and fetched < max_results:
            # Rate-limit guard
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                data = await self._fetch_page(query, cursor)

            docs = data.get("results") or []
            meta = data.get("meta") or {}

            if not docs:
                break

            pages += 1
            logger.info(
                "openalex_page_fetched",
                page=pages,
                count=len(docs),
                cursor=cursor,
            )

            for work in docs:
                if fetched >= max_results:
                    break
                yield self._normalize_work(work)
                fetched += 1

            # Advance cursor
            cursor = meta.get("next_cursor")
            logger.debug("openalex_next_cursor", cursor=cursor)

        logger.info(
            "openalex_fetch_complete",
            total_fetched=fetched,
            pages=pages,
            query=query[:100],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @_retry_dec
    async def _fetch_page(self, query: str, cursor: str) -> dict:
        """GET a single page of results from the OpenAlex works endpoint."""
        params: dict[str, str | int] = {
            "search": query,
            "per_page": PER_PAGE,
            "cursor": cursor,
            "sort": "relevance_score:desc",
        }

        url = f"{self.base_url}/works"
        logger.debug("openalex_request", url=url, params=params)

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text[:500]
            logger.error(
                "openalex_http_error",
                status=status,
                url=str(exc.request.url),
                body=body,
            )
            if status == 429:
                logger.warning("openalex_rate_limited — will retry with backoff")
            raise

        return response.json()

    def _normalize_work(self, work: dict) -> dict:
        """Convert a raw OpenAlex work dict to the standard document schema."""
        # ── Source IDs ──────────────────────────────────────────────
        openalex_id: str = work.get("id", "")  # e.g. "https://openalex.org/W..."
        doi: str | None = work.get("doi")      # already a full URL

        # ── Title ────────────────────────────────────────────────────
        title: str = work.get("title") or ""

        # ── Abstract (from inverted index) ────────────────────────────
        inverted = work.get("abstract_inverted_index")
        abstract = reconstruct_abstract(inverted)

        # ── Authors & Institutions ────────────────────────────────────
        authors: list[str] = []
        institutions: list[str] = []

        for authorship in work.get("authorships") or []:
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(str(name))

            for inst in authorship.get("institutions") or []:
                inst_name = inst.get("display_name")
                if inst_name and str(inst_name) not in institutions:
                    institutions.append(str(inst_name))

        # ── Publication metadata ──────────────────────────────────────
        pub_year: int | None = work.get("publication_year")
        language: str | None = work.get("language")

        # ── URL (best available) ─────────────────────────────────────
        primary_location = work.get("primary_location") or {}
        landing_page = (primary_location or {}).get("landing_page_url")
        oa_url = (work.get("open_access") or {}).get("oa_url")
        url: str = landing_page or oa_url or openalex_id

        return {
            "source_name": "openalex",
            "source_id": openalex_id,
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
        """Explicitly close the underlying HTTP client."""
        await self._client.aclose()
