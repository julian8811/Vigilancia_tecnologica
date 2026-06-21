FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/
COPY apps/worker/pyproject.toml apps/worker/uv.lock apps/worker/

RUN cd apps/api && uv sync --no-dev
RUN cd apps/worker && uv sync --no-dev

COPY apps/api/app apps/api/app
COPY apps/api/alembic apps/api/alembic
COPY apps/api/alembic.ini apps/api/alembic.ini
COPY apps/worker/worker apps/worker/worker

COPY infra/docker/start.sh /start.sh
RUN chmod +x /start.sh

ENV PATH="/app/apps/api/.venv/bin:$PATH" \
    PYTHONPATH="/app/apps/api:/app/apps/worker" \
    PYTHONUNBUFFERED=1 \
    ENV=production

EXPOSE 8080

CMD ["/start.sh"]
