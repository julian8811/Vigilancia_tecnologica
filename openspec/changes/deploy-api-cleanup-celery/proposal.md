# Proposal: Deploy API + Cleanup Celery/Redis

## Intent

Remove the dead Celery/Redis task-queue infrastructure and move actively-used worker code into the API package. This unblocks PythonAnywhere deployment by eliminating the Redis dependency and simplifies the project's architecture from 3 apps to 2 (API + Web).

## Scope

### In Scope
- Move worker connectors (OpenAlex, Semantic Scholar, Lens, Web) into `apps/api/app/connectors/`
- Move worker AI service (client, prompts, schemas, service) into `apps/api/app/ai/`
- Extract 3 collection helpers into `apps/api/app/tasks/collection_helpers.py`
- Update import paths in `apps/api/app/tasks/collection.py` and `analysis.py`
- Add missing deps to `apps/api/pyproject.toml` (none needed — all worker deps already present or unused)
- Delete `apps/worker/` entirely
- Remove Redis + worker services from all docker-compose files
- Remove CELERY_*, REDIS_URL from all env files
- Remove worker CI job, Makefile targets, pre-commit patterns
- Update openspec config to reflect simplified stack
- Clean `.env.example` into a complete template

### Out of Scope
- Changing connector/AI service behavior or interfaces
- Adding new API endpoints or capabilities
- Frontend changes
- Actual PythonAnywhere deploy (this prepares the codebase for it)
- Removing MinIO/S3 storage (still used by the API for document storage)

## Capabilities

### New Capabilities
None — pure refactor with no behavioral changes.

### Modified Capabilities
None — spec-level behavior unchanged; connectors, collection, and analysis work identically.

## Approach

1. **Create** `apps/api/app/connectors/` and `apps/api/app/ai/` packages by copying modules from `apps/worker/worker/` as-is (no behavioral changes).
2. **Extract** 3 helper functions (`_build_search_query`, `_compute_checksum`, `_is_source_selected`) into a new `apps/api/app/tasks/collection_helpers.py`.
3. **Update** import paths in `collection.py` and `analysis.py` to point to new local locations.
4. **Remove** all Celery/Redis code, infra files, env vars, CI jobs, Makefile targets, and pre-commit patterns.
5. **Delete** `apps/worker/` directory entirely.
6. **Update** config files and documentation to reflect the simplified stack.
7. **Verify** all existing tests pass with updated imports.

## Affected Areas

| Area | Impact | Description |
|------|--------|------------|
| `apps/api/app/connectors/` | New | 6 files from worker: base, openalex, semantic_scholar, lens, web, `__init__` |
| `apps/api/app/ai/` | New | 5 files from worker: client, prompts, schemas, service, `__init__` |
| `apps/api/app/tasks/collection_helpers.py` | New | 3 helper functions extracted from worker |
| `apps/api/app/tasks/collection.py` | Modified | Imports from `worker.*` → `app.connectors.*` + `app.tasks.collection_helpers` |
| `apps/api/app/tasks/analysis.py` | Modified | Imports from `worker.ai.service` → `app.ai.service` |
| `apps/api/pyproject.toml` | Modified | None changes needed (all deps already present) |
| `apps/worker/` | Removed | Entire directory (~20 files) |
| `infra/docker/worker.Dockerfile` | Removed | Dead Dockerfile |
| `docker-compose.yml` (root) | Modified | Remove redis + worker services, redis_data volume |
| `infra/docker/docker-compose.yml` | Modified | Remove redis service, redis_data volume |
| `infra/docker-compose.prod.yml` | Modified | Remove redis + worker services, CELERY_* env vars |
| `infra/docker/start.sh` | Modified | Remove Redis start + Celery start, keep migrations + uvicorn |
| `.env` | Modified | Remove CELERY_*, REDIS_URL |
| `.env.example` | Modified | Full template with DATABASE_URL, JWT_SECRET, API keys, FRONTEND_URL |
| `local.env` | Modified | Remove CELERY_*, REDIS_URL |
| `Makefile` | Modified | Drop run-worker, worker install/lint/test lines |
| `.github/workflows/ci.yml` | Modified | Remove worker job, update e2e `needs` |
| `.pre-commit-config.yaml` | Modified | Remove `worker` from ruff/mypy file patterns |
| `openspec/config.yaml` (both) | Modified | Remove Celery/Redis from stack context |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Connector imports break if PYTHONPATH changes | Low | All imports become `app.connectors.*` — absolute from project root |
| Missing worker dependency not in API | Low | Audited both pyproject.toml files; API already has all needed deps |
| Git history lost for deleted worker files | Low | Git retains history; `git log -- apps/worker/` still works after deletion |
| Docker-compose users lose local Redis | Med | Redis was only used by dead Celery; no runtime code reads it |

## Rollback Plan

1. `git revert` the merge commit for this change.
2. Restore `apps/worker/` and docker-compose files from the reverted commit.
3. Re-add CELERY_* env vars and CI jobs.
4. No data migration needed — database schema is unchanged.

## Dependencies

- Worker code must be moved to API *before* deleting `apps/worker/` (so imports still resolve during migration).
- All existing tests must pass after import path updates.
- PR must be reviewed before merge (per strategy: ask-always, review budget: 400 lines).

## Open Questions

- None — all answered in question round.

## Success Criteria

- [ ] `apps/worker/` directory deleted from filesystem
- [ ] No `from worker import` or `worker.` references anywhere in `apps/api/`
- [ ] No CELERY_* or REDIS_URL in any env file
- [ ] No `redis` or `worker` service in any docker-compose file
- [ ] No `worker` job in `.github/workflows/ci.yml`
- [ ] `uv run pytest tests/ -v` passes in `apps/api/`
- [ ] Docker Compose starts without Redis (api + postgres + minio only)
