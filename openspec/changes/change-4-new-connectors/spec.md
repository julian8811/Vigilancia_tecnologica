# Especificación: Change 4 — Nuevos Conectores

## 1. semantic-scholar-connector (NUEVO)

### Requerimiento: Implementar `SemanticScholarConnector`
- Implementa `BaseConnector`.
- Endpoint: `GET https://api.semanticscholar.org/graph/v1/paper/search?query=<q>&limit=<n>&offset=<n>&fields=title,abstract,authors,year,externalIds,openAccessPdf`.
- Auth: header `x-api-key` opcional desde `SEMANTIC_SCHOLAR_API_KEY`.
- Sin API key: rate limit compartido (~1000 req/s global). Con API key: 1 req/s dedicado.
- Paginación: offset-based, `offset += limit`, `limit <= 500`.
- Retry con `tenacity` sobre 429/5xx, 3 intentos.

### Escenarios
- **Feliz**: query "neural networks" → 3 páginas, ~150 papers, todos mapeados.
- **Sin API key**: funciona con Semaphore(5), documentar límite compartido.
- **429**: retry + backoff, luego failed con mensaje claro.
- **Sin resultados**: `fetch` termina sin yield.
- **Error de red**: 3 retries, luego excepción propagada al CollectionRun.

### Mapeo
| Campo fuente | Campo normalizado |
|---|---|
| `paperId` | `source_id` |
| `externalIds.doi` | `doi` (string sin URL) |
| `title` | `title` |
| `abstract` | `abstract` |
| `authors[].name` | `authors` |
| `authors[].affiliations` | `institutions` (si se pidió) |
| `year` | `publication_year` |
| — | `language` = `None` |
| `openAccessPdf.url` o `https://www.semanticscholar.org/paper/{paperId}` | `url` |
| `"paper"` | `document_type` |

---

## 2. lens-connector (NUEVO)

### Requerimiento: Implementar `LensConnector`
- Implementa `BaseConnector`.
- Endpoint: `POST https://api.lens.org/scholarly/search`.
- Auth: header `Authorization: Bearer <LENS_API_TOKEN>`.
- Body: `{"query": {"match": {"title": <q>}}, "size": 1000, "from": 0}`.
- Rate limit: 10 req/min → Semaphore acorde.
- Paginación: `from += size`, `size <= 1000`, límite 10K resultados.
- Retry con tenacity sobre 429/5xx.

### Escenarios
- **Feliz**: query → resultados, mapeo correcto.
- **401 token inválido**: fail fast, error en CollectionRun.
- **429 rate limit**: retry, luego failed.
- **Sin resultados**: fetch termina sin yield.
- **Campo incompleto**: usar valor por defecto `None`/vacío, no fallar.

### Mapeo
| Campo fuente | Campo normalizado |
|---|---|
| `lens_id` | `source_id` |
| `external_ids[type=doi]` | `doi` |
| `title` | `title` |
| `abstract` | `abstract` |
| `authors[].first_name + last_name` | `authors` |
| `authors[].affiliations[].name` | `institutions` |
| `year_published` | `publication_year` |
| `languages[0]` | `language` |
| `source_urls[type=html][0]` | `url` |
| `"paper"` | `document_type` |

---

## 3. web-scraper-connector (NUEVO)

### Requerimiento: Implementar `WebScraperConnector`
- **NO** extiende `BaseConnector`.
- Contrato: `async def scrape_urls(urls: list[str], max_urls: int = 50) -> AsyncGenerator[dict, None]`.
- Usa `trafilatura.fetch_url` + `trafilatura.bare_extraction`.
- Respeta `robots.txt` vía `urllib.robotparser`.
- Delay aleatorio 1-3s entre URLs.
- Timeout 30s por URL.

### Escenarios
- **Feliz**: 10 URLs válidas → 10 documentos.
- **URL inválida**: skip + warning.
- **Timeout**: skip + warning.
- **robots.txt disallow**: skip + mensaje claro.
- **Sin contenido**: skip + warning.

### Mapeo
| Campo fuente | Campo normalizado |
|---|---|
| `md5(url)` | `source_id` |
| `"web"` | `source_name` |
| `title` | `title` |
| `author` (split por coma) | `authors` |
| `date` (parse año) | `publication_year` |
| `url` | `url` |
| `body[:500]` | `abstract` |
| `body` completo | `metadata_json.full_text` |
| `"article"` | `document_type` |

---

## 4. collection-runs (MODIFICADO)

### Requerimiento: Routing de 3 nuevos sources
- `collection_tasks.py` debe soportar `semantic_scholar`, `lens`, `web`.
- Para `web`: leer `SearchStrategy.scrape_urls`, parsear URLs, llamar `scrape_urls()`.
- Si API key opcional falta: warn en log, continuar (puede funcionar sin).
- Si token requerido falta: fail fast.

---

## 5. search-strategy (MODIFICADO)

### Requerimiento: Campo `scrape_urls`
- Agregar `scrape_urls: Text | None` al modelo y schemas.
- Campo opcional, usado solo cuando `web` está en `sources_selected`.

---

## 6. config (MODIFICADO)

### Requerimiento: Variables de entorno
- `SEMANTIC_SCHOLAR_API_KEY: str = ""` (opcional).
- `LENS_API_TOKEN: str = ""` (requerido para Lens).
- Actualizar `.env.example`.
