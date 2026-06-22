# Diseño: Change 3 — Integración de Fuentes Externas (OpenAlex)

## Enfoque Técnico

Se extiende la máquina de estados del proyecto para que la transición `draft → collecting` dispare side effects: crear un `CollectionRun`, validar `SearchStrategy`, y encolar una tarea Celery. El worker recolecta documentos desde OpenAlex vía un conector abstracto con paginación cursor-based, rate limiting, y dedup por `(source_name, source_id)` > DOI > checksum. Frontend agrega botón "Collect Now" y badge de source.

## Decisiones de Arquitectura

### Decisión: Hook en `transition_status` en vez de endpoint separado

| Opción | Tradeoff |
|--------|----------|
| **Hook en service** (elegido) | Unifica la lógica: transicionar a `collecting` siempre dispara colección. No hay forma de estar en `collecting` sin una corrida asociada. |
| Endpoint POST /projects/{id}/collect separado | Más explícito pero permite estados inconsistentes (collecting sin CollectionRun). |

### Decisión: `source_name` como columna directa en Document, no join

| Opción | Tradeoff |
|--------|----------|
| **Columna directa** (elegido) | Consultas más rápidas, sin JOIN. El source_name es inmutable después de insert. |
| Tabla separada DocumentSource | Normalización innecesaria para un string fijo de 20 caracteres. |

### Decisión: Dedup por `(source_name, source_id)` antes que DOI

| Opción | Tradeoff |
|--------|----------|
| **(source_name, source_id) → DOI → checksum** (elegido) | Captura duplicados exactos del mismo source. DOI catch para el mismo paper desde distintos sources. Checksum catch para documentos subidos/URL. |
| Solo DOI | Papers sin DOI (muchos en OpenAlex) se duplican. |

### Decisión: Worker usa `AsyncTask` existente + engine propio

Mismo patrón que `graph_tasks.py`. El worker tiene su propio engine asíncrono a la DB. No comparte el engine de la API. El `PYTHONPATH` ya incluye `apps/api` — los modelos son importables.

### Decisión: No agregar `CollectionRun` al schema de `ProjectResponse`

Evita N+1 en listados de proyectos. `CollectionRun` tiene su propio endpoint paginado.

## Flujo de Datos

```
[Frontend] → POST /projects/{id}/status?status=collecting
    ↓
ProjectService.transition_status()
    ├── Valida transición draft→collecting
    ├── Valida que SearchStrategy exista y tenga "openalex" en sources_selected
    ├── Crea CollectionRun (status=pending)
    ├── Encola collect_from_source.delay(project_id, run_id)
    └── Retorna ProjectResponse (status=collecting)

[Celery Worker] → collect_from_source(project_id, run_id)
    ├── DB: CollectionRun → status=running, started_at=now
    ├── DB: Lee SearchStrategy → keywords, boolean_queries
    ├── OpenAlexConnector.fetch(search_query) → AsyncGenerator[dict]
    │   ├── GET /works?search=...&cursor=*&per_page=100
    │   ├── Semaphore(10) + asyncio.sleep(0.1) → 10 req/s
    │   ├── tenacity retry (3 intentos, exponential backoff)
    │   └── Parsea cada work → dict normalizado
    ├── Dedup pipeline:
    │   Por cada work:
    │   1. Buscar por (source_name="openalex", source_id=work.id)
    │   2. Si no, buscar por DOI exacto en el proyecto
    │   3. Si no, buscar por checksum
    │   4. Si no existe → INSERT
    │   (Acumula en batch de 50 para INSERT)
    ├── DB: CollectionRun → status=completed, docs_found=N, docs_inserted=M
    └── Si error → status=failed, error_message=...
```

## Cambios en Archivos

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `apps/api/app/models/enums.py` | Crear | `SourceName(StrEnum)` — `manual_upload`, `openalex`, `semantic_scholar`, `lens`, `web` |
| `apps/api/app/models/collection_run.py` | Crear | `CollectionRun` model — mismo patrón que `GraphRun` |
| `apps/api/app/models/document.py` | Modificar | +`source_name: Mapped[str]` default `"manual_upload"` |
| `apps/api/app/schemas/collection_run.py` | Crear | `CollectionRunResponse`, `CollectionRunListResponse` |
| `apps/api/app/api/v1/projects.py` | Modificar | +`GET/POST /{id}/collection-runs` |
| `apps/api/app/services/project_service.py` | Modificar | Hook en `transition_status` → `to_status="collecting"` |
| `apps/worker/worker/connectors/base.py` | Crear | `BaseConnector(ABC)` — `fetch(query) → AsyncGenerator[dict]` |
| `apps/worker/worker/connectors/openalex.py` | Crear | `OpenAlexConnector` — httpx, paginación, rate limit, retry |
| `apps/worker/worker/tasks/collection_tasks.py` | Crear | `collect_from_source` — AsyncTask, dedup, batch insert |
| `apps/web/hooks/use-collection.ts` | Crear | `useCollectionRuns(projectId)`, `useTriggerCollection()` |
| `apps/web/types/api.ts` | Modificar | +`CollectionRun`, +`source_name` en `Document`, fix `SearchStrategy` URL |
| `apps/web/app/projects/[id]/page.tsx` | Modificar | +"Collect Now" button en draft |
| `apps/web/app/projects/[id]/documents/page.tsx` | Modificar | +badge de source en tabla |

## Interfaces / Contratos

### Modelo `CollectionRun`

```python
class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(20), nullable=False, comment="openalex | semantic_scholar | lens | web")
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, comment="pending | running | completed | failed")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    docs_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    docs_inserted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["SurveillanceProject"] = relationship(back_populates="collection_runs")
```

### Endpoints

```
GET  /projects/{id}/collection-runs?page=1&page_size=20
     → 200 CollectionRunListResponse

POST /projects/{id}/collection-runs
     → 202 { "message": "Collection queued", "run_id": "uuid" }
     → 422 si no hay SearchStrategy o no incluye "openalex"
```

### Conector `BaseConnector`

```python
class BaseConnector(ABC):
    @abstractmethod
    async def fetch(self, query: str, **kwargs) -> AsyncGenerator[dict, None]:
        """Produce documentos normalizados como dicts."""
        ...
```

### `OpenAlexConnector`

Normaliza cada work de OpenAlex a:

```python
{
    "source_id": str,           # openalex work ID (W...)
    "title": str,
    "doi": str | None,
    "abstract": str | None,
    "authors": list[str],
    "institutions": list[str],
    "publication_year": int | None,
    "language": str | None,
    "url": str,                 # primary_location.landing_page_url
    "document_type": str,       # "paper"
    "source_name": "openalex",
}
```

### `collect_from_source` Task Signature

```python
@celery_app.task(base=AsyncTask, bind=True, name="collect_from_source")
async def collect_from_source(self, project_id: str, run_id: str) -> dict: ...
```

### Frontend Types

```typescript
interface CollectionRun {
  id: string;
  project_id: string;
  source_name: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at?: string;
  finished_at?: string;
  docs_found?: number;
  docs_inserted?: number;
  error_message?: string;
  created_at: string;
}

// Document se extiende con:
interface Document {
  // ...existing fields...
  source_name: string;  // nuevo
}
```

## Secuencias

### Collect Now exitoso

```
Usuario              Frontend              API                  Worker
  │                     │                   │                     │
  │  Click "Collect"    │                   │                     │
  │────────────────────>│                   │                     │
  │                     │  POST /projects/  │                     │
  │                     │  {id}/status?     │                     │
  │                     │  status=collecting│                     │
  │                     │──────────────────>│                     │
  │                     │                   │  Valida transición  │
  │                     │                   │  Valida SearchStrat │
  │                     │                   │  Crea CollectionRun │
  │                     │                   │  Encola Celery task │
  │                     │  202 + Project    │                     │
  │                     │<──────────────────│                     │
  │   Badge "collecting"│                   │                     │
  │<────────────────────│                   │                     │
  │                     │                   │                     │
  │                     │                   │   collect_from_     │
  │                     │                   │   source(proj,run)  │
  │                     │                   │  ──────────────────>│
  │                     │                   │                     │  OpenAlex API
  │                     │                   │                     │──GET /works?search=...──>
  │                     │                   │                     │<──200 works[]──────────
  │                     │                   │                     │  (paginación cursor)
  │                     │                   │                     │  ...repite...
  │                     │                   │                     │
  │                     │                   │                     │  Dedup + batch INSERT
  │                     │                   │                     │  Update CollectionRun
  │                     │                   │                     │  (status=completed)
```

### Dedup — mismo work dos veces

```
Collect Run #1:
  OpenAlex work W123 → (source_name="openalex", source_id="W123") → no existe → INSERT

Collect Run #2 (misma búsqueda):
  OpenAlex work W123 → (source_name="openalex", source_id="W123") → existe → SKIP
```

## Estrategia de Testing

| Capa | Qué testear | Cómo |
|------|-------------|------|
| Unit | `SourceName` enum | Valores correctos, default `manual_upload` |
| Unit | `ProjectStatusMachine.can_transition` | `draft→collecting` permitido, `archived→collecting` no |
| Unit | `BaseConnector.fetch` signature | ABC methods raise `NotImplementedError` |
| Unit | Dedup query building | Lógica de lookup: source_name+source_id → DOI → checksum |
| Unit | `OpenAlexConnector._normalize_work()` | Transformación de response OpenAlex a dict interno |
| Integ | `transition_status → collecting` hook | Mock Celery task, verificar CollectionRun creado |
| Integ | `POST /projects/{id}/collection-runs` | 202 con SearchStrategy válida, 422 sin ella |
| E2E | Frontend botón Collect Now | Solo visible en draft, dispara transición |

## Migración

### Nueva migración Alembic (`002_collection_runs.py`)

```python
def upgrade():
    # 1. source_name column en documents
    op.add_column("documents", sa.Column("source_name", sa.String(20),
        server_default="manual_upload", nullable=False,
        comment="manual_upload | openalex | semantic_scholar | lens | web"))
    op.create_index("ix_documents_source_lookup", "documents",
        ["project_id", "source_name", "source_id"])

    # 2. CollectionRun table
    op.create_table("collection_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_name", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("docs_found", sa.Integer, nullable=True),
        sa.Column("docs_inserted", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="External source collection runs per project",
    )

def downgrade():
    op.drop_table("collection_runs")
    op.drop_index("ix_documents_source_lookup")
    op.drop_column("documents", "source_name")
```

## Preguntas Abiertas

- [ ] Determinar si `transition_status` debe fallar (422) o solo warn si no hay `SearchStrategy`. Por ahora: 422 con mensaje claro.
- [ ] Máximo de works por CollectionRun: ¿200? ¿1000? OpenAlex permite hasta 10k por query paginada. Definir límite inicial de 500.
- [ ] `metadata_json` en `CollectionRun`: qué guardar? Versión de API, query usada, páginas recorridas.
