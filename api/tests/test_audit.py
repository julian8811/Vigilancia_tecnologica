"""Audit-log tests — register, login, and admin endpoint."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.db.session import async_session_factory
from app.models.user import User


async def _login_and_promote(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """Log in as a user, promote them to superuser, and return headers.

    The auth endpoint delivers the access token via the httpOnly
    ``vg_access`` cookie (NOT in the response body — the body only
    carries the user profile). We read the token from
    ``resp.cookies`` so the next request can use the
    ``Authorization: Bearer <token>`` header.

    The promotion happens in the DB AFTER login. The next request
    re-reads the user from the DB inside ``require_superuser`` and
    sees ``is_superuser=True`` — the JWT itself does not need to be
    re-issued.
    """
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.cookies.get("vg_access")
    assert token, "vg_access cookie missing from login response"

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_superuser = True
        await session.commit()

    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_records_audit_event(client: AsyncClient):
    """A successful registration appends a 'register' row to audit_log."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "audit-reg@example.com",
        "name": "Audit Reg",
        "password": "secure123",
        "organization_name": "Audit Org",
    })
    assert resp.status_code == 201, resp.text

    # Register a separate superuser and read the log.
    su_resp = await client.post("/api/v1/auth/register", json={
        "email": "audit-su@example.com",
        "name": "Audit SU",
        "password": "secure123",
        "organization_name": "SU Org",
    })
    assert su_resp.status_code == 201

    su_headers = await _login_and_promote(client, "audit-su@example.com", "secure123")

    log = await client.get(
        "/api/v1/admin/audit-log?event=register", headers=su_headers,
    )
    assert log.status_code == 200, log.text
    data = log.json()
    assert data["total"] >= 1
    assert any(item["event"] == "register" for item in data["items"])


@pytest.mark.asyncio
async def test_login_success_records_audit_event(client: AsyncClient):
    """A successful login appends a 'login_success' row to audit_log."""
    await client.post("/api/v1/auth/register", json={
        "email": "audit-login@example.com",
        "name": "Audit Login",
        "password": "secure123",
        "organization_name": "Login Org",
    })

    # Now log in successfully and check the audit log.
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "audit-login@example.com", "password": "secure123"},
    )
    assert resp.status_code == 200

    headers = await _login_and_promote(client, "audit-login@example.com", "secure123")
    log = await client.get(
        "/api/v1/admin/audit-log?event=login_success", headers=headers,
    )
    assert log.status_code == 200, log.text
    rows = log.json()["items"]
    assert len(rows) >= 1
    # The metadata should include the email.
    assert any(
        row.get("event_metadata", {}).get("email") == "audit-login@example.com"
        for row in rows
    )


@pytest.mark.asyncio
async def test_admin_audit_log_requires_superuser(client: AsyncClient, auth_headers):
    """A non-superuser calling /admin/audit-log gets 403."""
    resp = await client.get("/api/v1/admin/audit-log", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_audit_log_unauthenticated(client: AsyncClient):
    """An anonymous request to /admin/audit-log gets 401."""
    resp = await client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_audit_log_pagination(client: AsyncClient):
    """The endpoint paginates and reports total + total_pages."""
    # Register three users to produce three register audit rows.
    for i in range(3):
        await client.post("/api/v1/auth/register", json={
            "email": f"audit-page-{i}@example.com",
            "name": f"Page {i}",
            "password": "secure123",
            "organization_name": f"Page Org {i}",
        })

    headers = await _login_and_promote(
        client, "audit-page-0@example.com", "secure123",
    )

    resp = await client.get(
        "/api/v1/admin/audit-log?event=register&page=1&page_size=2", headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page_size"] == 2
    assert data["page"] == 1
    assert data["total"] >= 3
    assert data["total_pages"] >= 2
    assert len(data["items"]) == 2
