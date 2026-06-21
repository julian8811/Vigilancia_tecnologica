# Verification Report

**Change**: Change 3 — External Sources (OpenAlex)
**Version**: Spec topic `sdd/External Sources (OpenAlex)/spec` (obs #708)
**Mode**: Standard (no Strict TDD active)

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 17 (1.1–1.7, 2.1–2.3, 3.1–3.7) |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

All 17 tasks are implemented across 3 PRs, confirmed by both file inspection and git history.

---

## Build & Tests Execution

**Build (TypeScript)**: ✅ Passed
```
$ npx tsc --noEmit
EXIT: 0
```

**Linter (ruff)**: ⚠️ 6 warnings/errors in Change 3 files
```
$ ruff check app/models/collection_run.py app/models/enums.py ...
  → 4 × F821 (DateTime undefined) in collection_run.py
  → 1 × F821 (SurveillanceProject forward-ref flagged — false positive)
  → 1 × F401 (unused import SearchStrategyRepository in project_service.py)
```

**Tests**: ➖ No tests exist for Change 3
```
$ pytest app/tests/
  → no tests ran
The `app/tests/` directory only contains `__init__.py`.
```

**Coverage**: ➖ Not available (no test infrastructure for this change)

---

## Spec Compliance Matrix

| # | Requirement | Scenario | Test | Result |
|---|-------------|----------|------|--------|
| R1 | CollectionRun model | Happy: pending→running→completed | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R2 | CollectionRun model | Error: task fails→failed+error_message | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R3 | CollectionRun model | Rule: docs_found ≥ docs_inserted | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R4 | GET /projects/{id}/collection-runs | Happy: paginated DESC list | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R5 | POST trigger collection | Happy: draft + SearchStrategy → 202 | (none) | ⚠️ IMPLEMENTED (via status hook), UNTESTED |
| R6 | POST trigger collection | Error: no SearchStrategy → 422 | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R7 | POST trigger collection | Error: already collecting → 409 | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R8 | POST trigger collection | Error: project not found → 404 | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R9 | CollectionRunResponse schema | from_attributes=True, all fields | (none) | ✅ IMPLEMENTED |
| R10 | Celery task | Happy: 50 works, 48 inserted | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R11 | Celery task | Edge: 0 works → completed with 0 | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R12 | Celery task | Edge: network error → tenacity retry → failed | (none) | ⚠️ IMPLEMENTED, UNTESTED |
| R13 | BaseConnector ABC | Abstract fetch method | (none) | ✅ IMPLEMENTED |
| R14 | OpenAlexConnector | Pagination via cursor | (none) | ✅ IMPLEMENTED |
| R15 | OpenAlexConnector | Rate limit 10 req/s Semaphore | (none) | ✅ IMPLEMENTED |
| R16 | OpenAlexConnector | tenacity retry (3 attempts, exponential backoff) | (none) | ✅ IMPLEMENTED |
| R17 | OpenAlexConnector | Abstract reconstruction from inverted_index | (none) | ✅ IMPLEMENTED |
| R18 | OpenAlexConnector | Field normalization (source_id, title, doi, etc.) | (none) | ✅ IMPLEMENTED |
| R19 | source_name on Document | String(50), server_default="manual_upload" | (none) | ✅ IMPLEMENTED |
| R20 | SourceName enum | 5 values (manual_upload, openalex, semantic_scholar, lens, web) | (none) | ✅ IMPLEMENTED |
| R21 | DocumentResponse schema | source_name field added | (none) | ✅ IMPLEMENTED |
| R22 | Frontend Document type | source_name?: string | (none) | ✅ IMPLEMENTED |
| R23 | Frontend Source badge | Shows in table, differentiates manual_upload vs openalex | (none) | ✅ IMPLEMENTED |
| R24 | Status body fix | Reads status from JSON body, not query param | (none) | ✅ IMPLEMENTED |
| R25 | Fix /strategy→/search-strategy | All 3 URLs in use-projects.ts | (none) | ✅ IMPLEMENTED |
| R26 | Collect Now button | Only visible in draft status | (none) | ✅ IMPLEMENTED |
| R27 | Migration 002 | add source_name, collection_runs table, index | (none) | ✅ IMPLEMENTED |

**Compliance summary**: 21/27 scenarios implemented but UNTESTED; 6/27 fully compliant with no test gap; 1 CRITICAL bug (missing import).

---

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| **CollectionRun model** | ✅ Implemented | UUID PK, FK→projects (CASCADE), source_name, status, timestamps, counters, error_message, metadata_json, created_at. ❌ Missing `DateTime` import (see CRITICAL). |
| **source_name on Document** | ✅ Implemented | `String(50), server_default="manual_upload", nullable=False` — matches spec exactly. |
| **SourceName enum** | ✅ Implemented | 5 values: manual_upload, openalex, semantic_scholar, lens, web — matches spec. |
| **BaseConnector ABC** | ✅ Implemented | Abstract `fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]`. |
| **OpenAlexConnector** | ✅ Implemented | httpx.AsyncClient, Semaphore(10) rate limit, tenacity retry (3×, exp backoff), cursor pagination, abstract inverted_index reconstruction, field normalization. |
| **Celery task** | ✅ Implemented | Reads CollectionRun→project→SearchStrategy, builds query, dedup pipeline (source_key→DOI→checksum), batch insert (50), lifecycle counters. Takes `run_id` only (resolves project via CollectionRun). |
| **Status hook (transition → collecting)** | ✅ Implemented | Validates SearchStrategy exists, sources_selected includes "openalex", no active run (→409), creates CollectionRun, enqueues Celery task. 422 on missing strategy/source, 409 on active run, 404 on missing project. |
| **Status body fix** | ✅ Implemented | `POST /projects/{id}/status` reads `status` from `StatusTransitionRequest` JSON body, not query param. |
| **GET /projects/{id}/collection-runs** | ✅ Implemented | Paginated (page/page_size), `created_at DESC` ordering. |
| **Frontend CollectionRun types** | ✅ Implemented | `CollectionRun` interface with all fields + `CollectionRunListResponse`. |
| **Frontend source_name on Document** | ✅ Implemented | `source_name?: string` added to `Document` interface. |
| **use-collection hooks** | ✅ Implemented | `useCollectionRuns(projectId)`, `useTriggerCollection()`, `useLatestCollectionRuns(projectId)`. |
| **Fix /strategy→/search-strategy** | ✅ Implemented | 0 occurrences of `/strategy` (without prefix), 3 occurrences of `/search-strategy` — GET, PUT, POST all fixed. |
| **Collect Now button** | ✅ Implemented | Only renders when `project.status === "draft"`. Loading state on trigger. Uses `useTransitionStatus`. |
| **Source badge** | ✅ Implemented | `SourceBadge` component: shows "Manual" for manual_upload/null, colored badge for openalex. "Source" column in documents table. |
| **Migration 002** | ✅ Implemented | Adds `source_name` to documents (String(50), server_default), creates `ix_documents_source_lookup` index (project_id, source_name, source_id), creates `collection_runs` table with all columns. Downgrade reverses all. |

---

## Coherence (Design)

| Design Decision | Followed? | Notes |
|----------------|-----------|-------|
| Hook in `transition_status` instead of separate endpoint | ✅ Yes | `transition_status()` in `project_service.py` intercepts `to_status="collecting"`. |
| `source_name` as direct column on Document | ✅ Yes | Direct column, no join table. |
| Dedup by `(source_name, source_id)` → DOI → checksum | ✅ Yes | Three-level dedup pipeline in `collect_from_source`. |
| Worker uses `AsyncTask` pattern + own engine | ✅ Yes | Reuses `worker_session_factory` and `AsyncTask` from `graph_tasks.py`. |
| No `CollectionRun` on `ProjectResponse` | ✅ Yes | Separate endpoint `GET /projects/{id}/collection-runs`. |
| Semi-rate-limit by `asyncio.Semaphore(10)` + `asyncio.sleep(0.1)` | ✅ Yes | Correct implementation in `OpenAlexConnector.__init__` and `fetch`. |
| **Design**: task signature `(project_id, run_id)` | ⚠️ Deviated | Actual signature is `(run_id,)` — project resolved via CollectionRun FK. Arguably better design. |
| **Design**: `source_name` as `String(20)` on CollectionRun | ⚠️ Deviated | Actual uses `String(50)`. No functional impact; more future-proof. |
| **Spec**: `POST /projects/{id}/collect` endpoint | ⚠️ Deviated | Actual uses `POST /projects/{id}/status` with `{"status": "collecting"}` via status transition hook. This was an explicit design choice documented in the design doc. |

---

## Issues Found

### CRITICAL

1. **Missing `DateTime` import in `collection_run.py`**
   - File: `apps/api/app/models/collection_run.py` lines 38–61
   - The file imports `from sqlalchemy import ForeignKey, Integer, String, Text, func` but uses `DateTime(timezone=True)` on lines 39, 42, 58, 61 without importing `DateTime`.
   - This causes a `NameError: name 'DateTime' is not defined` at runtime when the model module is loaded.
   - While this bug also exists in pre-existing files (`organization.py`, `document.py`, `project.py`), the new `collection_run.py` perpetuates it.
   - **Fix**: Add `DateTime` to the import on line 8: `from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func`.

2. **No test coverage**
   - File: `apps/api/app/tests/` (empty directory)
   - Zero tests exist for any of the 17 implemented tasks. No unit tests for the OpenAlex connector, no integration tests for the Celery task, no E2E tests for the frontend.
   - Every spec scenario is UNTESTED.
   - **Recommendation**: At minimum, add unit tests for `SourceName` enum, `_normalize_work()`, `reconstruct_abstract()`, and `_compute_checksum()`. Add integration test for the status transition hook with mocked Celery.

### WARNING

1. **Unused import `SearchStrategyRepository` in `project_service.py`**
   - File: `apps/api/app/services/project_service.py` line 19
   - Imported but never used. Pre-existing issue in the codebase.

2. **Spec: `POST /projects/{id}/collect` not implemented as standalone endpoint**
   - The spec calls for a dedicated `POST /projects/{id}/collect` endpoint returning `202 + CollectionRunResponse`.
   - Actual implementation uses the status transition `POST /projects/{id}/status` with body `{"status": "collecting"}`, which also works but returns `ProjectResponse` instead of `CollectionRunResponse`.
   - This is an explicit design decision documented in the design doc ("Hook en transition_status en vez de endpoint separado"), so it's intentional, but differs from the spec's API contract.

3. **Missing `updated_at` in spec/design for CollectionRun**
   - The model has `updated_at` with `onupdate=func.now()` but neither the spec nor design mention it. This is actually an improvement (consistency with other models), but undocumented.

4. **Status badge uses `graph_ready` variant for `completed` runs**
   - File: `apps/web/app/projects/[id]/page.tsx` line 239
   - `run.status === "completed"` maps to `"graph_ready"` badge variant. This reuses an existing variant name in a semantically confusing way — a collection run being "completed" shouldn't share styling with the "graph_ready" project status. Works visually but is misleading.

### SUGGESTION

1. **Add source_name validation using SourceName enum**
   - The `CollectionRun.source_name` field is `String(50)` with no validation against the `SourceName` enum. Consider using `Enum(SourceName)` or adding a check constraint.

2. **Consider renaming status badge variant for collection runs**
   - Instead of reusing `"graph_ready"` variant for completed collection runs, use a distinct variant like `"success"` or `"completed"`.

3. **Consider adding DB-level default for `metadata_json` in migration**
   - The migration uses `default=dict` (ORM-level), but JSONB columns benefit from `server_default=sa.text("'{}'::jsonb")` for DB-level defaults. No functional impact since the column is nullable.

---

## Files Verified

| File | Status | Notes |
|------|--------|-------|
| `apps/api/app/models/enums.py` | ✅ | SourceName with 5 values |
| `apps/api/app/models/collection_run.py` | ❌ | Missing DateTime import (CRITICAL) |
| `apps/api/app/models/document.py` | ✅ | +source_name column |
| `apps/api/app/models/project.py` | ✅ | +collection_runs relationship |
| `apps/api/app/models/__init__.py` | ✅ | Exports CollectionRun, SourceName |
| `apps/api/app/schemas/collection_run.py` | ✅ | CollectionRunResponse + ListResponse |
| `apps/api/app/schemas/document.py` | ✅ | +source_name in DocumentResponse |
| `apps/api/app/schemas/__init__.py` | ✅ | Exports collection run schemas |
| `apps/api/alembic/versions/002_collection_runs.py` | ✅ | Migration with add column, index, table |
| `apps/api/app/repositories/collection_run_repository.py` | ✅ | list_by_project with pagination, DESC |
| `apps/api/app/services/project_service.py` | ✅ | Status hook with validations + Celery enqueue |
| `apps/api/app/api/v1/projects.py` | ✅ | GET collection-runs + StatusTransitionRequest body |
| `apps/api/app/api/v1/router.py` | ✅ | Projects router included (no change needed) |
| `apps/worker/worker/connectors/base.py` | ✅ | BaseConnector ABC |
| `apps/worker/worker/connectors/openalex.py` | ✅ | httpx, Semaphore, tenacity, pagination, normalization |
| `apps/worker/worker/tasks/collection_tasks.py` | ✅ | collect_from_source with dedup pipeline |
| `apps/worker/worker/tasks/__init__.py` | ✅ | Exports collect_from_source |
| `apps/worker/worker/app.py` | ✅ | Includes collection_tasks in Celery |
| `apps/web/types/api.ts` | ✅ | CollectionRun interface, +source_name on Document |
| `apps/web/hooks/use-collection.ts` | ✅ | useCollectionRuns, useTriggerCollection |
| `apps/web/hooks/use-projects.ts` | ✅ | /search-strategy URLs (3/3 fixed) |
| `apps/web/app/projects/[id]/page.tsx` | ✅ | Collect Now button in draft |
| `apps/web/app/projects/[id]/documents/page.tsx` | ✅ | SourceBadge component + Source column |

---

## Verdict

**FAIL**

The implementation is structurally complete — all 17 tasks, all 23 files are present and mostly correct. The TypeScript compiles cleanly, the Python syntax is valid, and the architecture follows the design decisions faithfully.

However, the **CRITICAL bug** in `collection_run.py` (missing `DateTime` import) means the CollectionRun model will crash on import at runtime. This is a blocking issue that prevents the entire feature from functioning. Combined with **zero test coverage** for any of the 27 spec scenarios, this implementation cannot be considered production-ready.

**To reach PASS**: Fix the `DateTime` import in `collection_run.py` and add basic coverage for the core scenarios (enum values, abstract reconstruction, dedup logic, status hook with mocked Celery).
