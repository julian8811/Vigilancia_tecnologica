"""Async database session factory and utilities."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


def _connect_args() -> dict:
    """Per-dialect connect_args.

    ``statement_cache_size=0`` is asyncpg-only — it disables the
    prepared-statement cache so PgBouncer and similar transaction-
    pool proxies work. Other drivers (aiosqlite, etc.) reject the
    kwarg.
    """
    if settings.DATABASE_URL.startswith("postgresql"):
        return {"statement_cache_size": 0}
    return {}


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args=_connect_args(),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def get_session() -> AsyncSession:  # type: ignore[misc]
    """Yield an async database session, retrying on transient failures."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
