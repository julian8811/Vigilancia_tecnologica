# Tasks: Deuda Técnica Cleanup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~260 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | 5 repos → BaseRepository | PR 1 | ~210 lines, independent |
| 2 | `_ensure_org` → `verify_project_org` | PR 1 | ~40 lines, independent |
| 3 | Worker Redis config | PR 1 | ~5 lines, independent |
| 4 | Unify Redis keys | PR 1 | ~5 lines, independent |

## Phase 1: Repository Inheritance

- [x] 1.1 Add `model_class` to TechnologyRepository, TrendRepository, ActorRepository, OpportunityRepository, ReportRepository
- [x] 1.2 Delete duplicated CRUD (get, create, update, delete, list_by_project) from each of the 5 repos
- [x] 1.3 Add missing repo exports to `repositories/__init__.py`
- [x] 1.4 Run repo tests — verify all 5 repos work with BaseRepository

## Phase 2: Auth Boundary Migration

- [x] 2.1 Replace `_ensure_org` with `verify_project_org` in `corpus.py` (4 call sites)
- [x] 2.2 Replace `_ensure_org` with `verify_project_org` in `projects.py` (15 call sites)
- [x] 2.3 Replace `_ensure_org` with `verify_project_org` in `documents.py` (7 call sites)
- [x] 2.4 Replace `_ensure_org` with `verify_project_org` in `graph.py` (9 call sites)
- [x] 2.5 Run auth route tests — verify 403→404 response change doesn't break routes

## Phase 3: Redis Configuration

- [x] 3.1 Swap hardcoded `"redis://localhost:6379/0"` for `settings.CELERY_BROKER_URL` in `worker/app.py`
- [x] 3.2 Remove redundant `"worker.tasks.collection_tasks"` include from worker config
- [x] 3.3 Replace `settings.REDIS_URL` with `settings.CELERY_BROKER_URL` in `services/analysis_service.py`
- [x] 3.4 Consolidate duplicate Redis connection keys in `settings.py` if applicable

## Phase 4: Verification

- [x] 4.1 Run full test suite — confirm zero regressions
- [x] 4.2 Grep for `_ensure_org` across corpus.py, projects.py, documents.py, graph.py — confirm zero hits
- [x] 4.3 Verify worker starts cleanly with settings-based Redis URL
