"""Celery task definitions.

Concrete tasks (ingestion, analysis, reporting) will be added here
as they are implemented.
"""

from __future__ import annotations

from worker.tasks.graph_tasks import run_graphify

__all__ = [
    "run_graphify",
]
