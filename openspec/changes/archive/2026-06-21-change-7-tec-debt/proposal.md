# Proposal: Deuda Técnica Cleanup

## Intent

Eliminate ~160 lines of duplicated CRUD in 5 repos and 35 stale auth call sites
that risk security boundary leaks. Fix inconsistent Redis config between worker and
API. Pure refactor — zero behavior changes.

## Scope

### In Scope
1. **5 repos → BaseRepository**: Technology, Trend, Actor, Opportunity, Report. Add `__init__.py` exports.
2. **35 `_ensure_org` → `verify_project_org`**: corpus.py (4), projects.py (15), documents.py (7), graph.py (9).
3. **Worker Redis hardcode**: Replace `"redis://localhost:6379/0"` with `settings.CELERY_BROKER_URL`.
4. **Redis key mismatch**: `analysis_service.py` → `CELERY_BROKER_URL` (not `REDIS_URL`).

### Out of Scope
All Medium/Low items (dead code, type maps, deprecations, type annotations, import cleanup) — deferred.

## Capabilities

No spec-level behavior changes.

### New Capabilities
None

### Modified Capabilities
None

## Approach

Four independent, revertible work units:
1. **Repos**: Add `model_class`, delete duplicated CRUD, add `__all__` exports.
2. **Auth**: Mechanical replacement `_ensure_org(org_id, user_id)` → `verify_project_org(project_id, user)` per route.
3. **Worker**: Replace hardcoded strings with `settings` values.
4. **Redis key**: Single-line swap in `analysis_service.py`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `repositories/analysis_repository.py` | Modified | 4 repos inherit BaseRepository, drop duplicated methods |
| `repositories/report_repository.py` | Modified | Inherit BaseRepository, drop duplicated methods |
| `repositories/__init__.py` | Modified | Add missing exports |
| `api/v1/corpus.py` | Modified | 4 routes: `_ensure_org` → `verify_project_org` |
| `api/v1/projects.py` | Modified | 15 routes: `_ensure_org` → `verify_project_org` |
| `api/v1/documents.py` | Modified | 7 routes: `_ensure_org` → `verify_project_org` |
| `api/v1/graph.py` | Modified | 9 routes: `_ensure_org` → `verify_project_org` |
| `worker/app.py` | Modified | Use settings instead of hardcoded Redis URL |
| `services/analysis_service.py` | Modified | Use `CELERY_BROKER_URL` instead of `REDIS_URL` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| BaseRepo migration breaks analysis routes | Low | Each repo independently testable via existing callers |
| Auth boundary typo (403 vs 404 response) | Low | Mechanical replacement, easy to spot in review |
| Worker won't start if misconfigured | Low | Immediate startup crash, trivial to revert |
| Redis key divergence missed | Low | Single-line change, grep-verifiable |

## Rollback Plan

Each item independently revertible via `git checkout <file>` — no migrations, no
data changes, no schema modifications. All rollbacks are instant.

## Dependencies

None.

## Success Criteria

- [ ] All 5 repos inherit from `BaseRepository`; no duplicated CRUD methods remain
- [ ] `__init__.py` exports all 5 repos; import tests pass
- [ ] Zero `_ensure_org` calls remain in corpus.py, projects.py, documents.py, graph.py
- [ ] `worker/app.py` reads Redis URL from `settings.CELERY_BROKER_URL` (not hardcoded)
- [ ] `analysis_service.py` uses `settings.CELERY_BROKER_URL` (not `settings.REDIS_URL`)
- [ ] All existing tests pass
