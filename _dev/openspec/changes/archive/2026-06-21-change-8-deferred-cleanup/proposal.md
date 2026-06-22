# Proposal: Deferred Cleanup (Change 7 leftovers)

## Intent

Clean up Medium/Low technical debt deferred from Change 7 — dead code, unused schemas, duplicated constants, unused dependency, and minor code quality fixes. Pure refactor, no behavior changes.

## Scope

### In Scope
- Remove `GraphifyAdapter.run_sync()` (~60 lines dead code)
- Remove 5 unused schemas from `__init__.py` exports
- Extract duplicated `NODE_TYPE_MAP`/`EDGE_TYPE_MAP` to `packages/shared/`
- Remove unused `scrapling` dependency
- Fix duplicate/unused imports (web.py, project_service.py, graph_service.py)
- Replace deprecated `datetime.utcnow()` with `datetime.now(UTC)`
- Move lazy connector imports to top-level in collection_tasks.py
- Fix `service._get_run()` private method call in graph.py

### Out of Scope
- Behavior changes, new features, test additions

## Capabilities

- New Capabilities: None
- Modified Capabilities: None

## Approach

Ten independent mechanical changes. Each is a single-file edit with zero risk. No migrations, no schema changes, no API contract changes.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/worker/worker/graphify/` | Modified | Remove `run_sync()` |
| `apps/api/app/schemas/__init__.py` | Modified | Remove 5 unused exports |
| `packages/shared/` | Created | Extracted type maps |
| `apps/worker/worker/graphify/parser.py` | Modified | Import type maps from shared |
| `apps/api/app/services/graph_service.py` | Modified | Import type maps from shared |
| `apps/worker/pyproject.toml` | Modified | Remove scrapling |
| `apps/worker/worker/connectors/web.py` | Modified | Deduplicate `import re` |
| `apps/api/app/services/project_service.py` | Modified | Remove unused import |
| `apps/api/app/services/corpus_service.py` | Modified | Replace `utcnow()` |
| `apps/worker/worker/tasks/collection_tasks.py` | Modified | Top-level imports |
| `apps/api/app/api/v1/graph.py` | Modified | Public method call |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Type map import breaks existing code | Low | Both imports from shared; test suites confirm |
| Private→public method missing | Low | Check `GraphService` for public alias first |

## Rollback Plan

Each change is a single `git checkout <file>` away.

## Success Criteria

- [ ] All 44 tests still pass (API 28 + worker 16)
- [ ] `grep -rn "run_sync"` returns 0 hits
- [ ] `grep -rn "scrapling"` returns 0 hits
- [ ] `grep -rn "utcnow"` returns 0 hits
- [ ] `_get_run` no longer called from routes
