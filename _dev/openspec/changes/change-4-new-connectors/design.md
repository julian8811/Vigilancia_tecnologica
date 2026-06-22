# Diseño Técnico: Change 4 — Nuevos Conectores

## 1. SemanticScholarConnector

### Archivo
`apps/worker/worker/connectors/semantic_scholar.py`

### Clase
```python
class SemanticScholarConnector(BaseConnector):
    def __init__(self, api_key: str | None = None): ...
    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]: ...
```

### Decisiones
- Si `api_key` está presente: `Semaphore(1)` y header `x-api-key`.
- Si no: `Semaphore(5)` para ser conservador con el pool compartido.
- Offset pagination: `offset += limit` hasta agotar resultados o `max_results`.
- Fields solicitados: `title,abstract,authors,year,externalIds,openAccessPdf`.
- `externalIds.doi` puede venir como string sin URL → no agregar prefijo.

### Mapping helpers
- `_normalize_paper(paper) -> dict`
- `_extract_institutions(authors) -> list[str]` (de `affiliations` si existe)

---

## 2. LensConnector

### Archivo
`apps/worker/worker/connectors/lens.py`

### Clase
```python
class LensConnector(BaseConnector):
    def __init__(self, api_token: str): ...
    async def fetch(self, query: str, max_results: int = 500) -> AsyncGenerator[dict, None]: ...
```

### Decisiones
- POST con JSON body. Query DSL simple: `{"query": {"match": {"title": query}}}`.
- Bearer token en header `Authorization`.
- Semaphore(1) dado el límite de 10 req/min.
- Paginación: `from += size`, default `size=200`.
- Si `LENS_API_TOKEN` vacío: `raise ValueError` al instanciar.

### Mapping helpers
- `_normalize_scholarly(record) -> dict`
- `_extract_doi(external_ids) -> str | None`
- `_extract_url(source_urls) -> str | None`
- `_extract_authors(authors) -> list[str]`
- `_extract_institutions(authors) -> list[str]` (deduplicadas)

---

## 3. WebScraperConnector

### Archivo
`apps/worker/worker/connectors/web.py`

### Clase
```python
class WebScraperConnector:
    async def scrape_urls(self, urls: list[str], max_urls: int = 50) -> AsyncGenerator[dict, None]: ...
```

### Decisiones
- NO extiende `BaseConnector` porque no es query-based.
- URLs provienen de `SearchStrategy.scrape_urls` (campo Text, separado por newline o comma).
- `trafilatura.fetch_url(url)` → `bare_extraction(..., with_metadata=True, output_format='dict')`.
- `urllib.robotparser.RobotFileParser` para verificar `robots.txt` por dominio (cache en memoria).
- Delay: `asyncio.sleep(random.uniform(1, 3))` entre requests.
- `source_id` = `hashlib.md5(url.encode()).hexdigest()`.
- `abstract` = primeros 500 chars del body.
- `metadata_json` = `{ "full_text": body, "hostname": hostname }`.

### Mapping helpers
- `_parse_date(date_str) -> int | None`
- `_parse_authors(author_str) -> list[str]`
- `_is_allowed(url) -> bool`

---

## 4. Collection Tasks Routing

### Archivo
`apps/worker/worker/tasks/collection_tasks.py`

### Cambios
En el bloque `if run.source_name == "openalex":`:
```python
elif run.source_name == "semantic_scholar":
    from worker.connectors.semantic_scholar import SemanticScholarConnector
    connector = SemanticScholarConnector(api_key=settings.SEMANTIC_SCHOLAR_API_KEY or None)
elif run.source_name == "lens":
    from worker.connectors.lens import LensConnector
    if not settings.LENS_API_TOKEN:
        raise ValueError("LENS_API_TOKEN not configured")
    connector = LensConnector(api_token=settings.LENS_API_TOKEN)
elif run.source_name == "web":
    from worker.connectors.web import WebScraperConnector
    urls = _parse_scrape_urls(strategy.scrape_urls)
    connector = WebScraperConnector()
    async for raw_doc in connector.scrape_urls(urls):
        ...
```

Para web, el conector no usa `_build_search_query`. Se leen URLs directamente.

### `_parse_scrape_urls(raw: str | None) -> list[str]`
- Split por newline, comma, o whitespace.
- Strip, filtrar vacíos, validar que sean URLs http/https.

---

## 5. SearchStrategy Schema Changes

### Modelo
`apps/api/app/models/search_strategy.py`:
```python
scrape_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### Schemas
`apps/api/app/schemas/search_strategy.py`:
- Agregar `scrape_urls: str | None = None` a `SearchStrategyCreate`, `SearchStrategyUpdate`, `SearchStrategyResponse`.

### Migración
`apps/api/alembic/versions/003_scrape_urls.py`:
- `ALTER TABLE search_strategies ADD COLUMN scrape_urls TEXT;`

---

## 6. Config Changes

### Archivo
`apps/api/app/core/config.py`:
```python
SEMANTIC_SCHOLAR_API_KEY: str = ""
LENS_API_TOKEN: str = ""
```

### Worker acceso
El worker necesita leer estas variables. Opciones:
1. Importar `Settings` desde `app.core.config` (current API settings).
2. Cargar desde env directamente en el conector.

**Decisión**: importar `settings` desde `app.core.config` para mantener una sola fuente de verdad.

### .env.example
Agregar:
```bash
SEMANTIC_SCHOLAR_API_KEY=
LENS_API_TOKEN=
```

---

## 7. Frontend Changes (mínimos)

- `apps/web/types/api.ts`: agregar `scrape_urls?: string` a `SearchStrategy`.
- `apps/web/app/projects/[id]/page.tsx`: si `web` está seleccionado, mostrar textarea para pegar URLs.
- No nuevos endpoints; se reusa `POST /projects/{id}/status` con `"collecting"`.

---

## 8. PRs Plan

| PR | Scope | Líneas estimadas |
|---|---|---|
| PR 1 | Semantic Scholar connector + routing | ~180 |
| PR 2 | Lens.org connector + config | ~220 |
| PR 3 | Web scraper + SearchStrategy.scrape_urls + frontend textarea | ~250 |
