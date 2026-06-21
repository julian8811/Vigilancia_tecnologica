# Tasks: Change 4 — Nuevos Conectores

## PR 1: Semantic Scholar Connector

- [x] 1.1 Crear `apps/worker/worker/connectors/semantic_scholar.py` con `SemanticScholarConnector`
- [x] 1.2 Modificar `collection_tasks.py` para rutear `source_name == "semantic_scholar"`
- [x] 1.3 Agregar `SEMANTIC_SCHOLAR_API_KEY` a Settings (`.env.example` bloqueado por reglas de permisos)
- [x] 1.4 Verificar sintaxis Python y linter

## PR 2: Lens.org Connector

- [x] 2.1 Crear `apps/worker/worker/connectors/lens.py` con `LensConnector`
- [x] 2.2 Modificar `collection_tasks.py` para rutear `source_name == "lens"`
- [x] 2.3 Agregar `LENS_API_TOKEN` a Settings (`.env.example` bloqueado)
- [x] 2.4 Verificar sintaxis Python y linter

## PR 3: Web Scraper + Frontend

- [x] 3.1 Agregar campo `scrape_urls` a modelo y schemas de SearchStrategy
- [x] 3.2 Crear migración Alembic `003_scrape_urls.py`
- [x] 3.3 Crear `apps/worker/worker/connectors/web.py` con `WebScraperConnector`
- [x] 3.4 Modificar `collection_tasks.py` para rutear `source_name == "web"`
- [x] 3.5 Actualizar `apps/web/types/api.ts` con `scrape_urls`
- [x] 3.6 Actualizar frontend para textarea de URLs cuando `web` esté seleccionado
- [x] 3.7 Verificar TypeScript y Python

---

**Review Workload Forecast**:
- Total estimado: ~650 líneas
- 400-line budget risk: High
- Chained PRs recommended: Yes
- Delivery strategy: force-chained (stacked-to-main)
- PR 1: ~180 líneas
- PR 2: ~220 líneas
- PR 3: ~250 líneas
