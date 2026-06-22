"""Background task runners — replaces Celery with in-process async execution.

These functions run document collection and AI analysis directly in the
API process using FastAPI BackgroundTasks. The worker's async logic is
reused without the Celery wrapper.
"""

from app.tasks.collection import run_collection
from app.tasks.analysis import run_analysis

__all__ = ["run_collection", "run_analysis"]
