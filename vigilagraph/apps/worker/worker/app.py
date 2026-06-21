"""Celery application configuration and entry point."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

app = Celery(
    "vigilagraph",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "worker.tasks",
        "worker.graphify.adapter",
    ],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=3600,       # 1 hour max per task
    task_soft_time_limit=3000,  # Soft limit at 50 minutes
    worker_prefetch_multiplier=1,
    result_expires=86400,       # Results expire after 1 day
)


@app.task(bind=True)
def health_check(self) -> dict[str, str]:
    """Simple health-check task to verify the worker is running."""
    return {
        "status": "ok",
        "worker": self.request.hostname or "unknown",
    }
