# Archive Report: Change 4 — Nuevos Conectores

**Status**: archived
**Date**: 2026-06-20

## Summary
Added three new external source connectors to VigilaGraph IA:
1. **Semantic Scholar** — free academic paper API with optional API key
2. **Lens.org** — scholarly search API with Bearer token auth
3. **Web Scraping** — URL-based content extraction using trafilatura

## PRs
- PR 1: Semantic Scholar connector + routing
- PR 2: Lens.org connector + config
- PR 3: Web scraper + SearchStrategy.scrape_urls + frontend textarea

## Artifacts
- `openspec/changes/change-4-new-connectors/proposal.md`
- `openspec/changes/change-4-new-connectors/spec.md`
- `openspec/changes/change-4-new-connectors/design.md`
- `openspec/changes/change-4-new-connectors/tasks.md`
- `openspec/changes/change-4-new-connectors/verify-report.md`

## Next Steps
- Run the application locally to validate the full flow
- Test connectors against live APIs
- Add automated tests when testing infrastructure is available
