# Archive Report: Change 3 — External Sources (OpenAlex)

**Status**: **archived**
**Archived at**: 2026-06-19
**Artifact store**: hybrid (openspec + engram)

## What Was Built

Change 3 implemented external source collection via OpenAlex API. 17 tasks across 3 stacked PRs, ~740 lines total.

### Data Layer (PR 1)
- `SourceName` enum (`manual_upload`, `openalex`, `semantic_scholar`, `lens`, `web`)
- `CollectionRun` model + Pydantic schemas + Alembic migration (002)
- `source_name` column on `Document` with `server_default="manual_upload"`
- `GET /projects/{id}/collection-runs` paginated endpoint
- `CollectionRunRepository.list_by_project()`

### Worker Layer (PR 2)
- `BaseConnector` ABC with async `fetch()` contract
- `OpenAlexConnector` with: httpx.AsyncClient, cursor-based pagination (`/works?search=...&cursor=*`), `asyncio.Semaphore(10)` rate limiting, `tenacity` retry (3 attempts, exponential backoff), abstract reconstruction from inverted_index, full field normalization
- Celery `collect_from_source` task with: 3-level dedup pipeline (`(source_name, source_id)` → DOI → checksum), batch insert (50), 500-work limit, lifecycle tracking on CollectionRun

### Trigger + Frontend (PR 3)
- Status machine hook: `transition_status` intercepts `to_status="collecting"`, validates SearchStrategy + sources_selected, creates CollectionRun, enqueues Celery task
- `POST /projects/{id}/status` reads status from JSON body (fixed from query param)
- `use-collection` hooks: `useCollectionRuns`, `useTriggerCollection`, `useLatestCollectionRuns`
- Collect Now button (visible in draft status)
- Source badges in documents table (Manual vs openalex)
- Fix frontend URLs: `/strategy` → `/search-strategy`

## Files Touched

23 files total:

| File | Action |
|------|--------|
| `apps/api/app/models/enums.py` | **Created** |
| `apps/api/app/models/collection_run.py` | **Created** |
| `apps/api/app/models/document.py` | Modified |
| `apps/api/app/models/project.py` | Modified |
| `apps/api/app/models/__init__.py` | Modified |
| `apps/api/app/schemas/collection_run.py` | **Created** |
| `apps/api/app/schemas/document.py` | Modified |
| `apps/api/app/schemas/__init__.py` | Modified |
| `apps/api/alembic/versions/002_collection_runs.py` | **Created** |
| `apps/api/app/repositories/collection_run_repository.py` | **Created** |
| `apps/api/app/services/project_service.py` | Modified |
| `apps/api/app/api/v1/projects.py` | Modified |
| `apps/worker/worker/connectors/base.py` | **Created** |
| `apps/worker/worker/connectors/openalex.py` | **Created** |
| `apps/worker/worker/tasks/collection_tasks.py` | **Created** |
| `apps/worker/worker/tasks/__init__.py` | Modified |
| `apps/worker/worker/app.py` | Modified |
| `apps/web/types/api.ts` | Modified |
| `apps/web/hooks/use-collection.ts` | **Created** |
| `apps/web/hooks/use-projects.ts` | Modified |
| `apps/web/app/projects/[id]/page.tsx` | Modified |
| `apps/web/app/projects/[id]/documents/page.tsx` | Modified |

## Engram Observation Lineage

| Artifact | Observation ID | Topic Key |
|----------|---------------|-----------|
| Exploration | #705 | `sdd/change-3/explore` |
| Proposal | (filesystem only — no engram artifact persisted) | — |
| Spec | (filesystem only — no engram artifact persisted) | — |
| Design | #709 | `sdd/External Sources (OpenAlex)/design` |
| Tasks | #711 (updated at archive) | `sdd/External Sources (OpenAlex)/tasks` |
| Apply-Progress | #712 | `sdd/External Sources (OpenAlex)/apply-progress` |
| Verify-Report | #714 | `sdd/External Sources (OpenAlex)/verify-report` |
| Archive-Report | (this observation) | `sdd/External Sources (OpenAlex)/archive-report` |

Note: Proposal and Spec artifacts exist only on filesystem (`openspec/changes/archive/2026-06-19-change-3-external-sources/`) but were not persisted to engram as separate observations during their respective phases.

## Stale Checkbox Reconciliation

The engram tasks observation (#711) contained unchecked implementation tasks from an earlier revision. The filesystem `tasks.md` already had all 17 tasks marked `[x]`, and both `apply-progress` (#712) and `verify-report` (#714) confirm 17/17 tasks complete. The orchestrator explicitly instructed archive-time reconciliation ("Update `tasks.md` to mark ALL tasks as `[x]`"). The engram observation was updated at archive time to reflect the final completed state.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| collection-runs | Created | 4 requirements — CollectionRun model, endpoints, schemas, Celery task |
| openalex-connector | Created | 2 requirements — BaseConnector ABC, OpenAlexConnector |
| document-management | Created | 4 requirements — source_name field, schema, frontend types, /strategy fix |
| project-status-machine | Created | 2 requirements — collecting hook, Collect Now button |

## Open Items (Non-Blocking)

1. **CRITICAL**: Missing `DateTime` import in `apps/api/app/models/collection_run.py` — will crash on model import at runtime. Pre-existing systemic issue (same bug in `organization.py`, `document.py`, `project.py`). Fix: add `DateTime` to the SQLAlchemy import.
2. **Zero test coverage**: No unit, integration, or E2E tests for any of the 17 tasks.
3. **Minor**: Unused `SearchStrategyRepository` import in `project_service.py`.
4. **Minor**: Collection run completed status badge reuses `graph_ready` variant (semantically confusing).
5. **Minor**: `source_name` uses `String(50)` without DB-level enum validation.
6. **Minor**: `metadata_json` missing DB-level `server_default` in migration (JSONB default only at ORM level).

## Next Recommended Action

Fix the `DateTime` import in `collection_run.py` (the CRITICAL bug) before deploying. Then consider adding test coverage for the core scenarios: `SourceName` enum, `_normalize_work()`, dedup logic, and the status transition hook with mocked Celery.
