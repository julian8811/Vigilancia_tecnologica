.PHONY: help install lint test build run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	cd api && uv sync --dev
	cd web && bun install

lint: ## Run all linters
	cd api && uv run ruff check app/ && uv run mypy app/ --ignore-missing-imports
	cd web && npx tsc --noEmit

test: ## Run all tests
	cd api && uv run pytest tests/ -v
	cd web && npx vitest run

test-cov: ## Run tests with coverage
	cd api && uv run pytest tests/ --cov=app --cov-report=term-missing

build: ## Build frontend for production
	cd web && bun run build

dev: ## Start development environment (Docker Compose)
	docker compose up -d

dev-down: ## Stop development environment
	docker compose down

run-api: ## Run API locally (dev mode)
	cd api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-web: ## Run frontend dev server
	cd web && bun run dev

clean: ## Clean all build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
