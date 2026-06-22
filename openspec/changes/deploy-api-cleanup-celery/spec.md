# Spec — deploy-api-cleanup-celery

**Domain**: code-organization  
**Type**: NEW (pure refactor, no behavioral changes)  
**Change**: Decomission Celery/Redis infrastructure and move active worker code into the API package.

---

## Purpose

Remove the dead Celery task-queue infrastructure and relocate all actively-used worker modules into `apps/api/app/`, eliminating the `apps/worker/` directory and the Redis dependency. This is a pure code reorganization — no connector, AI service, or task behavior changes.

---

## Requirements

### NEW Package Structure

### Requirement: Connector package moved to `apps/api/app/connectors/`

The system MUST copy the 6 files from `apps/worker/worker/connectors/` into `apps/api/app/connectors/` preserving internal imports, class names, and module structure.

| Source (apps/worker/worker/connectors/) | Destination (apps/api/app/connectors/) |
|-----------------------------------------|----------------------------------------|
| `__init__.py`                           | `__init__.py`                          |
| `base.py`                               | `base.py`                              |
| `openalex.py`                           | `openalex.py`                          |
| `semantic_scholar.py`                   | `semantic_scholar.py`                  |
| `lens.py`                               | `lens.py`                              |
| `web.py`                                | `web.py`                                |

#### Scenario: Connector modules are importable from their new path

- GIVEN the files have been copied to `apps/api/app/connectors/`
- WHEN a Python module does `from app.connectors.openalex import OpenAlexConnector`
- THEN the import resolves without error
- AND the connector class behaves identically to the original

### Requirement: AI service package moved to `apps/api/app/ai/`

The system MUST copy the 5 files from `apps/worker/worker/ai/` into `apps/api/app/ai/`, preserving all class names, prompt templates, Pydantic schemas, and import chain.

| Source (apps/worker/worker/ai/) | Destination (apps/api/app/ai/) |
|---------------------------------|-------------------------------|
| `__init__.py`                   | `__init__.py`                 |
| `client.py`                     | `client.py`                   |
| `prompts.py`                    | `prompts.py`                  |
| `schemas.py`                    | `schemas.py`                  |
| `service.py`                    | `service.py`                    |

#### Scenario: AI modules are importable from their new path

- GIVEN the files have been copied to `apps/api/app/ai/`
- WHEN a Python module does `from app.ai.service import AnalysisService`
- THEN the import resolves without error
- AND `AnalysisService.analyze_project()` works identically

### Requirement: Collection helper functions extracted to `apps/api/app/tasks/collection_helpers.py`

The system MUST define a new module `apps/api/app/tasks/collection_helpers.py` containing exactly these 3 functions copied from `apps/worker/worker/tasks/collection_tasks.py`:

| Function | Signature |
|----------|-----------|
| `_build_search_query` | `(strategy: Any) -> str` |
| `_compute_checksum` | `(doc: dict) -> str` |
| `_is_source_selected` | `(strategy: Any, source_name: str) -> bool` |

#### Scenario: Helpers are importable and behave identically

- GIVEN `collection_helpers.py` exists in `apps/api/app/tasks/`
- WHEN `from app.tasks.collection_helpers import _build_search_query, _compute_checksum, _is_source_selected`
- THEN all 3 functions resolve
- AND `_compute_checksum({"title": "Test", "abstract": "", "authors": [], "doi": ""})` returns the same MD5 hash as the original

### Requirement: Import paths updated in `apps/api/app/tasks/collection.py`

All `from worker.*` imports MUST be replaced with `from app.connectors.*` and `from app.tasks.collection_helpers`.

| Old import | New import |
|------------|------------|
| `from worker.connectors.openalex import OpenAlexConnector` | `from app.connectors.openalex import OpenAlexConnector` |
| `from worker.connectors.semantic_scholar import SemanticScholarConnector` | `from app.connectors.semantic_scholar import SemanticScholarConnector` |
| `from worker.connectors.lens import LensConnector` | `from app.connectors.lens import LensConnector` |
| `from worker.connectors.web import WebScraperConnector, _parse_urls` | `from app.connectors.web import WebScraperConnector, _parse_urls` |
| `from worker.tasks.collection_tasks import (_build_search_query, _compute_checksum, _is_source_selected)` | `from app.tasks.collection_helpers import (_build_search_query, _compute_checksum, _is_source_selected)` |

#### Scenario: collection.py runs without ImportError

- GIVEN the new packages exist and imports are updated
- WHEN `run_collection()` is invoked
- THEN no `ModuleNotFoundError` occurs
- AND all connector and helper calls produce identical results

### Requirement: Import path updated in `apps/api/app/tasks/analysis.py`

| Old import | New import |
|------------|------------|
| `from worker.ai.service import AnalysisService as AIAnalysis` | `from app.ai.service import AnalysisService as AIAnalysis` |

#### Scenario: analysis.py runs without ImportError

- GIVEN the AI package exists at `apps/api/app/ai/`
- WHEN `run_analysis()` is invoked
- THEN no `ModuleNotFoundError` occurs
- AND `AnalysisService.analyze_project()` produces identical results

### FILES TO DELETE

### Requirement: `apps/worker/` directory removed entirely

The system MUST delete the entire `apps/worker/` directory tree including all subdirectories and files, with no code migration from files not already relocated.

#### Scenario: Worker directory is deleted

- GIVEN all active worker code has been moved to `apps/api/app/`
- WHEN `rm -rf apps/worker/` is executed
- THEN the directory no longer exists
- AND no import or runtime reference to `apps/worker/` remains in `apps/api/`

### Requirement: `infra/docker/worker.Dockerfile` removed

#### Scenario: Worker Dockerfile is deleted

- GIVEN the worker service no longer exists
- WHEN the file `infra/docker/worker.Dockerfile` is deleted
- THEN no docker-compose file references it

### Requirement: Redis services and volumes removed from all docker-compose files

The system MUST remove the `redis` service, `worker` service, `redis_data` volume, and all `depends_on: redis` entries from:
- `docker-compose.yml` (root)
- `infra/docker-compose.prod.yml`
- `infra/docker/docker-compose.yml`

#### Scenario: docker-compose.yml has no redis or worker

- GIVEN all docker-compose files have been edited
- WHEN `docker compose config` is run on each file
- THEN no `redis:` or `worker:` service exists
- AND no `redis_data` volume exists
- AND no `depends_on: redis` references remain

### FILES TO CLEAN

### Requirement: Env files stripped of Celery/Redis variables

The following variables MUST be removed from `.env`, `local.env`, and `.env.example`:
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_TASK_SERIALIZER`
- `CELERY_RESULT_SERIALIZER`
- `CELERY_ACCEPT_CONTENT`
- `CELERY_*` (any other Celery-prefixed var)

Additionally, `.env.example` MUST be cleaned into a complete template with only active variables.

#### Scenario: No Celery/Redis env vars remain

- GIVEN the env files have been edited
- WHEN `grep -E '^(REDIS_URL|CELERY_)'` is run on each env file
- THEN no matches are found

### Requirement: Docker Compose env vars cleaned

Remove `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` references from Compose `environment:` blocks in all docker-compose files. Remove the `env_file: local.env` on the (now-deleted) worker service.

### Requirement: `infra/docker/start.sh` simplified

Remove Redis daemon start (`redis-server`), Redis health-wait loop, and Celery worker background start. Keep: alembic migration and uvicorn (foreground).

#### Scenario: start.sh has no Redis or Celery references

- GIVEN `start.sh` has been edited
- WHEN the file is read
- THEN no `redis-` or `celery` command appears
- AND `alembic upgrade head` and `uvicorn` remain

### Requirement: Makefile targets cleaned

Remove the `run-worker` target. Remove `cd apps/worker` lines from `install`, `lint`, and `test` targets. The `e2e` CI `needs` list MUST drop `worker`.

#### Scenario: No worker make targets exist

- GIVEN the Makefile has been edited
- WHEN `make help` is run
- THEN no `run-worker` target appears
- AND `install` no longer references `apps/worker`

### Requirement: CI workflow cleaned

Remove the entire `worker:` job from `.github/workflows/ci.yml`. Remove `worker` from the `e2e` job's `needs:` list.

#### Scenario: CI has no worker job

- GIVEN `.github/workflows/ci.yml` has been edited
- WHEN the file is read
- THEN no `worker:` job exists
- AND the `e2e` job `needs:` only references `[api, frontend]`

### Requirement: Pre-commit config narrowed

Remove `worker` from the `files:` patterns for `ruff` and `ruff-format` hooks. Pattern MUST change from `^apps/(api|worker)/` to `^apps/api/`.

#### Scenario: Pre-commit no longer scans worker

- GIVEN `.pre-commit-config.yaml` has been edited
- WHEN the file is read
- THEN no pattern contains `worker`

### Requirement: openspec/config.yaml updated

Remove Celery, Redis, and worker references from the `context:` string and `stack:` sections. Update task_queue entry and cache_queue entry.

#### Scenario: Config reflects simplified stack

- GIVEN `openspec/config.yaml` has been edited
- WHEN the file is read
- THEN no `Celery`, `task_queue`, or `worker` deployment appears
- AND `cache_queue` no longer mentions Redis/Valkey

### VERIFICATION

### Requirement: All existing API tests pass

The system MUST verify that `uv run pytest tests/ -v` in `apps/api/` succeeds with no regressions.

#### Scenario: API test suite passes

- GIVEN all code has been moved, imports updated, and files deleted
- WHEN `uv run pytest tests/ -v` is run in `apps/api/`
- THEN exit code is 0
- AND all previously-passing tests still pass

### Requirement: No residual `from worker import` in `apps/api/`

The system MUST verify zero references to the old worker package.

#### Scenario: Grep finds no worker imports in API

- GIVEN all changes are complete
- WHEN `grep -r 'from worker' apps/api/` is run
- THEN no matches are returned

### Requirement: No Redis or Celery in env files or docker-compose

- WHEN `grep -E '(CELERY_|REDIS_URL)'` is run on all env files and docker-compose files
- THEN zero matches

### NON-FUNCTIONAL

### Requirement: Zero behavioral changes

The system MUST NOT alter the logic, interface, or output of any connector, AI service, or task function. Only import paths and file locations change.

#### Scenario: Behavior is preserved end-to-end

- GIVEN identical inputs to `run_collection()` and `run_analysis()`
- WHEN comparing pre-refactor and post-refactor execution
- THEN document deduplication, collection results, and analysis output are byte-identical
