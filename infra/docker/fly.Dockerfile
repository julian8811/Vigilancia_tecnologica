FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY api/pyproject.toml api/uv.lock api/
RUN cd api && uv sync --no-dev

COPY api/app api/app
COPY api/alembic api/alembic
COPY api/alembic.ini api/alembic.ini

COPY infra/docker/start.sh /start.sh
RUN chmod +x /start.sh

ENV PATH="/app/api/.venv/bin:$PATH" \
    PYTHONPATH="/app/api" \
    PYTHONUNBUFFERED=1 \
    ENV=production

EXPOSE 8080

CMD ["/start.sh"]
