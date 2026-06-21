# Propuesta: Change 4 — Nuevos Conectores (Semantic Scholar + Lens.org + Web Scraping)

## Intención

Extender la capa de recolección externa con 3 conectores adicionales — Semantic Scholar, Lens.org y web scraping — siguiendo el mismo patrón `BaseConnector` que `OpenAlexConnector`. Cada conector permite recolectar documentos desde su fuente respectiva, normalizarlos al schema estándar del sistema y pasar por el pipeline de dedup existente.

## Alcance

### Incluido
- **PR 1**: `SemanticScholarConnector` (API REST offset-based, auth opcional vía header)
- **PR 2**: `LensConnector` (API POST con query DSL, auth Bearer token, scholarly solamente)
- **PR 3**: `WebScraperConnector` (URLs manuales, extracción con trafilatura, robots.txt + politeness)
- **Routing**: 3 nuevos `elif` en `collection_tasks.py` para encaminar por `source_name`
- **Config**: Variables de entorno `SEMANTIC_SCHOLAR_API_KEY` y `LENS_API_TOKEN`
- **Modelo**: `TrackedUrl` (o campo `scrape_urls` en SearchStrategy) para URLs de web scraping
- **Frontend**: Extensión del badge de fuente y botón Collect Now para los 3 nuevos orígenes

### Excluido
- Tabla `external_source_credentials` para API keys por organización/proyecto (se usa env vars)
- Patentes de Lens.org (scholarly solamente en esta iteración)
- Auto-descubrimiento de URLs via motores de búsqueda (solo URLs manuales)
- Indexación full-text del contenido scrapeado
- Refactor de `BaseConnector` o cambios al schema de documento

## Capacidades

### Nuevas Capacidades
- `semantic-scholar-connector`: Conexión con API Graph v1 de Semantic Scholar. Paginación offset (max 500/page). Auth opcional. Mapeo: `paperId` → `source_id`, `externalIds.doi` → `doi`.
- `lens-connector`: Conexión con Scholarly Search API de Lens.org. Paginación offset/size (max 1000). Auth Bearer token. Mapeo: `lens_id` → `source_id`, `external_ids` → `doi`.
- `web-scraper-connector`: Extracción desde URLs arbitrarias via `trafilatura.bare_extraction()`. URLs proveídas manualmente. Verificación robots.txt, delays de cortesía (1-3s), User-Agent identificable. Dedup por hash de URL.

### Capacidades Modificadas
- `collection-runs`: El endpoint `POST /projects/{id}/collect` y la tarea `collect_from_source` deben encaminar a los 3 nuevos conectores según `source_name`.
- `project-status-machine`: El hook de transición a `collecting` debe aceptar cualquiera de los 5 `SourceName` valores y crear `CollectionRun` por cada fuente seleccionada.

## Enfoque

Cada conector implementa `BaseConnector.fetch(query, max_results) → AsyncGenerator[dict]` con su propia lógica de API, rate limiting y normalización. La tarea Celery existente extiende su cadena `if/elif` para instanciar el conector correspondiente. El pipeline de dedup (source_id → DOI → checksum) y batch insert se reutiliza sin cambios.

Para web scraping, se introduce un modelo `TrackedUrl` (o un campo JSON `scrape_urls` en SearchStrategy) que almacena las URLs a scrapear por proyecto. El conector `WebScraperConnector` itera sobre esas URLs en lugar de ejecutar una búsqueda query-based.

## Áreas Afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `apps/worker/worker/connectors/semantic_scholar.py` | Nuevo | Conector Semantic Scholar |
| `apps/worker/worker/connectors/lens.py` | Nuevo | Conector Lens.org |
| `apps/worker/worker/connectors/web.py` | Nuevo | Conector Web Scraping |
| `apps/worker/worker/tasks/collection_tasks.py` | Modificado | 3 nuevos elif branches |
| `apps/worker/worker/connectors/__init__.py` | Modificado | Exportar nuevos conectores |
| `apps/api/app/core/config.py` | Modificado | `SEMANTIC_SCHOLAR_API_KEY`, `LENS_API_TOKEN` |
| `.env.example` | Modificado | Nuevas env vars documentadas |
| `apps/api/app/models/search_strategy.py` | Posible | Campo `scrape_urls` o nuevo modelo `TrackedUrl` |
| `apps/web/` | Modificado | Frontend: badges, Collect Now para nuevas fuentes |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Lens.org requiere aprobación manual para API key | Media | Documentar proceso; el conector funciona con la key ya obtenida |
| Web scraping puede ser bloqueado por el target | Media | Implementar robots.txt, User-Agent real, delays; el fallo de una URL no detiene las demás |
| Rate limits de Semantic Scholar (1000 req/s anónimo vs 1 req/s con key) | Baja | El conector aplica backoff y respeta el límite configurable |

## Plan de Rollback

Por PR individual. Cada PR es independiente: revertir los archivos tocados y eliminar los nuevos. La tarea `collect_from_source` falla con `ValueError` para source_names no soportados — no hay migraciones de base de datos que revertir (excepto el modelo `TrackedUrl` si se agrega).

## Dependencias

- `trafilatura` ya está en las dependencias del worker
- Las cuentas de API (Semantic Scholar, Lens.org) deben crearse antes de probar
- Ninguna dependencia externa nueva de Python

## Criterios de Éxito

- [ ] `SemanticScholarConnector.fetch()` retorna documentos normalizados desde la API pública sin key
- [ ] `LensConnector.fetch()` retorna documentos normalizados con token válido
- [ ] `WebScraperConnector.fetch()` extrae título, autor, fecha y contenido desde URLs reales
- [ ] La tarea `collect_from_source` encamina correctamente los 3 nuevos `source_name`
- [ ] Los documentos recolectados pasan el pipeline de dedup y se insertan en la tabla `documents`
- [ ] El frontend muestra badges y permite recolectar desde las 3 nuevas fuentes
