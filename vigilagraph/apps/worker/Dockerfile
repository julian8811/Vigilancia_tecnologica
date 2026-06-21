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
COPY worker/pyproject.toml .
RUN uv sync

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

# Install uv in runtime for graphify CLI tool
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY --from=builder /app/.venv .venv

# Copy API models (needed for app.models.* imports)
COPY api/app /app/app
# Copy worker code
COPY worker/worker /app/worker

# Install Playwright browsers (Chromium only for PDF rendering)
RUN playwright install chromium 2>/dev/null || true

RUN mkdir -p /data/storage && chown -R vigilagraph:vigilagraph /app /data/storage

# Install Graphify CLI tool
RUN UV_LINK_MODE=copy pip install graphifyy 2>/dev/null || \
    echo '#!/bin/sh\necho "WARNING: graphify not installed. Install: pip install graphifyy"' > /usr/local/bin/graphify \
    && chmod +x /usr/local/bin/graphify

USER vigilagraph

CMD ["celery", "-A", "worker.app", "worker", "-l", "info"]
