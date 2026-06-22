# Especificación: Change 3 — Fuentes Externas (OpenAlex)

> Cubre las 4 capacidades del cambio. Español neutro profesional.

---

## 1. collection-runs (NUEVA)

### Requerimiento: Modelo CollectionRun

El sistema DEBE crear tabla `collection_runs` con: `id` (UUID PK), `project_id` (FK → surveillance_projects, CASCADE), `source_name` (String), `status` (pending|running|completed|failed), `started_at`, `finished_at`, `docs_found` (int), `docs_inserted` (int), `error_message` (Text nullable), `metadata_json` (JSONB nullable), `created_at`.

- Feliz: CollectionRun pending → running → completed, contadores poblados.
- Error: tarea falla → status=failed, error_message guarda traceback.
- Regla: docs_found puede ser > docs_inserted (duplicados filtrados).

### Requerimiento: Endpoints CollectionRun

`GET /projects/{id}/collection-runs` → lista paginada DESC. `POST /projects/{id}/collect` → 202 + CollectionRunResponse (crea run + encola Celery).

- Feliz: draft, con SearchStrategy + sources_selected incluye openalex → 202.
- Error: sin SearchStrategy → 422.
- Error: ya collecting → 409.
- Error: 404 si proyecto no existe.

### Requerimiento: Schema CollectionRunResponse

Campos: id, project_id, source_name, status, started_at, finished_at, docs_found, docs_inserted, error_message, created_at. `from_attributes=True`.

### Requerimiento: Tarea Celery collect_from_source

Lee SearchStrategy, construye queries, itera conector, dedup por `(source_name, source_id)` → DOI → checksum, batch insert, actualiza CollectionRun.

- Feliz: 50 works, 48 insertados (2 dups), completed.
- Edge: 0 works → completed con contadores 0.
- Edge: error red → tenacity retry, si persiste → failed.

---

## 2. openalex-connector (NUEVA)

### Requerimiento: BaseConnector ABC

Clase abstracta con `fetch(self, query: str) → AsyncGenerator[dict]`.

### Requerimiento: OpenAlexConnector

Implementa `fetch()` contra `/works?search={query}&cursor=*` con `httpx.AsyncClient`.

- Paginación: `meta.next_cursor`, iterar hasta null.
- Rate limit: 10 req/s con `asyncio.Semaphore`.
- Retry: `tenacity.retry(stop=3, wait=wait_exponential())`.
- Normalización: `source_name="openalex"`, `source_id`, `title`, `doi`, `abstract` (desde inverted_index), `authors`, `institutions`, `publication_year`, `language`, `url`.
- Feliz: 3 páginas → ~75 docs.
- Edge: 429 → retry+backoff, logged.
- Edge: cursor inválido → raise, logged.
- Regla: source_id = OpenAlex ID canónico (`https://openalex.org/W...`).

---

## 3. document-management (MODIFICADA)

### Requerimiento: Campo source_name en Document

`Document.source_name: str` default `"manual_upload"`, nullable=false. Enum `SourceName` en `app/models/enums.py` como `StrEnum`: `manual_upload`, `openalex`, `semantic_scholar`, `lens`, `web`.

- Feliz manual: source_name="manual_upload".
- Feliz OpenAlex: source_name="openalex".
- Migración: documentos existentes heredan "manual_upload".

### Requerimiento: Schema DocumentResponse

Agregar `source_name: str | None = None` (opcional, no rompe clientes).

### Requerimiento: Frontend tipos + badge

`api.ts`: agregar `source_name?: string` a `Document`. Tabla muestra badge con source cuando no es `manual_upload`.

### Requerimiento: Fix */strategy → */search-strategy

`use-projects.ts`: cambiar URLs de `/strategy` a `/search-strategy` (GET, PUT, POST). Backend siempre usó `/search-strategy`.

---

## 4. project-status-machine (MODIFICADA)

### Requerimiento: Hook transition → collecting

`transition_status` DETECTA `to_status="collecting"` y ejecuta side effects ANTES de escribir:

1. Validar `project.search_strategy` existe → si no, 422.
2. Validar `sources_selected` incluye "openalex" → si no, 422.
3. Crear `CollectionRun(project_id, source_name="openalex", status="pending")`.
4. Encolar `collect_from_source.delay(collection_run_id=str(run.id))`.

- Feliz: draft + search strategy + openalex → collecting, CollectionRun creado, tarea encolada.
- Error: sin SearchStrategy → 422, status NO cambia.
- Error: sources_selected sin openalex → 422, status NO cambia.
- Error: ya collecting en curso → 409.
- Regla: fallar rápido — validaciones antes de toda escritura.

### Requerimiento: Botón "Collect Now" (NUEVO, UI)

Overview (`page.tsx`) muestra botón "Collect Now" solo en status `draft`. Llama `POST /projects/{id}/collect`.

- Feliz: clic → loading → 202 → proyecto pasa a collecting.
- Edge: ya collecting → botón deshabilitado + tooltip.
- Edge: sin search strategy → botón deshabilitado + tooltip.
