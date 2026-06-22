"""Auth endpoint tests — register, login, token validation, and org creation."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    """A user can register with valid data → 201 + user + token."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "name": "New User",
        "password": "secure123",
        "organization_name": "New Org",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["name"] == "New User"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with an existing email → 409."""
    await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "name": "First",
        "password": "secure123",
        "organization_name": "Org A",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "name": "Second",
        "password": "secure123",
        "organization_name": "Org B",
    })
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_login_success(client):
    """A registered user can login → 200 + access_token."""
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "name": "Login User",
        "password": "thepassword",
        "organization_name": "Login Org",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "thepassword",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Wrong password → 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpw@example.com",
        "name": "Test",
        "password": "correct",
        "organization_name": "Org",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "incorrect",
    })
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Non-existent email → 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "anything",
    })
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_auth_me(client, auth_headers):
    """GET /auth/me returns the current user profile."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "email" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_auth_me_no_token(client):
    """GET /auth/me without token → 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_change_password(client, auth_headers):
    """Authenticated user can change their password."""
    resp = await client.post("/api/v1/auth/change-password", json={
        "old_password": "testpass123",
        "new_password": "newpass456",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, auth_headers):
    """Wrong current password → 400."""
    resp = await client.post("/api/v1/auth/change-password", json={
        "old_password": "wrong",
        "new_password": "newpass456",
    }, headers=auth_headers)
    assert resp.status_code == 400, resp.text
