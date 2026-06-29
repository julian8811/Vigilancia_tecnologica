# ADR-001: In-process background tasks

**Status:** Accepted (with caveat). Revisit at 50k tasks/day or Q3 2026, whichever comes first.

**Context:** VigilaGraph runs document collection (`run_collection`), AI analysis (`run_analysis`), and graph generation (`graph_service.generate` — as a 1-hour subprocess) as background work. The original Celery design was dropped in favour of in-process `asyncio.create_task` to ship the MVP. Volume is currently low (a few hundred tasks/day at most).

**Decision:** Keep `asyncio.create_task` as the background runtime, wrapped by `app.tasks.safe.safe_background_task`. The wrapper:

- Binds a structlog `task` context so every log line is correlatable.
- Catches **all** exceptions and logs them with the full traceback (the request handler has already returned by then, so the user is not affected).
- Forwards args by position/keyword only — the function signature must be picklable so a future migration to BullMQ does not require code changes.

State persistence is the safety net for the in-process model: `CollectionRun`, `GraphRun`, and `AnalysisRun` rows carry the run state in the database. If a task fails, the row is updated with `error_message`. A periodic janitor (out of scope for this ADR; tracked as a follow-up) can re-enqueue any row stuck in `running` for more than N minutes.

**Consequences:**

- (+) Zero new infrastructure. One process, one Dockerfile, one `startCommand`. Fits the current single-tenant deploy on Railway.
- (+) All errors are caught and logged; the user is never broken by a background failure.
- (+) Task arguments are picklable → drop-in migration to BullMQ later.
- (−) In-flight work is lost on process restart. Mitigated by run-state rows (a janitor can re-enqueue stuck rows).
- (−) No retry / DLQ. The current `run_collection` retries internally on a per-connector basis; there is no outer retry. Add BullMQ's `max_retries` later.
- (−) No real-time task monitoring. The audit log + structlog are the only signals.

## Migration to BullMQ (planned, not scheduled)

The Redis that backs the app today (cache + future broker) can also host BullMQ. The migration is mechanical: convert `safe_background_task(coro_fn, *args, **kwargs)` into a BullMQ `enqueue(coro_fn, *args, **kwargs)`, run a separate `bullmq-worker` process, add `max_retries` and `backoff`. The function bodies (run_collection, run_analysis) do not change. Estimated effort: 1–2 weeks, including the worker deployment on Railway and a 7-day canary on 10% of traffic.

**Revisit if:** task volume crosses 50k/day, task loss becomes a real (not theoretical) problem, or we target a serverless deployment.
