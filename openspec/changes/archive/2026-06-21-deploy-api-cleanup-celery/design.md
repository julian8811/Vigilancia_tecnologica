# Design: Deploy API + Cleanup Celery/Redis

## Technical Approach

Pure structural refactor with zero behavioral changes. Move the two actively-used packages (`connectors/`, `ai/`) and three helper functions from the dead Celery worker into the API package, then delete the entire `apps/worker/` directory and all Celery/Redis infrastructure. The collection and analysis runners already call worker code via lazy imports — those import paths are updated to reflect the new local locations.

## Architecture Decisions

### Decision: Copy vs. Move for worker code

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `git mv` then fix imports | Preserves file history but breaks `git blame` continuity across packages | Rejected — `git rm` + new files is cleaner; `git log --follow` on the new files still traces ancestry |
| Copy-as-is, then delete worker | Clean separation of move step from delete step; CI passes at each stage | **Chosen** — Step 1 moves (copy), Step 5 deletes worker |

### Decision: collection_helpers.py as separate file vs. inline in collection.py

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Paste helpers into collection.py | No new file but mixes task orchestrator logic with pure transformation functions | **Chosen** — fewer files, less churn. The helpers are only used by `collection.py` (the old `collection_tasks.py` also used them, but that file is deleted). |
| Separate helpers file | Cleaner separation, testable independently | Rejected — over-engineering for 3 small pure functions used in one caller |

### Decision: Preserve `worker.` references in import comments

Replace `from worker.connectors.x import Y` with `from app.connectors.x import Y`. No alias changes, no interface changes. The `worker` package name disappears entirely from the API's import graph.

## Data Flow

```
Before                         After
──────                         ─────
api/app/tasks/collection.py    api/app/tasks/collection.py
  └─ from worker.connectors.*    └─ from app.connectors.*
  └─ from worker.tasks.*         └─ from app.tasks.collection_helpers (inline)

api/app/tasks/analysis.py      api/app/tasks/analysis.py
  └─ from worker.ai.service      └─ from app.ai.service

worker/(dead)                  (deleted)
  ├─ connectors/  ──copy──►   api/app/connectors/
  ├─ ai/          ──copy──►   api/app/ai/
  ├─ tasks/       ──delete──► (helpers extracted, celery wrappers deleted)
  ├─ graphify/    ──delete──► (celery-only, api runs graphify via subprocess)
  └─ app.py       ──delete──► (celery app)
```

## File Changes

### MOVED (copy to API)

| API Target | Source | Reason |
|------------|--------|--------|
| `apps/api/app/connectors/__init__.py` | `apps/worker/worker/connectors/__init__.py` | Copy as-is |
| `apps/api/app/connectors/base.py` | `apps/worker/worker/connectors/base.py` | Copy as-is |
| `apps/api/app/connectors/openalex.py` | `apps/worker/worker/connectors/openalex.py` | Copy as-is |
| `apps/api/app/connectors/semantic_scholar.py` | `apps/worker/worker/connectors/semantic_scholar.py` | Copy as-is |
| `apps/api/app/connectors/lens.py` | `apps/worker/worker/connectors/lens.py` | Copy as-is |
| `apps/api/app/connectors/web.py` | `apps/worker/worker/connectors/web.py` | Copy as-is |
| `apps/api/app/ai/__init__.py` | `apps/worker/worker/ai/__init__.py` | Copy as-is |
| `apps/api/app/ai/client.py` | `apps/worker/worker/ai/client.py` | Copy as-is |
| `apps/api/app/ai/prompts.py` | `apps/worker/worker/ai/prompts.py` | Copy as-is |
| `apps/api/app/ai/schemas.py` | `apps/worker/worker/ai/schemas.py` | Copy as-is |
| `apps/api/app/ai/service.py` | `apps/worker/worker/ai/service.py` | Copy as-is |

### EXTRACTED (new file)

| File | Content | Source |
|------|---------|--------|
| `apps/api/app/tasks/collection_helpers.py` (NEW) | `_compute_checksum()`, `_build_search_query()`, `_is_source_selected()` — extracted from `collection_tasks.py` | `apps/worker/worker/tasks/collection_tasks.py` lines 40–79 |

### MODIFIED (imports updated)

| File | Change |
|------|--------|
| `apps/api/app/tasks/collection.py` | `from worker.connectors.openalex` → `from app.connectors.openalex` (×4 connectors) |
| `apps/api/app/tasks/collection.py` | `from worker.tasks.collection_tasks import ...` → `from app.tasks.collection_helpers import ...` |
| `apps/api/app/tasks/analysis.py` | `from worker.ai.service import AnalysisService` → `from app.ai.service import AnalysisService` |

### DELETED (entire worker directory)

| Path | Reason |
|------|--------|
| `apps/worker/` | Entire directory — Celery app, dead tasks, dead graphify adapter, tests, Dockerfile |
| `infra/docker/worker.Dockerfile` | Dead Dockerfile for deleted worker |

### MODIFIED (infrastructure)

| File | Changes |
|------|---------|
| `docker-compose.yml` (root) | Remove `redis:` service block, `worker:` service block, `redis_data:` volume, `REDIS_URL` from api env, `depends_on: redis` from api |
| `infra/docker/docker-compose.yml` | Remove `redis:` service block, `redis_data:` volume |
| `infra/docker-compose.prod.yml` | Remove `redis:` service, `worker:` service, `redisdata:` volume, all CELERY_* env vars |
| `infra/docker/start.sh` | Remove Redis start (lines 4–11), Celery start (line 17); keep migrations + uvicorn |
| `.env` | Remove lines 6 (REDIS_URL), 18–22 (CELERY_* vars) |
| `local.env` | Remove lines 6 (REDIS_URL), 18–22 (CELERY_* vars) |
| `.env.example` | Remove line 22 (CELERY_RESULT_SERIALIZER); add OPENAI_API_KEY, GEMINI_API_KEY (both blank), clean template |
| `Makefile` | Remove `cd apps/worker` lines from install, lint, test; remove `run-worker` target |
| `.github/workflows/ci.yml` | Remove `worker:` job block; update `e2e:` needs from `[api, worker, frontend]` to `[api, frontend]` |
| `.pre-commit-config.yaml` | Change `files: ^apps/(api|worker)/` → `files: ^apps/api/` (two ruff hooks) |
| `openspec/config.yaml` | Update context and stack to remove Celery, Redis, Valkey; simplify `task_queue: none` |

## Interfaces / Contracts

No interfaces change. The three extracted helpers keep identical signatures:

```python
def _compute_checksum(doc: dict) -> str: ...
def _build_search_query(strategy: Any) -> str: ...
def _is_source_selected(strategy: Any, source_name: str) -> bool: ...
```

## Dependency Audit

| Dep | In API pyproject? | Used by moved code? | Action |
|-----|-------------------|---------------------|--------|
| httpx | ✅ | connectors | None needed |
| boto3 | ✅ | connectors (S3) | None needed |
| tenacity | ✅ | connectors | None needed |
| trafilatura | ✅ | web connector | None needed |
| openai | ✅ | AI service | None needed |
| structlog | ✅ | All moved code | None needed |
| pydantic | ✅ | AI schemas | None needed |
| python-multipart | ✅ | web connector | None needed |
| PyMuPDF | ✅ | AI service (PDF) | None needed |
| celery | ❌ | Not used by moved code | Safe to omit |
| redis | ❌ | Not used by moved code | Safe to omit |
| jinja2 | ❌ | Not used by moved code | Safe to omit |

All deps needed by the moved code are **already present** in `apps/api/pyproject.toml`. No changes needed.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | collection_helpers | Run existing API tests — helpers are pure functions with no behavior change |
| Unit | connectors, ai | Run existing API tests — code copied verbatim, imports only change |
| CI | Full pipeline | Remove worker job; e2e no longer depends on worker |

**Verification**: `uv run pytest tests/ -v` in `apps/api/` must pass before and after each migration step.

## Migration / Rollout

No migration required. Data model is unchanged. Rollback via `git revert`.

### Step order (critical for zero-downtime):
1. Copy `connectors/` and `ai/` packages to API
2. Create `collection_helpers.py` with extracted functions
3. Update imports in `collection.py` and `analysis.py`
4. **Run tests** — verify everything passes with both old and new imports resolving
5. Delete `apps/worker/` directory
6. Update all infra files (docker-compose, env, CI, Makefile, pre-commit, openspec config)
7. **Final test run** — verify CI-equivalent passes

## Open Questions

- None — all resolved in proposal question round and codebase audit.

## PYTHONPATH Cleanup

After migration, `PYTHONPATH` no longer needs to include `apps/worker/`. The `from app.*` imports already work within `apps/api/` without PYTHONPATH manipulation. No remaining cross-app imports exist after the import path updates.
