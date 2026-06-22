"""Helper functions for document collection — extracted from the Celery worker.

These were originally in ``worker.tasks.collection_tasks``.  They are pure
functions with no Celery or worker dependency, so they live here.
"""

from __future__ import annotations

import hashlib
from typing import Any


def _compute_checksum(doc: dict) -> str:
    """MD5 hash of the document *content* for deduplication.

    Uses the same fields that define a document's identity: title, abstract,
    authors, and DOI.
    """
    raw = "|".join([
        doc.get("title", "") or "",
        doc.get("abstract", "") or "",
        "|".join(doc.get("authors", []) or []),
        doc.get("doi", "") or "",
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_search_query(strategy: Any) -> str:
    """Construct an OpenAlex search query from a project's SearchStrategy.

    Priority: ``boolean_queries`` > ``keywords_en + keywords_es``.
    Falls back to ``"*"`` when the strategy has no keywords defined.
    """
    if strategy.boolean_queries and strategy.boolean_queries.strip():
        return strategy.boolean_queries.strip()[:500]

    parts: list[str] = []
    if strategy.keywords_en and strategy.keywords_en.strip():
        parts.append(strategy.keywords_en.strip())
    if strategy.keywords_es and strategy.keywords_es.strip():
        parts.append(strategy.keywords_es.strip())

    if parts:
        return " ".join(parts)[:500]

    return "*"


def _is_source_selected(strategy: Any, source_name: str) -> bool:
    """Check whether *source_name* appears in the strategy's selected sources."""
    raw = strategy.sources_selected or ""
    return source_name in [s.strip().lower() for s in raw.split(",") if s.strip()]
