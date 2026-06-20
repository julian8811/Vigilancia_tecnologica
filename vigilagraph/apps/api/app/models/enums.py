"""Shared enums for VigilaGraph models."""

from __future__ import annotations

from enum import StrEnum


class SourceName(StrEnum):
    """Valid external data-source identifiers for documents and collection runs.

    Values:
        manual_upload:    Document uploaded manually by the user.
        openalex:         OpenAlex academic database (openalex.org).
        semantic_scholar: Semantic Scholar academic search.
        lens:             Lens.org patent and scholarly database.
        web:              Web scraped / URL-tracked content.
    """

    manual_upload = "manual_upload"
    openalex = "openalex"
    semantic_scholar = "semantic_scholar"
    lens = "lens"
    web = "web"
