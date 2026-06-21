# Tasks: Deferred Cleanup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150 (mostly deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Suggested work units | Single PR |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Dead Code & Unused Exports

- [x] 1.1 Remove `GraphifyAdapter.run_sync()` from `apps/worker/worker/graphify/adapter.py`
- [x] 1.2 Remove 5 unused schemas from `apps/api/app/schemas/__init__.py` exports
- [x] 1.3 Remove `scrapling>=0.1` from `apps/worker/pyproject.toml`

## Phase 2: Deduplicate Type Maps

- [x] 2.1 Create `apps/api/app/core/graph_types.py` with `NODE_TYPE_MAP` and `EDGE_TYPE_MAP`
- [x] 2.2 Update `apps/worker/worker/graphify/parser.py` to import from shared
- [x] 2.3 Update `apps/api/app/services/graph_service.py` to import from shared

## Phase 3: Import & Code Quality Fixes

- [x] 3.1 Deduplicate `import re` in `apps/worker/worker/connectors/web.py`
- [x] 3.2 Remove inline `import re as _re` from `apps/api/app/services/project_service.py`
- [x] 3.3 Remove inline `import json` and `import shutil` from `graph_service.py`
- [x] 3.4 Replace `datetime.utcnow()` with `datetime.now(UTC)` in `corpus_service.py`
- [x] 3.5 Move lazy connector imports to top-level in `collection_tasks.py`
- [x] 3.6 Fix `service._get_run()` → `service.get_run()` in `apps/api/app/api/v1/graph.py`

## Phase 4: Verification

- [x] 4.1 Run backend tests: 28 passed, 1 skipped
- [x] 4.2 Run worker tests: 16 passed
- [x] 4.3 Grep for dead patterns: 0 hits for `run_sync`, `scrapling`, `utcnow`, `_get_run`
