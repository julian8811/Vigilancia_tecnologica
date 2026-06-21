FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync

# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd -r vigilagraph && useradd -r -g vigilagraph -d /app -s /sbin/nologin vigilagraph

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .

RUN pip install --no-cache-dir graphifyy openai && mkdir -p /data/storage && chown -R vigilagraph:vigilagraph /app /data/storage

USER vigilagraph
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
