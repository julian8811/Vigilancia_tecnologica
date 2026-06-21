# Especificación: Document Management

> Gestión del campo source_name en documentos, schemas y frontend.

---

## Requerimiento: Campo source_name en Document

`Document.source_name: str` default `"manual_upload"`, nullable=false. Enum `SourceName` en `app/models/enums.py` como `StrEnum`: `manual_upload`, `openalex`, `semantic_scholar`, `lens`, `web`.

- Feliz manual: source_name="manual_upload".
- Feliz OpenAlex: source_name="openalex".
- Migración: documentos existentes heredan "manual_upload".

## Requerimiento: Schema DocumentResponse

Agregar `source_name: str | None = None` (opcional, no rompe clientes).

## Requerimiento: Frontend tipos + badge

`api.ts`: agregar `source_name?: string` a `Document`. Tabla muestra badge con source cuando no es `manual_upload`.

## Requerimiento: Fix */strategy → */search-strategy

`use-projects.ts`: cambiar URLs de `/strategy` a `/search-strategy` (GET, PUT, POST). Backend siempre usó `/search-strategy`.
