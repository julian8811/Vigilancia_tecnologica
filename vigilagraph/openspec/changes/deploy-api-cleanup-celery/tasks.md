# Tasks: Deploy API + Cleanup Celery/Redis

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~180 (net, review-worthy) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

All ~180 changed lines are mechanical (copy, inline, remove). Pure refactor, no behavioral changes. Fits easily in one PR.

**Note — design vs spec conflict**: Design decides to **inline** the 3 helper functions into `collection.py` (rejecting separate `collection_helpers.py`). Spec says create `collection_helpers.py`. **User chose separate file** — override applied.

---

## Phase 1: Foundation — Move worker packages to API

- [x] **1.1** Create `apps/api/app/connectors/` — copy `__init__.py`, `base.py`, `openalex.py`, `semantic_scholar.py`, `lens.py`, `web.py` from `worker/worker/connectors/` as-is
- [x] **1.2** Create `apps/api/app/ai/` — copy `__init__.py`, `client.py`, `prompts.py`, `schemas.py`, `service.py` from `worker/worker/ai/` as-is
- [x] **1.3** Verify: `python -c "from app.connectors.openalex import OpenAlexConnector; from app.ai.service import AnalysisService"` resolves without error from `apps/api/`

## Phase 2: Core — Extract helpers, update imports

- [x] **2.1** Created `apps/api/app/tasks/collection_helpers.py` with 3 helpers. **User override**: separate file, not inlined (was `collection.py` inline in original task)
- [x] **2.2** In `collection.py`: changed 4 connector imports (`from worker.connectors.*` → `from app.connectors.*`); changed `from worker.tasks.collection_tasks` → `from app.tasks.collection_helpers`
- [x] **2.3** In `analysis.py`: changed `from worker.ai.service import AnalysisService` → `from app.ai.service import AnalysisService`
- [x] **2.4** (implied by 3.3) Updated imports in copied connector files (`openalex.py`, `semantic_scholar.py`, `lens.py`): `worker.connectors.base` → `app.connectors.base`
- [x] **2.5** (implied by 3.3) Updated imports in copied service.py: `worker.ai.*` → `app.ai.*`

## Phase 3: Delete — Remove worker directory

- [x] **3.1** Delete entire `apps/worker/` tree (connectors/, ai/, tasks/, graphify/, tests/, app.py, Dockerfile, pyproject.toml, uv.lock, .dockerignore, __pycache__/)
- [x] **3.2** Delete `infra/docker/worker.Dockerfile`
- [x] **3.3** Verify: `grep -r 'from worker' apps/api/` → 0 matches; `ls apps/worker/` fails (gone)

## Phase 4: Infrastructure — Clean docker-compose, start.sh

- [x] **4.1** Root `docker-compose.yml`: removed `redis:` service block, `worker:` service block, `redis_data:` volume, `REDIS_URL` from api env, `depends_on: redis` from api
- [x] **4.2** `infra/docker/docker-compose.yml`: removed `redis:` service block, `redis_data:` volume
- [x] **4.3** `infra/docker-compose.prod.yml`: removed `redis:` service, `worker:` service, `redisdata:` volume, all CELERY_* env vars, `depends_on: redis` from api
- [x] **4.4** `infra/docker/start.sh`: removed Redis daemon start + Celery background start; kept alembic + uvicorn

## Phase 5: Infrastructure — Clean env, CI, Makefile, pre-commit, config

- [x] **5.1** `.env` and `local.env`: removed `REDIS_URL` + all 5 `CELERY_*` lines
- [x] **5.2** `.env.example`: rebuilt as complete template with DB, JWT, S3, API keys, frontend URL — no Celery/Redis
- [x] **5.3** `Makefile`: removed `cd apps/worker` lines from `install`, `lint`, `test`; removed `run-worker` target
- [x] **5.4** `.github/workflows/ci.yml`: removed entire `worker:` job; changed `e2e` needs from `[api, worker, frontend]` → `[api, frontend]`
- [x] **5.5** `.pre-commit-config.yaml`: changed `files: ^apps/(api|worker)/` → `files: ^apps/api/` in both ruff hooks
- [x] **5.6** `openspec/config.yaml`: removed Celery/Redis/Valkey from context string and stack sections; set `task_queue: none`; removed worker entry

## Phase 6: Verification

- [x] **6.1** Run `uv run pytest tests/ -v` in `apps/api/` — **28 passed, 1 skipped** (test_upload_pdf requires S3/MinIO)
- [x] **6.2** Grep residual: `grep -r 'from worker' apps/api/` → 0 matches; `grep -rE '(CELERY_|REDIS_URL)' .env .env.example local.env` → 0 matches
- [x] **6.3** `docker compose config` on root and infra docker-compose files: YAML validated with Python (docker segfaults on this machine) — no redis/worker services in any compose file

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Design vs spec conflict**: design says inline helpers, spec says separate file | Mitigated | User chose separate file — override applied. |
| `collection.py` imports from `app.models.*` during 2.1 before 1.1 completes | None | Task 1 must complete before Task 2. Sequential dependency is enforced. |
| Missing dep in `api/pyproject.toml` for moved code | Low | Already audited — all deps present (httpx, boto3, tenacity, openai, etc.) |
| `.env.example` template still references removed vars | Low | Verification sweep (task 6.2) catches this |

## Dependencies

- **1.1 → 1.2 → 2** (packages must exist before imports resolve)
- **2 → 3** (imports must work before deleting old code)
- **3 → 4** (worker removed before infra clean; infra clean is independent but safer after)
- **4, 5 → 6** (all changes done before final verification)
- Tasks 4 and 5 are independent of each other — can run in parallel
