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

**Note — design vs spec conflict**: Design decides to **inline** the 3 helper functions into `collection.py` (rejecting separate `collection_helpers.py`). Spec says create `collection_helpers.py`. Follow the design — it's the final technical authority.

---

## Phase 1: Foundation — Move worker packages to API

- [ ] **1.1** Create `apps/api/app/connectors/` — copy `__init__.py`, `base.py`, `openalex.py`, `semantic_scholar.py`, `lens.py`, `web.py` from `worker/worker/connectors/` as-is
- [ ] **1.2** Create `apps/api/app/ai/` — copy `__init__.py`, `client.py`, `prompts.py`, `schemas.py`, `service.py` from `worker/worker/ai/` as-is
- [ ] **1.3** Verify: `python -c "from app.connectors.openalex import OpenAlexConnector; from app.ai.service import AnalysisService"` resolves without error from `apps/api/`

## Phase 2: Core — Extract helpers, update imports

- [ ] **2.1** Paste the 3 helper functions (`_compute_checksum`, `_build_search_query`, `_is_source_selected` from `collection_tasks.py` lines 40–79) into `apps/api/app/tasks/collection.py` above `run_collection()`
- [ ] **2.2** In `collection.py`: change 4 connector imports (`from worker.connectors.*` → `from app.connectors.*`); remove the `from worker.tasks.collection_tasks import ...` line
- [ ] **2.3** In `analysis.py`: change `from worker.ai.service import AnalysisService` → `from app.ai.service import AnalysisService`

## Phase 3: Delete — Remove worker directory

- [ ] **3.1** Delete entire `apps/worker/` tree (connectors/, ai/, tasks/, graphify/, tests/, app.py, Dockerfile, pyproject.toml, uv.lock, .dockerignore, __pycache__/)
- [ ] **3.2** Delete `infra/docker/worker.Dockerfile`
- [ ] **3.3** Verify: `grep -r 'from worker' apps/api/` returns zero matches; `ls apps/worker/` fails (gone)

## Phase 4: Infrastructure — Clean docker-compose, start.sh

- [ ] **4.1** Root `docker-compose.yml`: remove `redis:` service block, `worker:` service block, `redis_data:` volume, `REDIS_URL` from api env, `depends_on: redis` from api
- [ ] **4.2** `infra/docker/docker-compose.yml`: remove `redis:` service block, `redis_data:` volume
- [ ] **4.3** `infra/docker-compose.prod.yml`: remove `redis:` service, `worker:` service, `redisdata:` volume, all CELERY_* env vars, `depends_on: redis` from api
- [ ] **4.4** `infra/docker/start.sh`: remove Redis daemon start (lines 4–11), Celery background start (line 17); keep alembic + uvicorn

## Phase 5: Infrastructure — Clean env, CI, Makefile, pre-commit, config

- [ ] **5.1** `.env` and `local.env`: remove `REDIS_URL` + all 5 `CELERY_*` lines
- [ ] **5.2** `.env.example`: remove `CELERY_RESULT_SERIALIZER`; rebuild as complete template with all active vars (DB, JWT, S3, API keys, frontend URL) — no Celery/Redis
- [ ] **5.3** `Makefile`: remove `cd apps/worker` lines from `install`, `lint`, `test`; remove `run-worker` target
- [ ] **5.4** `.github/workflows/ci.yml`: remove entire `worker:` job; change `e2e` needs from `[api, worker, frontend]` → `[api, frontend]`
- [ ] **5.5** `.pre-commit-config.yaml`: change `files: ^apps/(api|worker)/` → `files: ^apps/api/` in both ruff hooks
- [ ] **5.6** `openspec/config.yaml`: remove Celery/Redis/Valkey from context string and stack sections; set `task_queue: none`; remove worker entry

## Phase 6: Verification

- [ ] **6.1** Run `uv run pytest tests/ -v` in `apps/api/` — all tests pass
- [ ] **6.2** Grep residual: `grep -r 'from worker' apps/api/` → 0 matches; `grep -rE '(CELERY_|REDIS_URL)' .env .env.example local.env` → 0 matches
- [ ] **6.3** `docker compose config` on root and infra docker-compose files succeeds with no redis/worker services

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Design vs spec conflict**: design says inline helpers, spec says separate file | High | Follow design — inline. Noted for executor. |
| `collection.py` imports from `app.models.*` during 2.1 before 1.1 completes | None | Task 1 must complete before Task 2. Sequential dependency is enforced. |
| Missing dep in `api/pyproject.toml` for moved code | Low | Already audited — all deps present (httpx, boto3, tenacity, openai, etc.) |
| `.env.example` template still references removed vars | Low | Verification sweep (task 6.2) catches this |

## Dependencies

- **1.1 → 1.2 → 2** (packages must exist before imports resolve)
- **2 → 3** (imports must work before deleting old code)
- **3 → 4** (worker removed before infra clean; infra clean is independent but safer after)
- **4, 5 → 6** (all changes done before final verification)
- Tasks 4 and 5 are independent of each other — can run in parallel
