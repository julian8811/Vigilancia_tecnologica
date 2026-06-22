# Archive Report — deploy-api-cleanup-celery

**Archived**: 2026-06-21
**Change**: Decommission Celery/Redis infrastructure, move active worker code into API
**Verdict**: PASS — 0 CRITICAL, 0 WARNING, 2 SUGGESTIONS

---

## Intent

Remove the dead Celery/Redis task-queue infrastructure and move actively-used worker code into the API package. This unblocked PythonAnywhere deployment by eliminating the Redis dependency and simplified the project from 3 apps to 2 (API + Web).

## Scope

### Completed
- **Moved** `apps/worker/worker/connectors/` (6 files) → `apps/api/app/connectors/`
- **Moved** `apps/worker/worker/ai/` (5 files) → `apps/api/app/ai/`
- **Extracted** 3 helper functions into `apps/api/app/tasks/collection_helpers.py`
- **Updated** imports in `collection.py` and `analysis.py` (zero `from worker` residuals)
- **Deleted** entire `apps/worker/` directory (39 files)
- **Cleaned** docker-compose (3 files), env files (3 files), Makefile, CI, pre-commit, start.sh
- **Updated** `openspec/config.yaml` — removed Celery/Redis/worker references
- **Fixed** 5 misleading Celery comments in docstrings
- **Verified** 28 tests pass, 1 pre-existing skip, zero regressions

### Not Changed
- Connector/AI service behavior or interfaces (pure refactor)
- API endpoints or capabilities
- Frontend code
- MinIO/S3 storage

## Task Completion

| Metric | Value |
|--------|-------|
| Tasks total | 15 |
| Tasks complete | 15 |
| Tasks incomplete | 0 |
| Task artifact | `tasks.md` (consolidated from vigilagraph tree) |

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| `code-organization` | Created (full spec) | New main spec capturing 2-app monorepo structure, no Celery/Redis |
| `config.yaml` | Updated | Removed Celery/Redis/Valkey/worker from context, stack, and testing sections |

## Verification Summary

| Check | Result |
|-------|--------|
| Structural: connectors/ (6 files) | ✅ |
| Structural: ai/ (5 files) | ✅ |
| Structural: collection_helpers.py (3 funcs) | ✅ |
| Structural: worker/ deleted | ✅ (39 files removed) |
| Imports: zero `from worker` residuals | ✅ |
| Docker Compose: no redis/worker services | ✅ (3 files) |
| Env files: no CELERY_* or REDIS_URL | ✅ (3 files) |
| Makefile: no worker targets | ✅ |
| CI: no worker job | ✅ |
| Pre-commit: no worker patterns | ✅ |
| start.sh: no redis/celery commands | ✅ |
| Tests: 28 passed, 1 skipped | ✅ |
| Config: no Celery/Redis/Valkey | ✅ |
| Behavioral: zero interface changes | ✅ |

## Suggestions (non-blocking)

1. **SUGGESTION-1**: Several docstrings in API source still mention Celery as backward-facing documentation. These are intentional historical references and do not affect behavior.
2. **SUGGESTION-2**: No `tasks.md` existed in the change directory at verify time (noted in verify report). Resolved during archive by consolidating from vigilagraph tree.

## Source of Truth Updated

The following now reflect the new architecture:
- `openspec/config.yaml` — simplified stack, no Celery/Redis/worker
- `openspec/specs/code-organization/spec.md` — new main spec for 2-app monorepo

## SDD Cycle Complete

```
Proposal  →  Spec  →  Design  →  Tasks  →  Apply  →  Verify  →  Archive  ✅
```

All phases completed. Change fully planned, implemented, verified, and archived.
