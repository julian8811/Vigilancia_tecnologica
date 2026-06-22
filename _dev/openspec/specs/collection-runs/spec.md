# Especificación: Collection Runs

> Tracking de ejecuciones de recolección desde fuentes externas, con estado, contadores y errores.

---

## Requerimiento: Modelo CollectionRun

El sistema DEBE crear tabla `collection_runs` con: `id` (UUID PK), `project_id` (FK → surveillance_projects, CASCADE), `source_name` (String), `status` (pending|running|completed|failed), `started_at`, `finished_at`, `docs_found` (int), `docs_inserted` (int), `error_message` (Text nullable), `metadata_json` (JSONB nullable), `created_at`.

- Feliz: CollectionRun pending → running → completed, contadores poblados.
- Error: tarea falla → status=failed, error_message guarda traceback.
- Regla: docs_found puede ser > docs_inserted (duplicados filtrados).

## Requerimiento: Endpoints CollectionRun

`GET /projects/{id}/collection-runs` → lista paginada DESC. `POST /projects/{id}/collect` → 202 + CollectionRunResponse (crea run + encola Celery).

- Feliz: draft, con SearchStrategy + sources_selected incluye openalex → 202.
- Error: sin SearchStrategy → 422.
- Error: ya collecting → 409.
- Error: 404 si proyecto no existe.

## Requerimiento: Schema CollectionRunResponse

Campos: id, project_id, source_name, status, started_at, finished_at, docs_found, docs_inserted, error_message, created_at. `from_attributes=True`.

## Requerimiento: Tarea Celery collect_from_source

Lee SearchStrategy, construye queries, itera conector, dedup por `(source_name, source_id)` → DOI → checksum, batch insert, actualiza CollectionRun.

- Feliz: 50 works, 48 insertados (2 dups), completed.
- Edge: 0 works → completed con contadores 0.
- Edge: error red → tenacity retry, si persiste → failed.
