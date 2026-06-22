#!/bin/sh
set -e

# Run migrations
cd /app/apps/api && alembic upgrade head

# Start FastAPI (foreground — keeps container alive)
cd /app/apps/api && exec uvicorn app.main:app --host 0.0.0.0 --port 8080
