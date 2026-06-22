"""Web scraping connector — extracts article content from URLs.

This connector does **not** extend ``BaseConnector`` because it is URL-driven
rather than query-driven.  It uses trafilatura to fetch and extract content,
respects robots.txt, and adds polite delays between requests.
"""

from __future__ import annotations

import asyncio
import hashlib
from structlog import get_logger
import random
import re
import urllib.robotparser
from typing import AsyncGenerator
from urllib.parse import urlparse

import httpx
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30.0
MAX_URLS_PER_RUN = 50
MIN_DELAY = 1.0
MAX_DELAY = 3.0
USER_AGENT = "VigilaGraph/1.0 (mailto:julian@example.com)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_urls(raw: str | None) -> list[str]:
    """Parse a raw newline/comma/whitespace separated string of URLs."""
    if not raw:
        return []

    urls: list[str] = []
    for token in raw.replace(",", "\n").split():
        url = token.strip()
        if url and url.startswith(("http://", "https://")):
            urls.append(url)
    return urls[:MAX_URLS_PER_RUN]


def _parse_year(date_str: str | None) -> int | None:
    """Best-effort year extraction from a date string."""
    if not date_str:
        return None

    # Try to find a 4-digit year in the string
    match = re.search(r"\b(19|20)\d{2}\b", str(date_str))
    return int(match.group(0)) if match else None


def _parse_authors(author_str: str | None) -> list[str]:
    """Split an author string by common separators."""
    if not author_str:
        return []
    parts = [p.strip() for p in re.split(r"[,;|]", author_str) if p.strip()]
    return parts


def _robots_cache() -> dict[str, urllib.robotparser.RobotFileParser]:
    """Module-level cache for robots.txt parsers."""
    if not hasattr(_robots_cache, "cache"):
        _robots_cache.cache = {}  # type: ignore[attr-defined]
    return _robots_cache.cache  # type: ignore[return-value]


def _is_allowed(url: str) -> bool:
    """Return True if robots.txt allows fetching *url* with our User-Agent."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        cache = _robots_cache()
        if robots_url not in cache:
            parser = urllib.robotparser.RobotFileParser(robots_url)
            parser.read()
            cache[robots_url] = parser

        return cache[robots_url].can_fetch(USER_AGENT, url)
    except Exception as exc:
        logger.warning("robots_txt_check_failed", url=url, error=str(exc))
        # Fail open: if we cannot verify robots.txt, allow the request
        return True


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class WebScraperConnector:
    """URL-driven connector that extracts web page content with trafilatura.

    Usage::

        connector = WebScraperConnector()
        async for doc in connector.scrape_urls(["https://example.com/article"]):
            print(doc["title"])
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def scrape_urls(
        self,
        urls: list[str],
        max_urls: int = MAX_URLS_PER_RUN,
    ) -> AsyncGenerator[dict, None]:
        """Yield normalized documents scraped from the provided URLs."""
        limited_urls = urls[:max_urls]
        logger.info("web_scrape_started", url_count=len(limited_urls))

        for idx, url in enumerate(limited_urls, start=1):
            try:
                if not _is_allowed(url):
                    logger.warning("web_scrape_robots_disallowed", url=url)
                    continue

                logger.debug("web_scrape_fetching", url=url, index=idx)
                downloaded = await self._fetch_url(url)
                if not downloaded:
                    logger.warning("web_scrape_empty_download", url=url)
                    continue

                extracted = trafilatura.bare_extraction(
                    downloaded,
                    output_format="python",
                    with_metadata=True,
                    include_comments=False,
                    include_tables=False,
                )
                if not extracted:
                    logger.warning("web_scrape_no_content", url=url)
                    continue

                yield self._normalize_extraction(extracted, url)

            except Exception as exc:
                logger.warning("web_scrape_url_failed", url=url, error=str(exc))
                continue

            # Polite delay between requests
            if idx < len(limited_urls):
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)

        logger.info("web_scrape_complete", processed=len(limited_urls))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _fetch_url(self, url: str) -> str | None:
        """Fetch raw HTML for a URL (retried up to 3x on HTTP errors/timeouts)."""
        response = await self._client.get(url)
        response.raise_for_status()
        return response.text

    def _normalize_extraction(self, extracted: dict, url: str) -> dict:
        """Convert a trafilatura extraction dict to the standard schema."""
        title: str = extracted.get("title") or ""
        body: str = extracted.get("raw_text") or extracted.get("text") or ""

        author_str = extracted.get("author")
        authors = _parse_authors(author_str)

        date_str = extracted.get("date")
        pub_year = _parse_year(date_str)

        hostname = extracted.get("hostname") or urlparse(url).netloc

        source_id = hashlib.md5(url.encode("utf-8")).hexdigest()

        abstract = body[:500].strip() if body else None

        return {
            "source_name": "web",
            "source_id": source_id,
            "title": title,
            "doi": None,
            "abstract": abstract,
            "authors": authors,
            "institutions": [],
            "publication_year": pub_year,
            "language": None,
            "url": url,
            "document_type": "article",
            "metadata_json": {
                "full_text": body,
                "hostname": hostname,
                "scrape_date": None,  # populated by caller if needed
            },
        }

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
