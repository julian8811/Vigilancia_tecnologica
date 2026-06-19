"""Celery application configuration and entry point."""

from __future__ import annotations

from celery import Celery

# NOTE: In production, these would be imported from a shared config module
# or from the API's settings. For now we inline the env-var names so the
# worker can operate independently.

BROKER_URL = "redis://localhost:6379/0"
RESULT_BACKEND = "redis://localhost:6379/0"

app = Celery(
    "vigilagraph",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
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
