# Architecture

> Living document. Update this when you make architectural decisions (and write an ADR under `docs/adr/`).

## Components

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│  Web (Next) │────▶│  API (FastAPI)                                   │
│  :3000      │     │  :8000                                           │
│             │     │                                                  │
│  - App Rtr  │     │  Routers ─▶ Services ─▶ Repositories ─▶ Models   │
│  - RHF+Zod  │     │                  │                               │
│  - TanStack │     │                  └─▶ tasks/ (asyncio.create_task) │
│  - shadcn   │     │                                                  │
│             │     │  Connectors: openalex, lens, semantic_scholar,   │
│             │     │              web                                  │
└─────────────┘     │                                                  │
                    │  /docs (auto OpenAPI)  /ready (DB healthcheck)   │
                    └─────┬───────────────────┬──────────────┬────────┘
                          │                   │              │
                          ▼                   ▼              ▼
                    ┌──────────┐       ┌──────────┐   ┌──────────┐
                    │ Postgres │       │  Redis   │   │  MinIO   │
                    │ +pgvector│       │ (cache)  │   │  (S3)    │
                    └──────────┘       └──────────┘   └──────────┘
```

The web app talks to the API only. The API orchestrates ingestion, analysis, and graph generation. The "worker" of the previous design is now an in-process task system driven by `asyncio.create_task` (see [ADR-001](#adr-001-in-process-background-tasks)).

## Data model (high level)

Tables (see `api/app/models/` for the SQLAlchemy definitions):

- `organizations` — tenant boundary.
- `users` — belongs to one organization, has `role` and `is_superuser` flags (enforced, see [ADR-003](#adr-003-rbac-enforced-on-mutating-endpoints)).
- `surveillance_projects` — the unit of work; each project has one organization.
- `search_strategies` — query templates scoped to a project.
- `documents` — uploaded or URL-fetched source material.
- `document_chunks` — text chunks for embedding/retrieval.
- `graph_runs` — one row per `graph generate` invocation.
- `graph_nodes` / `graph_edges` — extracted knowledge graph.
- `technologies`, `trends`, `actors`, `opportunities` — analysis outputs.
- `reports` — generated reports (PDF/Markdown/HTML).
- `collection_runs` — audit row for each collection cycle.

## Request flow: "Collect from search"

1. Client posts to `POST /api/v1/projects/{id}/search-strategies/{sid}/collect`.
2. Project service validates the org boundary, transitions project status to `collecting`.
3. Service schedules `tasks.collection.run_collection` via `asyncio.create_task`.
4. Collection task runs the configured connectors (openalex, lens, semantic_scholar, web) in sequence with per-connector rate limits and retry/backoff.
5. Each fetched document is stored in the `documents` table with its extracted text chunked into `document_chunks`.
6. Collection run completes; project status moves to `analyzing`.
7. Analysis service runs (`tasks.analysis.run_analysis`) and produces rows in `technologies`, `trends`, `actors`, `opportunities`.
8. Project status moves to `graph_ready`; user can now trigger graph generation.

## Background tasks (current approach)

The `tasks/` package is a **placeholder for a future queue**. The current implementation uses `asyncio.create_task` to schedule work, which works on a long-running process (Railway, Fly.io, Docker) but **does not survive serverless function cycles** (Vercel, Lambda).

If the deployment target changes to serverless, this code must be migrated to a real queue (BullMQ on Redis, or a managed job runner). See [ADR-001](#adr-001-in-process-background-tasks).

## Deployment

Three PaaS targets are supported via configuration files at the repo root:

| Target  | Config                          | Notes                                                |
|---------|---------------------------------|------------------------------------------------------|
| Railway | `railway.json` + `nixpacks.toml`| NIXPACKS builder. Use `POSTGRES_URL` from Railway.   |
| Render  | `render.yaml`                   | Managed Postgres + web service.                      |
| Fly.io  | `fly.toml` + `infra/docker/fly.Dockerfile` | Machines run on port 8000.              |

All three require:
- `JWT_SECRET` set to a real random value (≥ 32 bytes).
- `DATABASE_URL` pointing to a Postgres 16 + pgvector instance.
- `S3_*` set to MinIO or real S3 credentials.

## Observability

- **Logs:** `structlog` JSON to stdout. Production collectors (Render, Fly, Railway) ship them to their respective dashboards. No centralized log store yet.
- **Metrics:** None. Adding Prometheus + `/metrics` is on the roadmap.
- **Tracing:** None. Adding OpenTelemetry is on the roadmap.
- **Errors:** No Sentry (or equivalent) yet. Logs are the only signal.

## Known issues & audit findings

This section tracks the gaps found in the technical audit (2026-06-29). See [SECURITY.md](../SECURITY.md) for the security-focused checklist.

### CRITICAL — block production deploy

| # | Issue | Location | Status |
|---|-------|----------|--------|
| 1 | `JWT_SECRET` defaults to a known string | `api/app/core/config.py:28` | **Mitigated by** required-env check (TBD) |
| 2 | JWT in `localStorage` (XSS-stealable) | `web/hooks/use-auth.tsx:36,60,81` | Open |
| 3 | No rate limit on `/auth/login` | `api/app/api/v1/auth.py:19,26` | Open |
| 4 | E2E tests assert English text (broken) | `web/e2e/smoke.spec.ts` | Open |
| 5 | Pre-commit hooks reference `apps/...` | `.pre-commit-config.yaml:14,20,26` | **Fixed in this branch** |
| 6 | In-process `asyncio.create_task` (no serverless) | `api/app/services/project_service.py:201`, `analysis_service.py:61` | Open |
| 7 | HTML injection in report templates | `api/app/services/report_service.py:243-285` | Open |
| 8 | `nixpacks.toml` pins Python 3.11 | `nixpacks.toml:2` | **Fixed in this branch** |
| 9 | `railway.json` startCommand empty | `railway.json:7` | **Fixed in this branch** |
| 10 | `fly.toml` port 8080 vs API 8000 | `fly.toml:7,10` | **Fixed in this branch** |

### HIGH — significant risk

- No request ID middleware (`api/app/main.py`).
- No security headers middleware.
- `/ready` returns 200 when degraded (`api/app/main.py:83-91`).
- `require_roles` defined but never used (`api/app/api/deps.py:108-128`). **Fixed in this branch** — replaced by `require_min_role` and wired across all mutating routers (see ADR-003).
- No PII redaction in logs (`api/app/services/auth_service.py:42,73,...`).
- No audit log for sensitive operations.
- Inconsistent error response shape (`{error}` vs `{detail}`).
- No Dockerfile `HEALTHCHECK` in any service.

### MEDIUM — quality issues

- `RegisterRequest.password` accepts any non-empty string (`api/app/schemas/auth.py:13-19`).
- CORS uses wildcard methods/headers (`api/app/main.py:60-61`).
- No global body size limit.
- `seed-test-docs` reachable in OpenAPI spec.
- Dead code in `graph_service.py:603-608`.
- `get_current_active_user` returns 400 instead of 401/403.
- `bcrypt` instead of `argon2id` (passlib default).
- `alembic/env.py` has `# import app.models` commented out → no `--autogenerate`.
- Hardcoded S3 default credentials in `config.py:42-44`.
- Status labels duplicated in 4 places (no central i18n).

### LOW — nice-to-have

- No CSRF strategy (relevant if migrating to cookie-based auth).
- No bulk-create endpoints.
- No `next/image` usage (no images in the app).
- No `pip-audit` / `npm audit` step in CI.
- No coverage badge / coverage gate.
- `Dockerfile` re-installs deps already in `pyproject.toml`.
- Inconsistent slug uniqueness (org vs project).

## Architecture Decision Records

ADRs live in [`docs/adr/`](adr/). Each ADR captures the context, decision, and consequences of a significant architectural choice.

### ADR-001: In-process background tasks

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

**Migration to BullMQ (planned, not scheduled):**
The Redis that backs the app today (cache + future broker) can also host BullMQ. The migration is mechanical: convert `safe_background_task(coro_fn, *args, **kwargs)` into a BullMQ `enqueue(coro_fn, *args, **kwargs)`, run a separate `bullmq-worker` process, add `max_retries` and `backoff`. The function bodies (run_collection, run_analysis) do not change. Estimated effort: 1–2 weeks, including the worker deployment on Railway and a 7-day canary on 10% of traffic.

**Revisit if:** task volume crosses 50k/day, task loss becomes a real (not theoretical) problem, or we target a serverless deployment.


### ADR-002: SQLAlchemy 2.0 + asyncpg

**Status:** Accepted.
**Context:** The backend needs Postgres + pgvector for vector storage. We need async I/O throughout the request path.
**Decision:** Use SQLAlchemy 2.0 with the async dialect (`asyncpg`). Pydantic v2 for request/response schemas. Alembic for migrations.
**Consequences:** Pydantic v2 has stricter validation than v1 — caught several issues at boot time. Async SQLAlchemy 2.0 is well-supported but has rough edges around relationships; we keep them shallow.

### ADR-003: RBAC enforced on mutating endpoints

**Status:** Implemented.
**Context:** The `User` model has `role` and `is_superuser` columns. The `require_min_role(min_role)` dependency is defined in `app/api/deps.py:203-229`.
**Decision:** All mutating endpoints (POST, PUT, PATCH, DELETE) now gate via `require_min_role(Role.ANALYST)`. Read-only endpoints remain open to `viewer`. Superusers bypass all checks.
**Consequences:** (+) RBAC is now wired across all routers. (-) The exact permission matrix needs review before multi-tenant public release.

### ADR-004: Graphify as an external CLI

**Status:** Accepted.
**Context:** Knowledge-graph extraction is a complex problem. There is an existing open-source CLI ([graphifyy](https://pypi.org/project/graphifyy/)) that does it well.
**Decision:** Invoke `graphifyy` as a subprocess from the API via `asyncio.create_subprocess_exec`. The tool is installed as a system-level `uv tool`, **not** as a Python package dependency.
**Consequences:** (+) No need to maintain extraction code. (−) Subprocess startup is slow (~5-10s). (−) Requires `uv` and the `graphifyy` tool in the runtime image. (−) Long-running (1h) subprocess inside a request handler is fragile on platforms with HTTP timeouts.
