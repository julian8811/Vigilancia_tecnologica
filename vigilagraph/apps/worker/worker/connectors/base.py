"""Abstract base connector for external data-source integrations.

Every external source (OpenAlex, Semantic Scholar, Lens.org, web scraping)
implements this interface so the collection task can treat them uniformly.
"""

from __future__ import annotations

from structlog import get_logger
from abc import ABC, abstractmethod
from typing import AsyncGenerator

logger = get_logger(__name__)


class BaseConnector(ABC):
    """Abstract base for external-source document connectors.

    Subclasses implement :meth:`fetch` to produce a stream of normalized
    document dicts.  The contract includes:

    * **Rate limiting** — subclasses MUST self-limit to stay within the
      source's acceptable request rate (polite pool, API tier, etc.).
    * **Error handling** — transient errors (429, 5xx) SHOULD be retried
      with exponential backoff.  Persistent errors MUST be logged and
      MAY be re-raised after exhausting retries.
    * **Normalization** — every yielded dict MUST conform to the standard
      document schema documented in :meth:`fetch`.
    """

    @abstractmethod
    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]:
        """Fetch documents matching *query* from the external source.

        Parameters
        ----------
        query : str
            Search query string in the source's native syntax.
        max_results : int
            Maximum number of documents to return (default 500).

        Yields
        ------
        dict
            A normalized document with **all** of the following keys:

            ================= ======== ==========================================
            Key               Type     Description
            ================= ======== ==========================================
            ``source_name``   str      Connector identifier (e.g. ``"openalex"``)
            ``source_id``     str      Permanent ID on the source platform
            ``title``         str      Document title
            ``doi``           str|None Digital Object Identifier (full URL)
            ``abstract``      str|None Abstract or summary text
            ``authors``       list[str] Author display names
            ``institutions``  list[str] Affiliated institution names (deduplicated)
            ``publication_year`` int|None Year of publication
            ``language``      str|None ISO 639-1 code (e.g. ``"en"``)
            ``url``           str      Best available landing-page or PDF URL
            ``document_type``  str     Content category (e.g. ``"paper"``)
            ================= ======== ==========================================

        Raises
        ------
        ConnectionError
            If the source is unreachable after all retries.
        ValueError
            If the response cannot be parsed.
        """
        ...
