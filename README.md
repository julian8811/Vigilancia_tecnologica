# VigilaGraph IA

> AI-powered technology surveillance platform.
> Monitor, analyse, and visualise technology landscapes across patents, news, repositories, and scientific literature.

[![CI](https://github.com/julian8811/Vigilancia_tecnologica/actions/workflows/ci.yml/badge.svg)](https://github.com/julian8811/Vigilancia_tecnologica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## What is VigilaGraph?

VigilaGraph turns unstructured technology signals (open-access papers, patents, repositories, news) into a navigable knowledge graph. It ingests documents, extracts entities and relationships using an LLM-assisted pipeline (Graphify CLI), and lets you explore the resulting graph in the browser.

**Use cases**
- Competitive intelligence: track who is publishing on a given technology.
- Tech scouting: discover emerging actors and trends in a domain.
- Patent landscape analysis: visualise inventors, assignees, and citation networks.
- Research due diligence: map a research field before committing resources.

## Architecture

```
vigilagraph/
├── api/                FastAPI backend (Python 3.12 + SQLAlchemy 2.0 + Pydantic v2 + pgvector)
├── web/                Next.js 14 frontend (TypeScript, App Router, TanStack Query, shadcn/ui)
├── packages/shared/    Shared TypeScript types
├── infra/              Docker Compose, Nginx configs, deployment scripts
├── _dev/               OpenSpec specs, prompt templates, internal docs
├── docs/               Architecture decisions, ADRs, runbooks
└── .github/            CI, issue/PR templates, CODEOWNERS
```

> The previous `apps/api`, `apps/web`, `apps/worker` layout was refactored to the flat structure above. The Celery worker is no longer a separate service — background work is performed by `asyncio.create_task` invocations inside the request handlers (see `apps/api/app/tasks/`).

## Quick start (local development)

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start the stack (Postgres + MinIO + API + Web)
make dev

# 3. Apply database migrations
docker compose exec api uv run alembic upgrade head

# 4. Open the app
open http://localhost:3000
```

The default `.env` is dev-friendly. **Do not** deploy with `JWT_SECRET=CHANGE-ME` — see [SECURITY.md](SECURITY.md).

## Services

| Service      | Port      | Description                                                     |
|--------------|-----------|-----------------------------------------------------------------|
| **API**      | `:8000`   | FastAPI REST backend — `/docs` for OpenAPI, `/ready` for health |
| **Web**      | `:3000`   | Next.js frontend (Rioplatense Spanish UI)                       |
| **DB**       | `:5432`   | PostgreSQL 16 with `pgvector` extension                        |
| **MinIO**    | `:9000`   | S3-compatible object storage                                    |

## Tech stack

**Backend** — FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Alembic · asyncpg · structlog · slowapi · bcrypt · JWT (HS256)
**Frontend** — Next.js 14 (App Router) · React 18 · TypeScript (strict) · TanStack Query · React Hook Form + Zod · shadcn/ui · Tailwind · Cytoscape.js
**Infrastructure** — PostgreSQL 16 + pgvector · MinIO · Graphify CLI (knowledge-graph extraction) · Docker Compose · Railway / Render / Fly.io

## Development

```bash
make install   # install everything (uv + bun)
make lint      # ruff + mypy + tsc
make test      # pytest + vitest
make test-cov  # pytest with coverage report
make build     # production build of the frontend
```

Pre-commit hooks are configured (see `.pre-commit-config.yaml`). Install them with:

```bash
pip install pre-commit
pre-commit install
```

## Deployment

The repo includes config for three PaaS targets:

- **Railway** — `railway.json` + `nixpacks.toml` (Python 3.12 + node 20)
- **Render** — `render.yaml` (managed Postgres + web service)
- **Fly.io** — `fly.toml` + `infra/docker/fly.Dockerfile`

See [docs/DEPLOYMENT.md](docs/ARCHITECTURE.md#deployment) for the full runbook.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, data flow, ADRs
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [SECURITY.md](SECURITY.md) — how to report vulnerabilities
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards
- API docs at `/docs` once the API is running (FastAPI auto-generated)

## License

[MIT](LICENSE) — see LICENSE file for details.
