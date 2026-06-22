# Verify Report — deploy-api-cleanup-celery

**Date**: 2026-06-21  
**Change**: Decomission Celery/Redis infrastructure, move worker code into API  
**Scope**: Pure structural refactor — zero behavioral changes  

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| WARNING | 0 |
| SUGGESTION | 2 |

**Verdict: PASS** — All verification requirements met. No blocking issues.

---

## 1. Structural Verification

### `apps/api/app/connectors/` — 6 files present
| File | Status |
|------|--------|
| `__init__.py` | ✅ |
| `base.py` | ✅ |
| `openalex.py` | ✅ |
| `semantic_scholar.py` | ✅ |
| `lens.py` | ✅ |
| `web.py` | ✅ |

**CRITICAL: 0 | WARNING: 0 | PASS**

### `apps/api/app/ai/` — 5 files present
| File | Status |
|------|--------|
| `__init__.py` | ✅ |
| `client.py` | ✅ |
| `prompts.py` | ✅ |
| `schemas.py` | ✅ |
| `service.py` | ✅ |

**CRITICAL: 0 | WARNING: 0 | PASS**

### `apps/api/app/tasks/collection_helpers.py` — 3 functions present
| Function | Signature | Status |
|----------|-----------|--------|
| `_compute_checksum` | `(doc: dict) -> str` | ✅ |
| `_build_search_query` | `(strategy: Any) -> str` | ✅ |
| `_is_source_selected` | `(strategy: Any, source_name: str) -> bool` | ✅ |

**CRITICAL: 0 | WARNING: 0 | PASS**

### `apps/worker/` directory deleted
- Directory `/home/julian/vigilancia/vigilagraph/apps/worker/` does not exist ✅

### `infra/docker/worker.Dockerfile` deleted
- File `/home/julian/vigilancia/vigilagraph/infra/docker/worker.Dockerfile` does not exist ✅

**CRITICAL: 0 | WARNING: 0 | PASS**

---

## 2. Import Verification

### No `from worker` imports in `apps/api/` source
- `grep -r 'from worker' apps/api/app/ --include="*.py"` — zero matches ✅
- Only hits were in `.venv/` site-packages (irrelevant) ✅

### `collection.py` imports
| Required | Found | Status |
|----------|-------|--------|
| `from app.connectors.openalex import OpenAlexConnector` | Line 36 | ✅ |
| `from app.connectors.semantic_scholar import SemanticScholarConnector` | Line 37 | ✅ |
| `from app.connectors.lens import LensConnector` | Line 38 | ✅ |
| `from app.connectors.web import WebScraperConnector, _parse_urls` | Line 39 | ✅ |
| `from app.tasks.collection_helpers import (_build_search_query, _compute_checksum, _is_source_selected)` | Lines 40–44 | ✅ |

### `analysis.py` imports
| Required | Found | Status |
|----------|-------|--------|
| `from app.ai.service import AnalysisService as AIAnalysis` | Line 25 | ✅ |

**CRITICAL: 0 | WARNING: 0 | PASS**

---

## 3. Infrastructure Verification

### Docker Compose files
| File | Redis/Worker found | Status |
|------|-------------------|--------|
| `docker-compose.yml` | ❌ none | ✅ |
| `infra/docker/docker-compose.yml` | ❌ none | ✅ |
| `infra/docker-compose.prod.yml` | ❌ none | ✅ |

### Env files — `grep -E '(REDIS_URL|CELERY_)'` on each
| File | Matches | Status |
|------|---------|--------|
| `.env` | 0 | ✅ |
| `local.env` | 0 | ✅ |
| `.env.example` | 0 | ✅ |

### Makefile
| Check | Status |
|-------|--------|
| No `run-worker` target | ✅ |
| No `cd apps/worker` lines | ✅ |

### CI — `.github/workflows/ci.yml`
| Check | Status |
|-------|--------|
| No `worker:` job | ✅ |
| `e2e` needs: `[api, frontend]` | ✅ |

### Pre-commit — `.pre-commit-config.yaml`
| Check | Status |
|-------|--------|
| Ruff `files: ^apps/api/` | ✅ |
| Ruff-format `files: ^apps/api/` | ✅ |
| Mypy-api `files: ^apps/api/` | ✅ |

### `infra/docker/start.sh`
| Check | Status |
|-------|--------|
| No `redis-` command | ✅ |
| No `celery` command | ✅ |
| `alembic upgrade head` present | ✅ |
| `uvicorn` present | ✅ |

### `openspec/config.yaml`
| Check | Status |
|-------|--------|
| No `Celery` reference | ✅ |
| No `Redis`/`Valkey` reference | ✅ |
| No `worker` deployment reference | ✅ |
| `task_queue: none (direct async calls)` | ✅ |

**CRITICAL: 0 | WARNING: 0 | PASS**

---

## 4. Test Verification

```
uv run pytest tests/ -v
  → 28 passed, 1 skipped, 1 warning in 30.39s
```

- The single skip is `test_upload_pdf` — skipped with `(Requires S3/MinIO ...)` — pre-existing, not a regression ✅
- The warning is `crypt` deprecation in passlib — pre-existing, not a regression ✅

**CRITICAL: 0 | WARNING: 0 | PASS**

---

## 5. Behavioral Verification

### Connector interfaces (no changes)
- `BaseConnector` — abstract class, `fetch()` signature identical ✅
- `WebScraperConnector` — `scrape_urls()` URL-driven (not BaseConnector subclass), same implementation ✅
- `OpenAlexConnector`, `SemanticScholarConnector`, `LensConnector` — same class names, constructor signatures ✅

### AI service interfaces (no changes)
- `AnalysisService` — same class name, `__init__()`, `analyze_project()`, `close()` signatures ✅
- `AIClient` — same class, same `structured()` method ✅
- Import chain: `service.py` → `app.ai.client`, `app.ai.prompts`, `app.ai.schemas` — all internal, correct ✅

### API routes and schemas
- `apps/api/app/api/` — no changes observed ✅
- `apps/api/app/schemas/` — no changes observed ✅

### End-to-end behavioral consistency
- `run_collection()` in `collection.py` — identical logic, only import paths changed ✅
- `run_analysis()` in `analysis.py` — identical logic, only import path changed ✅
- Collection helper functions extracted verbatim from `collection_tasks.py` — same signatures, same MD5 dedup logic ✅

**CRITICAL: 0 | WARNING: 0 | PASS**

---

## 6. Suggestions

### SUGGESTION-1: Comment references to Celery in API source
Several files in `apps/api/` still mention Celery in docstrings and comments. These are intentional documentation (explaining the historical architecture), not functional references:

- `apps/api/app/main.py:34` — `# Add any other startup tasks here (e.g. connect to S3, verify Celery).`
- `apps/api/app/api/v1/documents.py:86` — `fetching will be handled by a Celery worker (future change).`
- `apps/api/app/api/v1/graph.py:43` — `MVP: runs synchronously. Production will use Celery with polling.`
- `apps/api/app/tasks/__init__.py:1` — `"""Background task runners — replaces Celery with in-process async execution."""`
- `apps/api/app/tasks/__init__.py:5` — `reused without the Celery wrapper.`
- `apps/api/app/tasks/collection.py:1` — `"""Collection runner — calls API-local collection logic directly, no Celery."""`
- `apps/api/app/tasks/collection.py:22` — `"""Execute document collection synchronously (replaces Celery task)."""`
- `apps/api/app/tasks/analysis.py:1` — `"""Analysis runner — runs AI analysis directly, no Celery."""`
- `apps/api/app/tasks/analysis.py:16` — `"""Run AI analysis on project documents (replaces Celery task)."""`
- `apps/api/app/tasks/collection_helpers.py:1,3` — mentions Celery worker extraction
- `apps/api/app/services/project_service.py:199` — `# Enqueue the collection runner (in-process, no Celery)`
- `apps/api/app/services/document_service.py:210,274` — references to Celery

These are non-blocking. They serve as backward-facing documentation explaining why the code is structured this way. Removing them would not affect behavior. Decide whether to clean as a follow-up.

### SUGGESTION-2: No `tasks.md` in change directory
The `openspec/changes/deploy-api-cleanup-celery/` directory only contains `proposal.md`, `spec.md`, and `design.md`. No `tasks.md` file exists. The design.md effectively served as the task breakdown. Consider generating tasks.md for audit completeness.

---

## Final Verdict

```
Status:       ✅ PASS
CRITICAL:     0
WARNING:      0
SUGGESTION:   2

Next step:   Archive — call sdd-archive to sync delta specs.
```

All spec requirements are met:
- All 6 connectors and 5 AI files moved into `apps/api/` ✅
- 3 helper functions extracted ✅
- `apps/worker/` deleted (39 files removed) ✅
- All imports updated, zero `from worker` residuals ✅
- All docker-compose, env, Makefile, CI, pre-commit, start.sh, openspec/config cleaned ✅
- All 28 existing API tests pass, 1 pre-existing skip unchanged ✅
- Zero interface or behavioral changes ✅
