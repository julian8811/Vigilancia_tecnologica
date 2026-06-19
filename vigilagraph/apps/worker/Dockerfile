FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install Playwright system deps early so layer is cached.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --frozen --no-dev

# ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd -r vigilagraph && useradd -r -g vigilagraph -d /app -s /sbin/nologin vigilagraph

# Runtime Playwright deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .

# Install Playwright browsers (Chromium only for PDF rendering)
RUN playwright install chromium 2>/dev/null || true

RUN mkdir -p /data/storage && chown -R vigilagraph:vigilagraph /app /data/storage

# Graphify is expected to be installed via `uv tool install graphifyy`.
# It is invoked as a CLI subprocess, not a Python import.
RUN echo '#!/bin/sh\necho "ERROR: graphify not installed. Run: uv tool install graphifyy"' > /usr/local/bin/graphify \
    && chmod +x /usr/local/bin/graphify

USER vigilagraph

CMD ["celery", "-A", "worker.app", "worker", "-l", "info"]
