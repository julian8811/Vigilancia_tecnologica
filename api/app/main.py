"""VigilaGraph IA — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from structlog import get_logger

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.db.session import async_session_factory

logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs on startup and shutdown."""
    configure_logging()
    logger.info("starting_up", env=settings.ENV, backend_url=settings.BACKEND_URL)

    # ── Startup ──────────────────────────────────────────────────
    # Database engine is lazily initialised via the session factory.
    # Add any other startup tasks here (e.g. connect to S3).

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    from app.db.session import engine

    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="VigilaGraph IA",
    description="API de vigilancia tecnológica con IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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


@app.get("/health")
async def health() -> dict:
    """Liveness probe — returns 200 if the process is running."""
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    """Readiness probe — checks DB connectivity and returns 200 if all dependencies are available."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "conectado"}
    except Exception as exc:
        return {"status": "degraded", "database": str(exc)}
