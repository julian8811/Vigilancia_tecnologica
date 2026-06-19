# VigilaGraph IA

**AI-powered technology surveillance platform.**  
Monitor, analyse, and visualise technology landscapes across patents, news, repositories, and scientific literature.

## Architecture

```
vigilagraph/
├── apps/
│   ├── api/        — FastAPI backend (Python 3.12)
│   ├── web/        — Next.js 14 frontend (TypeScript)
│   └── worker/     — Celery worker (Python 3.12)
├── packages/
│   └── shared/     — Shared TypeScript types
├── infra/          — Docker Compose, Nginx configs, scripts
└── prompts/        — Prompt templates for AI pipelines
```

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. Open the app
open http://localhost:3000
```

## Services

| Service   | Port  | Description                    |
|-----------|-------|--------------------------------|
| **API**   | :8000 | FastAPI REST backend            |
| **Web**   | :3000 | Next.js frontend                |
| **Worker**| —     | Celery async task runner        |
| **DB**    | :5432 | PostgreSQL 16 + pgvector        |
| **Redis** | :6379 | Message broker / cache          |
| **MinIO** | :9000 | S3-compatible object storage    |

## Graphify

[Graphify](https://pypi.org/project/graphifyy/) is an external CLI tool for knowledge-graph extraction.  
It is installed via `uv tool install graphifyy` and invoked as a subprocess from the worker — it is **not** a Python project dependency.

## Development

```bash
# API only (with hot reload)
cd apps/api && uv run uvicorn app.main:app --reload

# Web only
cd apps/web && npm run dev

# Worker
cd apps/worker && uv run celery -A worker.app worker -l info
```

## License

Proprietary — all rights reserved.
