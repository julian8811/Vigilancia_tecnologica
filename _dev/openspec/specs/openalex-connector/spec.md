# Especificación: OpenAlex Connector

> Conector abstracto y su implementación OpenAlex para recolección de documentos académicos.

---

## Requerimiento: BaseConnector ABC

Clase abstracta con `fetch(self, query: str) → AsyncGenerator[dict]`.

## Requerimiento: OpenAlexConnector

Implementa `fetch()` contra `/works?search={query}&cursor=*` con `httpx.AsyncClient`.

- Paginación: `meta.next_cursor`, iterar hasta null.
- Rate limit: 10 req/s con `asyncio.Semaphore`.
- Retry: `tenacity.retry(stop=3, wait=wait_exponential())`.
- Normalización: `source_name="openalex"`, `source_id`, `title`, `doi`, `abstract` (desde inverted_index), `authors`, `institutions`, `publication_year`, `language`, `url`.
- Feliz: 3 páginas → ~75 docs.
- Edge: 429 → retry+backoff, logged.
- Edge: cursor inválido → raise, logged.
- Regla: source_id = OpenAlex ID canónico (`https://openalex.org/W...`).
