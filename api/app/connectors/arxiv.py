"""arXiv API connector — fetches preprints from arxiv.org.

arXiv hosts 2.5M+ preprints in CS, physics, math, and related fields.
No API key is required. The public API serves Atom XML at a polite
rate of ~1 request every 3 seconds.

API docs: https://info.arxiv.org/help/api/index.html
"""

from __future__ import annotations

import asyncio
import re
from structlog import get_logger
from typing import AsyncGenerator
from urllib.parse import quote_plus

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.connectors.base import BaseConnector

logger = get_logger(__name__)

BASE_URL = "https://export.arxiv.org/api/query"
DEFAULT_TIMEOUT = 45.0
MAX_CONCURRENT = 1
BATCH_SLEEP = 3.5  # arXiv polite pool: ≤ 1 req / 3 s
MAX_RESULTS_PER_PAGE = 100
RETRY_ATTEMPTS = 3

_retry_dec = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(min=3, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
    ),
    reraise=True,
)

_NS_RE = re.compile(r"\{[^}]+\}(.*)")  # strip XML namespaces


def _tag(name: str) -> str:
    return f"{{http://www.w3.org/2005/Atom}}{name}"


def _arxiv_tag(name: str) -> str:
    return f"{{http://arxiv.org/schemas/atom}}{name}"


def _extract_text(elem, tag: str) -> str:
    child = elem.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def _extract_authors(elem) -> list[str]:
    authors = []
    for author_elem in elem.findall(_tag("author")):
        name = _extract_text(author_elem, _tag("name"))
        if name:
            authors.append(name)
    return authors


def _extract_arxiv_id(entry_id: str) -> str:
    """From 'http://arxiv.org/abs/2106.09685' → '2106.09685'."""
    parts = entry_id.split("/")
    return parts[-1] if parts else entry_id


def _clean_html(raw: str) -> str:
    """Strip basic HTML tags from abstract text."""
    return re.sub(r"<[^>]+>", "", raw).strip()


class ArxivConnector(BaseConnector):
    """Connector for the arXiv public API.

    Usage::

        connector = ArxivConnector()
        async for doc in connector.fetch("transformers", max_results=30):
            print(doc["title"])
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_concurrent: int = MAX_CONCURRENT,
    ) -> None:
        self.base_url = base_url
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "VigilaGraph/1.0 (https://vigilagraph-web.onrender.com)"},
        )

    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Yield normalized documents from arXiv."""
        import xml.etree.ElementTree as ET

        fetched = 0
        start = 0

        while fetched < max_results:
            async with self._semaphore:
                await asyncio.sleep(BATCH_SLEEP)
                raw_xml = await self._fetch_page(query, start)

            if not raw_xml:
                break

            root = ET.fromstring(raw_xml)
            entries = root.findall(_tag("entry"))
            if not entries:
                break

            for entry in entries:
                if fetched >= max_results:
                    break
                yield self._normalize_entry(entry)
                fetched += 1

            start += len(entries)

            # Stop if arXiv returned fewer than requested (no more results)
            total = root.find(_tag("totalResults"))
            total_results = int(total.text) if total is not None and total.text else 0
            if start >= total_results:
                break

        logger.info("arxiv_fetch_complete", total_fetched=fetched, query=query[:100])

    @_retry_dec
    async def _fetch_page(self, query: str, start: int) -> str:
        limit = min(MAX_RESULTS_PER_PAGE, 100)
        params = {
            "search_query": f"all:{quote_plus(query)}",
            "start": start,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        resp = await self._client.get(self.base_url, params=params)
        resp.raise_for_status()
        return resp.text

    def _normalize_entry(self, entry) -> dict:
        arxiv_id = _extract_arxiv_id(_extract_text(entry, _tag("id")))
        title = _clean_html(_extract_text(entry, _tag("title")))
        abstract = _clean_html(_extract_text(entry, _tag("summary")))

        authors = _extract_authors(entry)

        published = _extract_text(entry, _tag("published"))
        pub_year: int | None = None
        if published and len(published) >= 4:
            try:
                pub_year = int(published[:4])
            except ValueError:
                pass

        doi: str | None = None
        for link in entry.findall(_tag("link")):
            href = link.attrib.get("href", "")
            if "doi.org" in href:
                doi = href.split("doi.org/")[-1] if "doi.org/" in href else None
            elif link.attrib.get("title") == "doi":
                doi = href

        url = f"https://arxiv.org/abs/{arxiv_id}"

        return {
            "source_name": "arxiv",
            "source_id": arxiv_id,
            "title": title,
            "doi": doi.lower() if doi else None,
            "abstract": abstract or None,
            "authors": authors,
            "institutions": [],
            "publication_year": pub_year,
            "language": "en",
            "url": url,
            "document_type": "paper",
        }

    async def close(self) -> None:
        await self._client.aclose()
