# Propuesta: Change 3 — Integración de Fuentes Externas (OpenAlex)

## Intención

Habilitar la recolección automática de documentos desde fuentes externas, empezando por OpenAlex (gratuito, sin API key, 100k req/día). Hoy los proyectos solo aceptan documentos por subida manual o URL. Esto limita el valor de VigilaGraph IA como plataforma de vigilancia, porque el usuario tiene que traer sus propios documentos. Con OpenAlex, un proyecto en draft con una estrategia de búsqueda definida puede recolectar papers académicos automáticamente.

## Scope

### In Scope

| # | Deliverable | Capa |
|---|-------------|------|
| 1 | Modelo `CollectionRun` (nueva tabla) | API Models |
| 2 | Columna `source_name` en `Document` + enum `SourceName` | API Models |
| 3 | Conector abstracto `BaseConnector` + `OpenAlexConnector` | Worker |
| 4 | Tarea Celery `collect_from_source` (patrón `AsyncTask` existente) | Worker Tasks |
| 5 | Hook en `transition_status → collecting` que dispara la colección | API Services |
| 6 | Endpoints `GET/POST /projects/{id}/collection-runs` | API Routes |
| 7 | Schemas Pydantic para CollectionRun | API Schemas |
| 8 | Tipos Frontend + hook `useCollect` | Web Types/Hooks |
| 9 | Botón "Collect Now" + badge de source en documentos | Web UI |
| 10 | Fix mismatch frontend: */strategy → */search-strategy | Web Hooks |

### Out of Scope (deferido)

- Conectores Semantic Scholar, Lens.org (requieren API keys)
- Web scraping con trafilatura
- Gestión de credenciales de fuentes externas
- Dashboard de rate limiting
- WebSocket para progreso en tiempo real
- Tests automatizados (el proyecto no tiene infraestructura)

## Capacidades

### Nuevas Capacidades
- `collection-runs`: ejecuciones de recolección desde fuentes externas, con tracking de estado, documentos encontrados/insertados, errores
- `openalex-connector`: integración con API REST de OpenAlex (`/works?search=...`) con paginación, rate limiting y retry

### Capacidades Modificadas
- `document-management`: se agrega `source_name` al modelo y schemas
- `project-status-machine`: la transición `draft → collecting` ahora dispara side effects (crea CollectionRun + encola tarea Celery)

## Enfoque Técnico

1. **SourceName enum**: `StrEnum` en `app/models/enums.py` con valores `manual_upload | openalex | semantic_scholar | lens | web`. Default `manual_upload`.
2. **CollectionRun model**: misma estructura que `GraphRun` (mismo patrón de run tracking). FK a `surveillance_projects`, status enum, timestamps, contadores, `error_message`, `metadata_json`.
3. **Conectores**: `BaseConnector(ABC)` con método `fetch(query) → AsyncGenerator[dict]`. `OpenAlexConnector` implementa llamadas a la API con `httpx.AsyncClient`, paginación vía `meta.next_cursor`, rate limiting de 10 req/s (polite pool), retry con `tenacity`.
4. **Colección**: la tarea Celery lee la `SearchStrategy` del proyecto, construye queries, itera el conector, desduplica por `(source_name, source_id)` → DOI → checksum, hace batch insert de documentos, actualiza `CollectionRun`.
5. **Status hook**: `ProjectService.transition_status` detecta `to_status="collecting"`, valida que exista `SearchStrategy` y que `sources_selected` incluya `openalex`, crea `CollectionRun`, encola tarea Celery con `collect_from_source.delay(...)`.
6. **Frontend**: el botón "Collect Now" disponible solo en status `draft`. La tabla de documentos muestra un badge con el `source_name`. El hook `use-collection.ts` expone `useCollectionRuns(projectId)` y `useTriggerCollection()`.

## Archivos Afectados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `apps/api/app/models/enums.py` | **Nuevo** | `SourceName` enum compartido |
| `apps/api/app/models/collection_run.py` | **Nuevo** | Modelo `CollectionRun` |
| `apps/api/app/models/document.py` | Modificado | +`source_name` column |
| `apps/api/app/models/__init__.py` | Modificado | Exportar `CollectionRun` |
| `apps/api/app/models/project.py` | Modificado | +`collection_runs` relationship |
| `apps/api/app/schemas/collection_run.py` | **Nuevo** | Schemas `CollectionRunResponse`, `CollectionRunListResponse` |
| `apps/api/app/schemas/__init__.py` | Modificado | Exportar nuevos schemas |
| `apps/api/app/schemas/document.py` | Modificado | +`source_name` en `DocumentResponse` |
| `apps/api/app/api/v1/projects.py` | Modificado | +2 endpoints de collection |
| `apps/api/app/services/project_service.py` | Modificado | Hook `draft→collecting` |
| `apps/worker/worker/connectors/base.py` | **Nuevo** | `BaseConnector` ABC |
| `apps/worker/worker/connectors/openalex.py` | **Nuevo** | `OpenAlexConnector` |
| `apps/worker/worker/tasks/__init__.py` | Modificado | Importar collection_tasks |
| `apps/worker/worker/tasks/collection_tasks.py` | **Nuevo** | Tarea `collect_from_source` |
| `apps/web/types/api.ts` | Modificado | +`source_name`, +`CollectionRun`, fix SearchStrategy |
| `apps/web/hooks/use-collection.ts` | **Nuevo** | Hooks `useCollectionRuns`, `useTriggerCollection` |
| `apps/web/hooks/use-projects.ts` | Modificado | Fix */strategy → */search-strategy |
| `apps/web/hooks/use-documents.ts` | Modificado | Fix SearchStrategy type |
| `apps/web/app/projects/[id]/page.tsx` | Modificado | +"Collect Now" button |
| `apps/web/app/projects/[id]/documents/page.tsx` | Modificado | +source badge |

## Riesgos

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| OpenAlex rate limit (10 req/s) | Baja | Usar `asyncio.Semaphore` + espera entre requests. Son pocos documentos por proyecto. |
| Dedup incorrecto entre sources | Media | Prioridad: `(source_name, source_id)` > DOI > checksum. El mismo paper puede llegar por distintos sources. |
| Worker no encuentra modelos del API | Baja | `PYTHONPATH` ya incluye `apps/api`. Verificar import en worker. |
| Celery task se ejecuta sin SearchStrategy | Baja | Validación en `transition_status` antes de encolar. |
| Frontend mismatch */strategy rompe | Media | Fix explícito en este change, sincronizar con backend. |

## Rollback Plan

1. **Base de datos**: `ALTER TABLE documents DROP COLUMN source_name; DROP TABLE collection_runs;`
2. **Código**: revertir commits que toquen `apps/api/app/models/`, `apps/worker/worker/connectors/`, `apps/web/types/api.ts`
3. **Worker**: reiniciar worker para que no cargue tareas nuevas
4. **Frontend**: si el badge o botón rompen, el layout sigue funcionando (datos opcionales)

## Dependencias

- `httpx` y `tenacity`: ya en worker deps
- `Celery`: ya configurado con Redis broker
- OpenAlex: sin API key, público
- Worker ya importa `app.models.*` — no requiere cambios de infraestructura

## Criterios de Éxito

- [ ] `POST /projects/{id}/collect` crea CollectionRun, encola tarea, devuelve 202
- [ ] Worker recolecta documentos desde OpenAlex y los inserta en la DB
- [ ] Documentos recolectados tienen `source_name = "openalex"`, DOI, abstract, authors
- [ ] Dedup funciona: misma búsqueda dos veces no duplica documentos
- [ ] Frontend muestra badge de source y botón "Collect Now" en proyectos draft
- [ ] Frontend usa */search-strategy (no */strategy)
