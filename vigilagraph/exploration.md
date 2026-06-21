# Exploration: Deuda Técnica — VigilaGraph IA

## 1. Backend Repositories (`apps/api/app/repositories/`)

### Current State

**`BaseRepository`** provides generic CRUD:
- `get(id)`, `list(**filters)`, `create(schema)`, `update(id, schema)`, `delete(id)`

**Repos that DO inherit** (9 of 14 — correct):
| Repo | Inherits From | Notes |
|------|--------------|-------|
| `UserRepository` | ✅ `BaseRepository[User]` | Clean |
| `ProjectRepository` | ✅ `BaseRepository[SurveillanceProject]` | Clean |
| `SearchStrategyRepository` | ✅ `BaseRepository[SearchStrategy]` | Clean |
| `OrganizationRepository` | ✅ `BaseRepository[Organization]` | Clean |
| `CollectionRunRepository` | ✅ `BaseRepository[CollectionRun]` | Clean |
| `DocumentRepository` | ✅ `BaseRepository[Document]` | Clean |
| `GraphRunRepository` | ✅ `BaseRepository[GraphRun]` | Clean |
| `GraphNodeRepository` | ✅ `BaseRepository[GraphNode]` | Clean |
| `GraphEdgeRepository` | ✅ `BaseRepository[GraphEdge]` | Clean |

**Repos that do NOT inherit** (5 of 14 — duplicated CRUD):

1. **`TechnologyRepository`** — Standalone, 3 methods duplicate list/bulk/delete
2. **`TrendRepository`** — Standalone, 3 methods duplicate list/bulk/delete
3. **`ActorRepository`** — Standalone, 3 methods duplicate list/bulk/delete
4. **`OpportunityRepository`** — Standalone, 3 methods duplicate list/bulk/delete
5. **`ReportRepository`** — Standalone, 4 methods duplicate get/create/delete/list

### Duplicated Code Volume

The 4 analysis repos (`Technology`, `Trend`, `Actor`, `Opportunity`) are copy-paste templates:
- Each has `list_by_project()` — pagination logic × 4 = **~40 lines duplicated**
- Each has `bulk_insert()` — session add_all + flush × 4 = **~16 lines duplicated**
- Each has `delete_by_project()` — delete query × 4 = **~20 lines duplicated**

**`ReportRepository`** duplicates `get()`, `create()`, `delete()`, `list_by_project()` that `BaseRepository` already provides = **~40 lines duplicated**

**Total: ~160 lines of duplicated CRUD code that would be eliminated** by migrating to `BaseRepository`.

### Additional Issues

- `TechnologyRepository` et al. are NOT exported from `repositories/__init__.py` (missing from `__all__`)
- `ReportRepository` is NOT exported from `repositories/__init__.py` (missing from `__all__`)
- `analysis_repository.py` and `report_repository.py` are excluded from `repositories/__init__.py`

### Affected Files
- `apps/api/app/repositories/analysis_repository.py` — TechnologyRepository, TrendRepository, ActorRepository, OpportunityRepository
- `apps/api/app/repositories/report_repository.py` — ReportRepository
- `apps/api/app/repositories/__init__.py` — missing exports

---

## 2. Dead Code Scan

### Connectors — All Used

| Connector | Used In | Status |
|-----------|---------|--------|
| `connectors/openalex.py` | `collection_tasks.py` line 143 | ✅ Alive |
| `connectors/semantic_scholar.py` | `collection_tasks.py` line 147 | ✅ Alive |
| `connectors/lens.py` | `collection_tasks.py` line 153 | ✅ Alive |
| `connectors/web.py` | `collection_tasks.py` line 159 | ✅ Alive |

### Dead Code Items

**1. `GraphifyAdapter.run_sync()`** — `apps/worker/worker/graphify/adapter.py:149-211`
- Marked as "kept for backward compatibility" but nothing calls it
- The worker uses `run_async()`, the API uses its own inline subprocess in `GraphService.generate()`
- **~60 lines of dead code**

**2. Unused Schemas** — defined but never imported outside schema files:
| Schema | File | Last Used |
|--------|------|-----------|
| `DocumentUpdate` | `schemas/document.py` | Only in schema's own module + `__init__.py` |
| `UserCreate` | `schemas/user.py` | Only in schema's own module + `__init__.py` |
| `UserUpdate` | `schemas/user.py` | Only in schema's own module + `__init__.py` |
| `OrganizationUpdate` | `schemas/organization.py` | Only in schema's own module + `__init__.py` |
| `DocumentChunkResponse` | `schemas/document.py` | Only in schema's own module + `__init__.py` |

**3. Unused dependencies:**
- `scrapling>=0.1` in `apps/worker/pyproject.toml` — listed but never imported. Comment in `web.py` line 9 confirms: *"scrapling already installed but not used here"*

**4. Redundant import:**
- `import re` in `apps/worker/worker/connectors/web.py` at line 18 is duplicated by inner `import re` at line 63 inside `_parse_year()`. The module-level import already covers it.

**5. `import re` in `project_service.py` line 5** — imported at module level but never used (the method `_append_copy_suffix` uses `import re as _re` inline at line 313 instead).

### No Commented-Out Code Found
Zero commented-out code blocks across the scanned files.

---

## 3. Celery Configuration

### Current State

There are **3 separate Celery app instances** with inconsistent config:

| Location | Config Source | Broker | Notes |
|----------|--------------|--------|-------|
| `worker/app.py` | **Hardcoded** `BROKER_URL = "redis://localhost:6379/0"` | Hardcoded | Ignores `settings.CELERY_BROKER_URL` entirely |
| `api/.../project_service.py` | `settings.CELERY_BROKER_URL` | From settings | References `settings.CELERY_BROKER_URL` |
| `api/.../analysis_service.py` | `settings.REDIS_URL` | From settings | References `settings.REDIS_URL` instead of `CELERY_BROKER_URL` |

### Issues

1. **Worker ignores settings entirely** — `BROKER_URL` and `RESULT_BACKEND` are hardcoded strings with a TODO comment saying they *should* be imported from settings but never were.

2. **Inconsistent settings keys** — `settings.py` has both:
   - `REDIS_URL` (line 28, general-purpose Redis)
   - `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (lines 57-58, Celery-specific)
   - `analysis_service.py` uses `REDIS_URL` while `project_service.py` uses `CELERY_BROKER_URL` — they happen to default to the same value but drift on config changes.

3. **Separate Celery app instances** — Each service creates its own `Celery("vigilagraph")` instance instead of sharing a common one.

4. **Redundant `include` path** — Worker `app.py` includes both `"worker.tasks"` and `"worker.tasks.collection_tasks"`, but `worker.tasks.__init__` already imports from `collection_tasks`. The explicit `collection_tasks` include is unnecessary.

### Affected Files
- `apps/worker/worker/app.py` — hardcoded broker/backend, redundant include
- `apps/api/app/services/project_service.py` — separate Celery instance
- `apps/api/app/services/analysis_service.py` — separate Celery instance, wrong settings key
- `apps/api/app/core/config.py` — has `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (three overlapping keys)

---

## 4. General Code Quality

### `_ensure_org()` vs `verify_project_org()` (from Change 5)

**Old pattern** (`_ensure_org` — returns 403, no project-boundary check):
- `corpus.py` — 4 routes
- `projects.py` — 15 routes
- `documents.py` — 7 routes
- `graph.py` — 9 routes (most routes; 2 already migrated)
- **Total: 35 call sites still using `_ensure_org`**

**New pattern** (`verify_project_org` — returns 404, verifies project belongs to user's org):
- `search.py` — 1 route
- `reports.py` — 5 routes
- `graph.py` — 2 routes (download-json, html)
- `analysis.py` — 5 routes
- **Total: 13 call sites using `verify_project_org`**

All 35 `_ensure_org` sites should be migrated to `verify_project_org`.

### Duplicated Type Maps

`NODE_TYPE_MAP` and `EDGE_TYPE_MAP` (40+ lines) are duplicated in two files:
- `apps/worker/worker/graphify/parser.py` (lines 10-44)
- `apps/api/app/services/graph_service.py` (lines 36-70)

Should live in `packages/shared/`.

### Deprecated `datetime.utcnow()`

Used in `corpus_service.py` lines 173 and 288:
```python
"last_rebuild_at": datetime.utcnow().isoformat()
```
Should be `datetime.now(UTC)` — the rest of the codebase consistently uses `datetime.now(UTC)`.

### Access to Private Method

`apps/api/app/api/v1/graph.py` lines 193 and 212 call `service._get_run(run_id)` (a method named with underscore convention). Should either be made public or accessed through a proper public method.

### Type Annotation Gaps

| File | Issue |
|------|-------|
| `report_service.py` | `docs: list` instead of `list[Document]` |
| `graphify/importer.py:28` | `run_id: Any` instead of `run_id: uuid.UUID` |
| `analysis_repository.py` | All 4 analysis repos use `self.db` instead of `self.session` (inconsistent with BaseRepository convention) |

### Import Style Inconsistency

`apps/worker/worker/tasks/collection_tasks.py` uses **lazy imports** inside if/elif branches:
```python
if run.source_name == "openalex":
    from worker.connectors.openalex import OpenAlexConnector
    connector = OpenAlexConnector()
```
These should be top-level imports for clarity and to surface import errors at startup.

### Inline `import json` / `import shutil` in `graph_service.py`

Lines 110 and 113 inside the `generate()` method re-import modules already imported at the top of the file (line 6 `import json`, line 7 `import shutil`). These are redundant.

---

## 5. Priority Summary

| # | Item | Effort | Priority | Category |
|---|------|--------|----------|----------|
| 1 | Migrate 5 non-BaseRepository repos to inherit from BaseRepository | 2-3h | **Critical** | Repository duplication |
| 2 | Replace 35 `_ensure_org` calls with `verify_project_org` | 1-2h | **High** | Pattern inconsistency |
| 3 | Celery worker: use `settings` instead of hardcoded URLs | 1h | **High** | Config |
| 4 | Consolidate Celery instances (worker/app.py logic into shared) | 2-3h | **High** | Architecture |
| 5 | Remove dead `GraphifyAdapter.run_sync()` | 0.5h | **Medium** | Dead code |
| 6 | Remove 5 unused schemas from `__init__.py` | 0.5h | **Medium** | Dead code |
| 7 | Deduplicate `NODE_TYPE_MAP`/`EDGE_TYPE_MAP` into shared package | 1h | **Medium** | Code quality |
| 8 | Remove unused `scrapling` dependency | 0.25h | **Low** | Dependency |
| 9 | Fix `import re` duplication in `web.py` | 0.25h | **Low** | Code quality |
| 10 | Remove unused `import re` in `project_service.py` | 0.1h | **Low** | Code quality |
| 11 | Replace `datetime.utcnow()` with `datetime.now(UTC)` in `corpus_service.py` | 0.25h | **Low** | Deprecation |
| 12 | Remove redundant inline imports in `graph_service.py` | 0.1h | **Low** | Code quality |
| 13 | Remove redundant Celery `include` in worker/app.py | 0.1h | **Low** | Config |
| 14 | Fix type annotations (report_service, importer) | 0.5h | **Low** | Type safety |
| 15 | Move lazy imports to top-level in `collection_tasks.py` | 0.5h | **Low** | Code quality |
| 16 | Add missing repository exports to `__init__.py` | 0.1h | **Low** | API completeness |
| 17 | Make `_get_run()` public or add public accessor in graph route | 0.25h | **Low** | Encapsulation |

### Estimated Total Effort: ~11-16 hours
### Priority Breakdown: 2 Critical | 2 High | 3 Medium | 10 Low
