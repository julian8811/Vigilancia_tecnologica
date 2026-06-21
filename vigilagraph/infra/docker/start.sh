#!/bin/sh
set -e

# Start Redis (no persistence, in-memory only)
redis-server --port 6379 --daemonize yes
echo "[start] Redis started on 6379"

# Wait for Redis
until redis-cli ping 2>/dev/null; do
  sleep 0.5
done

# Run migrations
cd /app/apps/api && alembic upgrade head

# Start Celery worker in background
cd /app/apps/worker && celery -A worker.app worker --loglevel=info --concurrency=2 &

# Start FastAPI (foreground — keeps container alive)
cd /app/apps/api && exec uvicorn app.main:app --host 0.0.0.0 --port 8080
