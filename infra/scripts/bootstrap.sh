#!/usr/bin/env bash
#
# bootstrap.sh — Initial setup for VigilaGraph IA development.
#
# Usage:
#   chmod +x infra/scripts/bootstrap.sh && ./infra/scripts/bootstrap.sh
#
# This script:
#   1. Installs Graphify CLI via uv
#   2. Creates required directories
#   3. Copies .env.example to .env if missing
#   4. Starts Docker Compose infrastructure services
#   5. Runs Alembic migrations
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "🔄 Bootstrapping VigilaGraph IA at ${ROOT_DIR}"

# ── 1. Install Graphify CLI ───────────────────────────────────────
echo "📦 Installing Graphify CLI..."
if command -v graphify &>/dev/null; then
    echo "   graphify already installed ($(graphify --version 2>/dev/null || echo 'version check skipped'))"
else
    uv tool install graphifyy
    echo "   graphify installed."
fi

# ── 2. Create required directories ─────────────────────────────────
echo "📁 Creating storage directories..."
mkdir -p "${ROOT_DIR}/data/storage"
mkdir -p "${ROOT_DIR}/data/upload"
echo "   Done."

# ── 3. Environment file ───────────────────────────────────────────
if [ ! -f "${ROOT_DIR}/.env" ]; then
    echo "📄 Copying .env.example → .env"
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "   ⚠️  Edit .env with your production secrets before deploying."
else
    echo "   .env already exists, skipping."
fi

# ── 4. Docker Compose infrastructure ──────────────────────────────
echo "🐳 Starting infrastructure services (PostgreSQL + MinIO)..."
docker compose -f "${ROOT_DIR}/infra/docker/docker-compose.yml" up -d
echo "   Infrastructure services started."

# ── 5. Alembic migrations ─────────────────────────────────────────
echo "🗃️  Running database migrations..."
docker compose -f "${ROOT_DIR}/infra/docker/docker-compose.yml" exec -T postgres \
    pg_isready -U vigilagraph -d vigilagraph -t 10 || true
cd "${ROOT_DIR}/api" && alembic upgrade head
echo "   Migrations applied."

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "✅ VigilaGraph IA bootstrapped successfully."
echo ""
echo "   Start the full stack:  docker compose up -d"
echo "   Open the web app:      http://localhost:3000"
echo "   API docs:              http://localhost:8000/docs"
echo "   MinIO Console:         http://localhost:9001"
