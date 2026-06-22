# Prompt maestro — Plataforma de vigilancia tecnológica asistida con IA y grafos de conocimiento usando Graphify

## 1. Contexto general del proyecto

Aplicación SaaS llamada **VigilaGraph IA**, enfocada en realizar **vigilancias tecnológicas, científicas, competitivas y estratégicas** de forma asistida con inteligencia artificial.

La aplicación debe permitir que un usuario defina un tema de vigilancia tecnológica y a partir de ese tema, la plataforma debe buscar, recolectar, organizar, analizar y reportar información de múltiples fuentes.

La aplicación debe generar:
1. Un **reporte de vigilancia tecnológica asistido con IA**.
2. Un **grafo de conocimiento** del tema investigado.
3. Una **matriz de tendencias y oportunidades**.
4. Una **matriz de actores relevantes**.
5. Una **matriz de tecnologías, aplicaciones y madurez tecnológica**.
6. Una **síntesis ejecutiva para toma de decisiones**.
7. Exportaciones en HTML, PDF, DOCX, Markdown, JSON y eventualmente PPTX.

La aplicación debe usar como base el repositorio **safishamsi/graphify**, aprovechando su capacidad para convertir documentos, carpetas, papers, PDFs, código, imágenes y corpus mixtos en un grafo de conocimiento consultable.

---

## 2. Nombre tentativo del producto

```
VigilaGraph IA
```

Nombre interno del repositorio:

```
vigilagraph
```

---

## 3. Visión del producto

Construir una plataforma que permita pasar de una pregunta amplia como:

```
Realizar una vigilancia tecnológica sobre control biológico en Colombia y el mundo.
```

A un sistema que entregue:

```
tema → búsqueda multifuente → corpus documental → extracción IA → grafo de conocimiento → análisis de tendencias → reporte ejecutivo → recomendaciones estratégicas
```

---

## 4. Propuesta de valor

> VigilaGraph IA automatiza la vigilancia tecnológica mediante búsqueda multifuente, análisis asistido con IA y generación de grafos de conocimiento, permitiendo a universidades, empresas, grupos de investigación y oficinas de innovación identificar tendencias, actores, tecnologías, oportunidades y brechas estratégicas en menos tiempo.

---

## 5. Usuarios principales

### 5.1 Investigador
### 5.2 Oficina de investigación o innovación
### 5.3 Startup o empresa
### 5.4 Consultor
### 5.5 Administrador de la plataforma

---

## 6. Alcance del MVP

### 6.1 Funcionalidades obligatorias del MVP

- autenticación de usuarios
- creación de organización
- creación de proyecto de vigilancia
- definición del tema de vigilancia
- definición de palabras clave
- generación asistida de ecuaciones de búsqueda
- selección de fuentes
- búsqueda en fuentes académicas abiertas
- carga manual de PDFs
- carga manual de URLs
- extracción de metadatos
- extracción de texto de documentos
- almacenamiento del corpus
- generación de grafo con Graphify
- lectura de `graph.json`
- visualización interactiva del grafo
- generación de resumen asistido con IA
- clasificación de documentos
- identificación de tecnologías
- identificación de actores
- identificación de tendencias
- identificación de oportunidades
- generación de reporte HTML
- exportación a PDF
- exportación a Markdown
- descarga del grafo en JSON
- panel de proyectos
- panel de documentos
- panel de actores
- panel de tecnologías
- panel de tendencias
- logs de procesamiento

### 6.2 Funcionalidades no obligatorias para MVP

- app móvil nativa
- sistema de pagos
- integración con WhatsApp
- integración con Google Drive
- colaboración en tiempo real
- edición avanzada de reportes tipo Google Docs
- generación automática de diapositivas
- vigilancia programada recurrente
- análisis bibliométrico avanzado completo
- patent landscaping avanzado
- modelos propios entrenados
- white label

---

## 7. Diferencia frente a una vigilancia tradicional

VigilaGraph IA debe automatizar gran parte del flujo:

```
búsqueda → corpus → limpieza → extracción → grafo → análisis → reporte → actualización
```

---

## 8. Repositorio base: Graphify

Usar el repositorio **safishamsi/graphify** como inspiración y herramienta base.

Graphify debe usarse inicialmente como:
1. **CLI instalada en el entorno del worker**.
2. **Skill para Codex durante desarrollo**.
3. **Motor de generación de grafo a partir del corpus documental**.
4. **Generador de `graph.json`, `graph.html` y `GRAPH_REPORT.md`**.
5. **Base para construir una capa propia de grafo consultable dentro de VigilaGraph IA**.

Patrón de adaptación:

```
VigilaGraph IA → GraphifyAdapter → CLI Graphify → graphify-out → GraphService → UI / Reportes / IA
```

---

## 9. Instalación esperada de Graphify en desarrollo

```bash
uv tool install graphifyy
graphify install --platform codex
```

Salida esperada:

```
graphify-out/
├── graph.html
├── GRAPH_REPORT.md
├── graph.json
└── cache/
```

---

## 10. Arquitectura recomendada (Monorepo)

```
vigilagraph/
├── apps/
│   ├── web/                  # Frontend Next.js
│   ├── api/                  # Backend FastAPI
│   ├── worker/               # Workers de búsqueda, IA, reportes y graphify
│   └── mcp/                  # Servidores MCP internos
├── packages/
│   ├── shared/               # Tipos compartidos
│   ├── ui/                   # Componentes UI
│   └── config/               # Configuración común
├── infra/
│   ├── docker/
│   ├── nginx/
│   ├── terraform/
│   └── scripts/
├── docs/
├── prompts/
├── tests/
├── docker-compose.yml
├── .env.example
├── README.md
└── TASKS.md
```

---

## 11. Stack tecnológico recomendado

### 11.1 Frontend
Next.js + App Router, React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, TanStack Table, React Hook Form, Zod, Recharts/ECharts, Cytoscape.js/Sigma.js, Lucide React, Sonner.

### 11.2 Backend
Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Uvicorn, httpx, tenacity, structlog, pytest, python-multipart.

### 11.3 Worker
Python 3.12, Celery, Redis/Valkey, Playwright, Scrapling, PyMuPDF, pypdf, Graphify CLI, NetworkX, Jinja2, Playwright/WeasyPrint para PDF.

### 11.4 Base de datos
PostgreSQL + pgvector (MVP). Neo4j/Memgraph (versión avanzada). Redis/Valkey para colas. MinIO/S3 para almacenamiento.

### 11.5 IA
Generación de ecuaciones, limpieza, resúmenes, clasificación, extracción de tecnologías/actores/tendencias/oportunidades, reportes, preguntas sobre el corpus.

---

## 12. Flujo principal de la aplicación

### 12.1 Crear proyecto de vigilancia
### 12.2 Generar estrategia de búsqueda
### 12.3 Recolectar fuentes
### 12.4 Crear corpus documental
### 12.5 Ejecutar Graphify
### 12.6 Enriquecer grafo con IA
### 12.7 Generar reporte

---

## 13. Módulos principales

### 13.1 Módulo de proyectos
### 13.2 Módulo de fuentes
### 13.3 Módulo de corpus
### 13.4 Módulo Graphify
### 13.5 Módulo de grafo
### 13.6 Módulo de análisis IA
### 13.7 Módulo de reportes
### 13.8 Módulo de preguntas sobre el corpus

---

## 14. Modelo de datos inicial

### 14.1 organizations
### 14.2 users
### 14.3 surveillance_projects
### 14.4 search_strategies
### 14.5 documents
### 14.6 document_chunks
### 14.7 graph_runs
### 14.8 graph_nodes
### 14.9 graph_edges
### 14.10 technologies
### 14.11 trends
### 14.12 actors
### 14.13 opportunities
### 14.14 reports

---

## 15. Endpoints API iniciales

### 15.1 Proyectos
### 15.2 Estrategia de búsqueda
### 15.3 Documentos
### 15.4 Recolección
### 15.5 Graphify y grafo
### 15.6 Análisis
### 15.7 Reportes

---

## 16. Pipeline técnico

### 16.1 Pipeline completo
### 16.2 Pipeline de recolección
### 16.3 Pipeline Graphify
### 16.4 Pipeline de reporte

---

## 17. Servicios internos

### 17.1 GraphifyAdapter
### 17.2 CorpusService
### 17.3 SourceConnectorService
### 17.4 AIAnalysisService
### 17.5 ReportService

---

## 18. Conectores de fuentes

### 18.1 Interfaz base
### 18.2 Conector OpenAlex
### 18.3 Conector Semantic Scholar
### 18.4 Conector Lens
### 18.5 Conector web genérico

---

## 19. Graphify como base del grafo

### 19.1 Qué debe tomar Graphify como entrada
### 19.2 Cómo debe enriquecer la aplicación la salida de Graphify
### 19.3 Versionado de grafos

---

## 20. Visualización del grafo

### 20.1 Vista principal
### 20.2 Filtros
### 20.3 Panel de nodo
### 20.4 Panel de comunidad

---

## 21. Reporte de vigilancia tecnológica

### 21.1 Estructura del reporte completo
### 21.2 Reporte ejecutivo
### 21.3 Reporte académico
### 21.4 Reporte empresarial

---

## 22. Matrices analíticas

### 22.1 Matriz de tecnologías
### 22.2 Matriz de actores
### 22.3 Matriz de tendencias
### 22.4 Matriz de brechas
### 22.5 Matriz de oportunidades

---

## 23. Prompting interno para IA

### 23.1 Prompt para estrategia de búsqueda
### 23.2 Prompt para extracción de tecnologías
### 23.3 Prompt para análisis de tendencias
### 23.4 Prompt para generación de reporte

---

## 24. MCP para la aplicación

### 24.1 MCP de proyectos
### 24.2 MCP de corpus
### 24.3 MCP de fuentes
### 24.4 MCP de Graphify
### 24.5 MCP de reportes
### 24.6 Seguridad MCP

---

## 25. Buenas prácticas de programación

### 25.1 Código general
### 25.2 Backend
### 25.3 Frontend
### 25.4 IA
### 25.5 Graphify

---

## 26. Seguridad

### 26.1 Seguridad general
### 26.2 Seguridad documental
### 26.3 Seguridad en scraping

---

## 27. Observabilidad

---

## 28. DevOps

### 28.1 Docker Compose
### 28.2 Producción MVP

---

## 29. Variables de entorno

---

## 30. Estructura backend

```
apps/api/
├── app/
│   ├── main.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/v1/
│   └── tests/
```

---

## 31. Estructura worker

```
apps/worker/
├── worker/
│   ├── app.py
│   ├── tasks/
│   ├── graphify/
│   ├── connectors/
│   ├── extractors/
│   ├── ai/
│   └── utils/
```

---

## 32. Estructura frontend

```
apps/web/
├── app/
├── components/
├── lib/
├── hooks/
└── types/
```

---

## 33. Pantallas del MVP

1. Login
2. Registro
3. Onboarding de organización
4. Dashboard general
5. Lista de proyectos
6. Crear proyecto de vigilancia
7. Estrategia de búsqueda
8. Carga de documentos
9. Documentos recolectados
10. Procesamiento del corpus
11. Vista de grafo
12. Detalle de nodo
13. Análisis IA
14. Tendencias
15. Tecnologías
16. Actores
17. Oportunidades
18. Reportes
19. Configuración
20. Logs de ejecución

---

## 34. Dashboard del proyecto

---

## 35. Criterios visuales

---

## 36. Testing

### 36.1 Backend (pytest)
### 36.2 Worker
### 36.3 Frontend (Vitest + Testing Library + Playwright)

---

## 37. Definition of Done

---

## 38. Primer entregable esperado de Codex

Construir una primera versión funcional que permita:

1. Levantar el monorepo con Docker Compose
2. Entrar al frontend
3. Crear organización
4. Crear proyecto de vigilancia
5. Generar estrategia de búsqueda con IA mock o real
6. Cargar PDFs o documentos
7. Convertir documentos a texto
8. Crear carpeta de corpus
9. Ejecutar Graphify sobre el corpus
10. Leer `graph.json`
11. Mostrar nodos y relaciones en una visualización básica
12. Mostrar `GRAPH_REPORT.md`
13. Generar análisis inicial con IA
14. Generar reporte HTML
15. Exportar PDF
16. Descargar JSON del grafo
17. Ver logs del proceso

---

## 39. Fases de desarrollo para Codex

### Fase 1 — Bootstrap
### Fase 2 — Modelos y base de datos
### Fase 3 — API base
### Fase 4 — Corpus y documentos
### Fase 5 — Graphify
### Fase 6 — UI del grafo
### Fase 7 — IA
### Fase 8 — Reportes
### Fase 9 — Fuentes externas
### Fase 10 — Seguridad y pruebas

---

## 40. Instrucción final para Codex

Construye esta aplicación de manera incremental. No intentes hacer todo en un solo cambio.

Prioriza primero:

```
1. estructura base
2. proyectos
3. carga de documentos
4. corpus
5. integración Graphify
6. visualización del grafo
7. análisis IA
8. reportes
9. conectores externos
10. seguridad y tests
```
