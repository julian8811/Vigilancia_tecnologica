"""Pytest configuration — async test client, test database, and auth fixtures.

Usage:

    pytest apps/api/tests -v --cov=app
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Monkey-patch sqlite3 with pysqlite3-binary before any sqlite3/aiosqlite
# import.  The system _sqlite3 C extension may lack sqlite3_deserialize.
# ---------------------------------------------------------------------------
import sys as _sys

try:
    import pysqlite3 as _pysqlite3
    _sys.modules["sqlite3"] = _pysqlite3
except ImportError:
    pass

import asyncio
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Make JSONB (PostgreSQL-only) work on SQLite by compiling it to standard
# JSON.  This avoids model changes just for the test suite.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # noqa: ARG001
    return compiler.visit_JSON(element, **kw)


import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_active_user, get_db
from app.db.base import Base
from app.main import app

# ---------------------------------------------------------------------------
# Test database — file-based SQLite so every connection sees the same data.
# ---------------------------------------------------------------------------

_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="vigilagraph_test_")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)

TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _cleanup_db() -> None:
    """Remove the temporary database file when the process exits."""
    global _db_fd, _db_path
    os.close(_db_fd)
    if os.path.exists(_db_path):
        os.unlink(_db_path)


import atexit

atexit.register(_cleanup_db)


@pytest.fixture(scope="function")
def event_loop():
    """Provide a fresh event loop per test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after.

    File-based SQLite ensures all connections share the same data.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Dependency overrides
# ---------------------------------------------------------------------------


async def _override_get_db() -> AsyncGenerator[AsyncSession, Any]:
    """Provide a test session instead of the production one."""
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, Any]:
    """Provide an async test client against the FastAPI app."""
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user via API and return Bearer auth headers.

    Uses the same register endpoint a real client would hit, ensuring the
    test user + org exist in the DB before any authenticated request.
    """
    import secrets

    email = f"test-{secrets.token_hex(4)}@example.com"
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "name": "Test User",
        "password": "testpass123",
        "organization_name": "Test Org",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    token = data["access_token"]

    # Override the current-user dependency with the registered user so tests
    # that use auth_headers DON'T hit the login endpoint again.
    user_id = data["user"]["id"]
    org_id = data["user"]["organization_id"]

    async def _override_current_user():
        from app.models.user import User
        from sqlalchemy import select

        async with TestSessionFactory() as session:
            result = await session.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError(f"User {user_id} not found in DB")
            return user

    app.dependency_overrides[get_current_active_user] = _override_current_user
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Helper to create a project
# ---------------------------------------------------------------------------


async def create_test_project(client: AsyncClient, auth_headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    """Create a test surveillance project and return the response data."""
    payload = {
        "name": "Test Project",
        "topic": "biological control",
        "description": "A test project for integration testing",
        "surveillance_type": "technological",
        "language": "en",
        **overrides,
    }
    resp = await client.post("/api/v1/projects", json=payload, headers=auth_headers)
    assert resp.status_code == 201, f"Project creation failed: {resp.text}"
    return resp.json()
