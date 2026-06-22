#!/bin/sh
set -e

# Run migrations
cd /app/api && alembic upgrade head

# Start FastAPI (foreground — keeps container alive)
cd /app/api && exec uvicorn app.main:app --host 0.0.0.0 --port 8080
