"""Celery task definitions.

Concrete tasks (ingestion, collection, analysis, reporting) are added
here as they are implemented.
"""

from __future__ import annotations

from worker.tasks.collection_tasks import collect_from_source
from worker.tasks.graph_tasks import run_graphify
from worker.tasks.analysis_tasks import run_analysis

__all__ = [
    "collect_from_source",
    "run_graphify",
    "run_analysis",
]
