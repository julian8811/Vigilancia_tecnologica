# Spec: Code Organization — VigilaGraph IA

> Current monorepo structure and module boundaries after Celery/Redis decomission.

---

## Architecture Overview

The system is a 2-app monorepo under `vigilagraph/`:
- **apps/api/** — FastAPI backend (Python 3.12, SQLAlchemy async, httpx, OpenAI)
- **apps/web/** — Next.js 14 (App Router) frontend (TypeScript, TanStack Query, shadcn/ui)

The former `apps/worker/` directory and all Celery/Redis infrastructure have been removed. Background tasks run synchronously in-process via direct async calls.

---

## Requirement: API Package Structure

The API package (`apps/api/app/`) MUST organize code into the following top-level subpackages:

| Package | Purpose |
|---------|---------|
| `api/` | FastAPI route handlers (versioned under `v1/`) |
| `schemas/` | Pydantic v2 request/response schemas |
| `models/` | SQLAlchemy 2 ORM models |
| `repositories/` | Data access layer (BaseRepository pattern) |
| `services/` | Business logic layer |
| `tasks/` | Background task runners (in-process, no Celery) |
| `connectors/` | External source connectors (OpenAlex, Semantic Scholar, Lens, Web) |
| `ai/` | AI service client, prompts, schemas, and analysis service |

**Scenario: API package structure is valid**

- GIVEN the source tree under `apps/api/app/`
- WHEN inspected
- THEN each subpackage listed above exists
- AND no `worker` subpackage or cross-app import exists

---

## Requirement: Connector Package

`apps/api/app/connectors/` MUST provide 6 files with stable interfaces:

| File | Class/Module |
|------|-------------|
| `__init__.py` | Package export |
| `base.py` | `BaseConnector` abstract class |
| `openalex.py` | `OpenAlexConnector` |
| `semantic_scholar.py` | `SemanticScholarConnector` |
| `lens.py` | `LensConnector` |
| `web.py` | `WebScraperConnector`, `_parse_urls` |

All connectors are imported as `from app.connectors.<name> import <Class>`.

---

## Requirement: AI Service Package

`apps/api/app/ai/` MUST provide 5 files:

| File | Module |
|------|--------|
| `__init__.py` | Package export |
| `client.py` | `AIClient` |
| `prompts.py` | Prompt templates |
| `schemas.py` | Pydantic schemas for AI responses |
| `service.py` | `AnalysisService` |

All AI modules import internally as `from app.ai.<name> import ...`.

---

## Requirement: Task Runner Package

`apps/api/app/tasks/` MUST provide in-process task runners:

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring explaining no-Celery architecture |
| `collection.py` | `run_collection()` — synchronous document collection |
| `analysis.py` | `run_analysis()` — synchronous AI analysis |
| `collection_helpers.py` | `_build_search_query()`, `_compute_checksum()`, `_is_source_selected()` |

**Scenario: Tasks are importable without Celery**

- GIVEN the tasks package
- WHEN `from app.tasks.collection import run_collection` is called
- THEN it executes synchronously without Celery dependency
- AND imports resolve from `app.connectors.*` and `app.ai.*`

---

## Requirement: No Worker or Celery Dependencies

The codebase MUST have zero runtime or build dependencies on:
- `celery`
- `redis`
- `apps/worker/` directory
- `CELERY_*` or `REDIS_URL` environment variables
- Celery/Redis docker-compose services

All infrastructure files (docker-compose, Makefile, CI, pre-commit, env templates) MUST reflect this simplified architecture.
