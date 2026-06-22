FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app/api

COPY api/pyproject.toml ./
RUN uv sync --no-dev

COPY api/app ./app
COPY api/alembic ./alembic
COPY api/alembic.ini ./

ENV PATH="/app/api/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ENV=production

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
