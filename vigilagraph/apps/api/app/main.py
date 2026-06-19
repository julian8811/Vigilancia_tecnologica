"""VigilaGraph IA — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog import get_logger

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs on startup and shutdown."""
    configure_logging()
    logger.info("starting_up", env=settings.ENV, backend_url=settings.BACKEND_URL)

    # ── Startup ──────────────────────────────────────────────────
    # Database engine is lazily initialised via the session factory.
    # Add any other startup tasks here (e.g. connect to S3, verify Celery).

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    from app.db.session import engine

    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="VigilaGraph IA",
    description="AI-powered technology surveillance API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers ────────────────────────────────────────────────
register_error_handlers(app)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(v1_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root redirect — returns API metadata."""
    return {"service": "VigilaGraph IA", "version": "1.0.0", "docs": "/docs"}
