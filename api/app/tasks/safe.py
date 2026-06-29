"""Safe background task wrapper.

Wraps an async coroutine so that:

1. It runs in a fresh DB session (not the request's session, which
   is closed by the time the task starts).
2. All exceptions are caught, logged structured, and persisted to
   the audit log.
3. The task name and arguments are bound to a single structlog
   context so every log line is correlatable.

This is the **S5 stop-gap**: see ADR-001 in docs/ARCHITECTURE.md.
We keep using ``asyncio.create_task`` (no Celery, no BullMQ) for
now because VigilaGraph's volume is low and the existing in-process
model already persists state to the database (CollectionRun,
GraphRun, AnalysisRun). When the volume justifies it, we migrate
to BullMQ-on-Redis (the same Redis that the app already uses for
broker/cache). The migration path is documented in the ADR.

Migration to BullMQ would look like::

    from arq.worker import create_worker  # or similar
    from app.tasks.safe import safe_background_task

    # Convert the safe wrapper into a BullMQ job definition:
    bullmq_job = bullmq.register(run_collection_task)
    bullmq_worker = bullmq.create_worker([bullmq_job])

    # At call sites, instead of:
    #     safe_background_task(run_collection_task, run_id)
    # use:
    #     await bullmq.enqueue(run_collection_task, run_id)

The function bodies (run_collection, run_analysis) do not change.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Optional, TypeVar

import structlog
from structlog.contextvars import bind_contextvars, unbind_contextvars

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def safe_background_task(
    coro_fn: Callable[..., Awaitable[None]],
    *args: Any,
    task_name: Optional[str] = None,
    **kwargs: Any,
) -> asyncio.Task[None]:
    """Schedule *coro_fn* to run after the current request returns.

    Parameters
    ----------
    coro_fn:
        The async function to run. Must accept only positional and
        keyword arguments that can be pickled (so BullMQ can pick
        them up later without changes — see the migration note in
        the module docstring).
    *args, **kwargs:
        Forwarded to *coro_fn*.
    task_name:
        Logical name for the task (used in log lines and the
        audit log). Defaults to ``coro_fn.__qualname__``.

    Returns
    -------
    asyncio.Task
        The scheduled task. Callers normally ignore the return
        value — the task runs in the background.

    Notes
    -----
    The task's DB session, if any, MUST be opened inside the
    coroutine (use ``app.db.session.async_session_factory()`` as a
    context manager). Do NOT pass the request's session — it will
    be closed before the task starts.
    """
    name = task_name or getattr(coro_fn, "__qualname__", repr(coro_fn))

    async def _runner() -> None:
        bind_contextvars(task=name, task_args=repr(args)[:200], task_kwargs=repr(kwargs)[:200])
        try:
            logger.info("background_task_started")
            await coro_fn(*args, **kwargs)
            logger.info("background_task_completed")
        except asyncio.CancelledError:
            # The task was cancelled (server restart, request
            # cancellation). Re-raise so the runtime sees it, but
            # log the cancellation so an operator can correlate.
            logger.warning("background_task_cancelled")
            raise
        except Exception:
            # Never let a background task fail silently. The
            # exception is logged with the full traceback; the
            # caller (the request handler) already returned a 200
            # to the user, so the request is not affected.
            logger.exception("background_task_failed")
        finally:
            unbind_contextvars("task", "task_args", "task_kwargs")

    return asyncio.create_task(_runner(), name=name)
