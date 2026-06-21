FROM python:3.12-slim

RUN pip install uv

WORKDIR /app/apps/worker

COPY apps/worker/pyproject.toml ./
RUN uv sync --no-dev

COPY apps/worker/worker ./worker
COPY apps/api/app ./app

ENV PATH="/app/apps/worker/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ENV=production

CMD ["celery", "-A", "worker.app", "worker", "--loglevel=info", "--concurrency=4"]
