# Tasks: Change 3 — Integración de Fuentes Externas (OpenAlex)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~740 (253 + 325 + 160) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Data Layer) → PR 2 (Worker) → PR 3 (Trigger + Frontend) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Data Layer — modelos, schemas, migración, endpoint GET collection-runs | PR 1 | Base para todo lo demás. Independiente. |
| 2 | Worker — conectores y tarea Celery | PR 2 | Depende de PR 1 (modelos, DB). Base = main tras merge PR 1. |
| 3 | Trigger + Frontend — hook transition, botón Collect Now, badge source | PR 3 | Depende de PR 2 (tarea Celery). Base = main tras merge PR 2. |

---

## PR 1: Data Layer — Migración, Modelos, Schemas, GET CollectionRuns

- [x] **1.1** Crear `apps/api/app/models/enums.py` con `SourceName(StrEnum)`: `manual_upload`, `openalex`, `semantic_scholar`, `lens`, `web`.
- [x] **1.2** Crear `apps/api/app/models/collection_run.py` — modelo `CollectionRun` con todos los campos del diseño: id UUID PK, project_id FK, source_name, status, started_at, finished_at, docs_found, docs_inserted, error_message, metadata_json (JSONB), created_at, updated_at. Relación `project` back_populates.
- [x] **1.3** Modificar `apps/api/app/models/document.py`: agregar `source_name: Mapped[str] = mapped_column(String(50), server_default="manual_upload", nullable=False)`.
- [x] **1.4** Modificar `apps/api/app/models/project.py`: agregar `collection_runs: Mapped[list[CollectionRun]]` relationship back_populates. Actualizar `apps/api/app/models/__init__.py`: importar + exportar `CollectionRun` y `SourceName`.
- [x] **1.5** Crear `apps/api/app/schemas/collection_run.py` con `CollectionRunResponse` y `CollectionRunListResponse` (from_attributes=True). Modificar `apps/api/app/schemas/document.py`: agregar `source_name: str = "manual_upload"` a `DocumentResponse`. Actualizar `apps/api/app/schemas/__init__.py`.
- [x] **1.6** Crear migración Alembic `apps/api/alembic/versions/002_collection_runs.py`: add column `source_name` a `documents` (server_default="manual_upload"), índice compuesto `ix_documents_source_lookup` (project_id, source_name, source_id), crear tabla `collection_runs`. Downgrade: drop table, drop index, drop column.
- [x] **1.7** Crear `apps/api/app/repositories/collection_run_repository.py` — `CollectionRunRepository.list_by_project(project_id, page, page_size)`. Modificar `apps/api/app/api/v1/projects.py`: agregar `GET /projects/{id}/collection-runs` → 200 `CollectionRunListResponse` paginado DESC, org-scoped.

**ACs cubiertas (spec):** Modelo CollectionRun (feliz/error/regla), Schema CollectionRunResponse, Document.source_name manual_upload default, migración documentos existentes.

---

## PR 2: Worker — Conectores y Tarea Celery

- [x] **2.1** Crear `apps/worker/worker/connectors/base.py` — `BaseConnector(ABC)` con método abstracto `async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]: ...`.
  - Docstring completo con contrato de interfaz (rate limiting, error handling, schema de cada dict).
- [x] **2.2** Crear `apps/worker/worker/connectors/openalex.py` — `OpenAlexConnector(BaseConnector)`:
  - httpx.AsyncClient con timeout 30s.
  - Paginación cursor-based (`/works?search={query}&cursor=*&per_page=100`), itera hasta `meta.next_cursor = null`.
  - Rate limit 10 req/s vía `asyncio.Semaphore(10)` + `asyncio.sleep(0.1)` entre batches.
  - Retry con `tenacity.retry(stop=3, wait=wait_exponential(min=1, max=10))` — captura 429, 5xx.
  - Normalización de cada work: source_id (OpenAlex ID W...), title, doi, abstract (desde inverted_index), authors, institutions, publication_year, language, url (primary_location.landing_page_url), document_type="paper", source_name="openalex".
  - Logging de páginas, rate limits, errores.
- [x] **2.3** Crear `apps/worker/worker/tasks/collection_tasks.py` — `collect_from_source(self, run_id: str) -> dict` (AsyncTask, bind=True, name="collect_from_source"):
  - Reusa worker_engine y AsyncTask desde `graph_tasks.py` (mismo patrón).
  - Marca CollectionRun → status=running, started_at=now.
  - Lee SearchStrategy del proyecto (keywords_en, keywords_es, boolean_queries, sources_selected).
  - Construye query combinada para OpenAlex (prioridad: boolean_queries > keywords).
  - Valida que `run.source_name` esté en `sources_selected`.
  - Instancia `OpenAlexConnector`, itera `fetch()`.
  - Dedup pipeline in-memory: pre-carga todos los documentos del proyecto, chequea `(source_name, source_id)` → DOI → checksum.
  - Batch insert cada 50 docs (acumula en lista, `session.add_all()`, flush).
  - Mantiene tracking en memoria de cada doc insertado (misma run no se duplica).
  - Respeta límite de 500 works por CollectionRun.
  - Al completar: status=completed, docs_found=N, docs_inserted=M, finished_at=now, metadata_json con query + source + límite.
  - Si error: status=failed, error_message=str(exc)[:2000].
  - Actualizar `apps/worker/worker/tasks/__init__.py`: importar `collect_from_source`.
  - Actualizar `apps/worker/worker/app.py`: agregar `"worker.tasks.collection_tasks"` al include.

**ACs cubiertas (spec):** BaseConnector ABC, OpenAlexConnector paginación/rate limit/retry/normalización, Tarea collect_from_source feliz/0-works/error-red, Dedup pipeline, Límite 500 works.

---

## PR 3: Trigger + Frontend — Hook, UI, Tipos

- [x] **3.1** Modificar `apps/api/app/services/project_service.py`:
  - En `transition_status()`: detectar `to_status == "collecting"` ANTES de escribir.
    - Validar que `project.search_strategy` no sea None → 422 "SearchStrategy required".
    - Validar que `project.search_strategy.sources_selected` contenga "openalex" → 422 "Source 'openalex' not selected".
    - Validar que no exista un CollectionRun en estado running para este proyecto → 409 "Collection already in progress".
    - Crear `CollectionRun(project_id=project.id, source_name="openalex", status="pending")`.
    - Encolar `collect_from_source.delay(str(collection_run.id))`.
    - Luego continuar con escritura del status.
  - Usar `celery_app.send_task(...)` (patrón sin importar la tarea directamente).
- [x] **3.2** Modificar `apps/api/app/api/v1/projects.py`: arreglar `transition_project_status` para leer `status` del body JSON (no query param). Agregar `StatusTransitionRequest` schema.
- [x] **3.3** Modificar `apps/web/types/api.ts`:
  - Agregar `CollectionRun` interface (id, project_id, source_name, status, started_at?, finished_at?, docs_found?, docs_inserted?, error_message?, created_at).
  - Agregar `source_name?: string` a `Document`.
  - Agregar `ProjectStatus` incluir `"failed"`.
  - Agregar `CollectionRunListResponse`.
- [x] **3.4** Crear `apps/web/hooks/use-collection.ts` — `useCollectionRuns(projectId: string)`, `useTriggerCollection()`, `useLatestCollectionRuns(projectId)`.
- [x] **3.5** Modificar `apps/web/hooks/use-projects.ts`: corregir URLs de `/strategy` a `/search-strategy` en `useSearchStrategy`, `useUpdateSearchStrategy`, `useGenerateSearchStrategy`.
- [x] **3.6** Modificar `apps/web/app/projects/[id]/page.tsx`:
  - Agregar botón "Collect Now" en sección de quick actions (card).
  - Solo visible cuando `project.status === "draft"`.
  - Llamar `useTriggerCollection` con `projectId`.
  - Loading state mientras la transición está en curso.
  - Muestra últimas 3 collection runs con badges de status y contadores.
  - Refrescar proyecto y colecciones luego de la transición.
- [x] **3.7** Modificar `apps/web/app/projects/[id]/documents/page.tsx`:
  - Agregar columna "Source" en la tabla de documentos.
  - `SourceBadge` componente: muestra "Manual" si source_name es "manual_upload" o undefined, badge con color para "openalex".

**ACs cubiertas (spec):** Hook transition → collecting (feliz/sin-strategy/sin-openalex/ya-collecting), StatusTransitionRequest fix, Botón Collect Now (feliz/disabled), Badge source, Fix URL strategy.

---

## Resumen de Archivos

| Archivo | Acción | PR |
|---------|--------|----|
| `apps/api/app/models/enums.py` | **Crear** | PR 1 |
| `apps/api/app/models/collection_run.py` | **Crear** | PR 1 |
| `apps/api/app/models/document.py` | Modificar | PR 1 |
| `apps/api/app/models/project.py` | Modificar | PR 1 |
| `apps/api/app/models/__init__.py` | Modificar | PR 1 |
| `apps/api/app/schemas/collection_run.py` | **Crear** | PR 1 |
| `apps/api/app/schemas/document.py` | Modificar | PR 1 |
| `apps/api/app/schemas/__init__.py` | Modificar | PR 1 |
| `apps/api/alembic/versions/002_collection_runs.py` | **Crear** | PR 1 |
| `apps/api/app/repositories/collection_run_repository.py` | **Crear** | PR 3 (deferred from PR 1) |
| `apps/api/app/api/v1/projects.py` | Modificar | PR 1, PR 3 |
| `apps/api/app/api/v1/router.py` | — | No changes needed (endpoint added to existing projects router) |
| `apps/worker/worker/connectors/base.py` | **Crear** | PR 2 |
| `apps/worker/worker/connectors/openalex.py` | **Crear** | PR 2 |
| `apps/worker/worker/tasks/collection_tasks.py` | **Crear** | PR 2 |
| `apps/worker/worker/tasks/__init__.py` | Modificar | PR 2 |
| `apps/worker/worker/app.py` | Modificar | PR 2 |
| `apps/api/app/services/project_service.py` | Modificar | PR 3 |
| `apps/web/types/api.ts` | Modificar | PR 3 |
| `apps/web/hooks/use-collection.ts` | **Crear** | PR 3 |
| `apps/web/hooks/use-projects.ts` | Modificar | PR 3 |
| `apps/web/app/projects/[id]/page.tsx` | Modificar | PR 3 |
| `apps/web/app/projects/[id]/documents/page.tsx` | Modificar | PR 3 |
