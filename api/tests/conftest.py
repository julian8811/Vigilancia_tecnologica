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
# Build the test DATABASE_URL BEFORE any app imports so that
# ``from app.main import app`` (which loads settings.DATABASE_URL) sees
# the SQLite path, not the production Postgres default.
# ---------------------------------------------------------------------------
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="vigilagraph_test_")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-please-do-not-use-in-production")

# ---------------------------------------------------------------------------
# Make JSONB (PostgreSQL-only) work on SQLite by compiling it to standard
# JSON.  This avoids model changes just for the test suite.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):  # noqa: ARG001
    return compiler.visit_JSON(element, **kw)


import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import NullPool  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.deps import get_current_active_user, get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Test database — file-based SQLite so every connection sees the same data.
# ---------------------------------------------------------------------------

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
    Also redirects the production async_session_factory to the test
    engine so AuditService (which uses its own session) writes to
    the test DB.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import app.db.session as _db_session

    original_factory = _db_session.async_session_factory
    _db_session.async_session_factory = TestSessionFactory
    try:
        yield
    finally:
        _db_session.async_session_factory = original_factory
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
    """Provide an async test client against the FastAPI app.

    ASGITransport does not propagate cookies across requests. We
    wrap the transport's handle_async_request to inject a Cookie
    header from a shared test_cookies dict, and we capture Set-Cookie
    from each response back into that dict (including Max-Age=0
    deletes for logout). This makes the test client behave like a
    real browser.
    """
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]

    test_cookies: dict[str, str] = {}
    original_handle = transport.handle_async_request

    async def patched_handle(*args, **kwargs):
        req = kwargs.get("request") or (args[0] if args else None)
        if req is not None and "cookie" not in (k.lower() for k in req.headers) and test_cookies:
            req.headers["Cookie"] = "; ".join(
                f"{k}={v}" for k, v in test_cookies.items()
            )
        resp = await original_handle(*args, **kwargs)
        for name, value in resp.headers.raw:
            if name.lower() != b"set-cookie":
                continue
            line = value.decode()
            kv = line.split(";", 1)[0]
            if "=" not in kv:
                continue
            cookie_name, cookie_value = kv.split("=", 1)
            cookie_name = cookie_name.strip()
            cookie_value = cookie_value.strip()
            is_expired = "max-age=0" in line.lower() or cookie_value == ""
            if is_expired:
                test_cookies.pop(cookie_name, None)
            else:
                test_cookies[cookie_name] = cookie_value
        return resp

    transport.handle_async_request = patched_handle  # type: ignore[assignment]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user via API and return Bearer auth headers.

    Uses the same register endpoint a real client would hit, ensuring the
    test user + org exist in the DB before any authenticated request.

    Also includes the CSRF token in the returned headers so tests
    that hit mutating endpoints don't trip the CSRFMiddleware (the
    Bearer token alone is not enough — the SPA sends both).
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
    # Cookie-based auth: extract the vg_access token from the
    # Set-Cookie header for use in Authorization: Bearer calls.
    token = resp.cookies.get("vg_access")
    # CSRF double-submit: the server set vg_csrf on the response;
    # the SPA echoes it in the X-CSRF-Token header. The middleware
    # only checks the header against the cookie, so any source for
    # the token is fine.
    csrf_token = data.get("csrf_token") or resp.cookies.get("vg_csrf")
    assert csrf_token, "Register response must include a CSRF token (cookie or body)"

    # Override the current-user dependency with the registered user so tests
    # that use auth_headers DON'T hit the login endpoint again.
    user_id = data["user"]["id"]
    org_id = data["user"]["organization_id"]

    async def _override_current_user():
        from fastapi import HTTPException
        from app.models.user import User
        from sqlalchemy import select

        async with TestSessionFactory() as session:
            result = await session.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise RuntimeError(f"User {user_id} not found in DB")
            # Mirror the real dependency: an is_active=False user is
            # forbidden. Tests that toggle is_active mid-test (e.g.
            # test_inactive_user_gets_403) rely on this.
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Cuenta desactivada")
            return user

    app.dependency_overrides[get_current_active_user] = _override_current_user
    return {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": csrf_token,
    }


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
