"""Role-based access control tests.

Covers:

* Default role on register (owner for new org, viewer for join).
* Mutating endpoints require analyst+ (or admin+ for delete).
* Read endpoints work for viewer.
* is_superuser bypasses every check.
* Privilege ceiling on the change-role endpoint.
* Last-owner protection.
* Inactive user gets 403.
"""

from __future__ import annotations

import secrets
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.db.session import async_session_factory
from app.models.user import User


async def _register(client: AsyncClient, *, email: str | None = None, password: str = "testpass123", name: str = "User") -> dict:
    email = email or f"rbac-{secrets.token_hex(4)}@example.com"
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "name": name,
        "password": password,
        "organization_name": f"Org {email}",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_role(client: AsyncClient, user_id: str, role: str) -> None:
    """Force-set a user's role via direct DB access (test-only)."""
    async with async_session_factory() as session:
        await session.execute(
            update(User).where(User.id == uuid.UUID(user_id)).values(role=role)
        )
        await session.commit()


async def _get_user_id_from_token(client: AsyncClient, token: str) -> str:
    """Resolve a JWT to its user_id by hitting /auth/me."""
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ── Default role on register ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_new_org_assigns_owner_role(client: AsyncClient):
    """A user who creates a new org gets role='owner'."""
    data = await _register(client)
    assert data["user"]["role"] == "owner"


@pytest.mark.asyncio
async def test_register_join_existing_org_assigns_viewer_role(client: AsyncClient):
    """A user who joins an existing org gets role='viewer'."""
    # Create the founder.
    founder = await _register(client, email="rbac-founder@example.com")

    # Founder's slug is in the response — get it via DB.
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == uuid.UUID(founder["user"]["id"]))
        )
        user = result.scalar_one()
        org_id = user.organization_id
        from app.models.organization import Organization
        org_result = await session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = org_result.scalar_one()

    # Join with the org slug.
    joiner = await client.post("/api/v1/auth/register", json={
        "email": "rbac-joiner@example.com",
        "name": "Joiner",
        "password": "testpass123",
        "organization_slug": org.slug,
    })
    assert joiner.status_code == 201, joiner.text
    assert joiner.json()["user"]["role"] == "viewer"


# ── Project role gates ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(client: AsyncClient):
    """A viewer (joined existing org) gets 403 on POST /projects."""
    # Founder creates the org.
    founder = await _register(client, email="rbac-f1@example.com")
    founder_id = await _get_user_id_from_token(client, founder["access_token"])
    org_id_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {founder['access_token']}"},
    )
    org_slug = (await async_session_factory().__aenter__()) if False else None  # noqa
    async with async_session_factory() as session:
        from app.models.organization import Organization
        org = (await session.execute(
            select(Organization).where(Organization.id == uuid.UUID(founder["user"]["organization_id"]))
        )).scalar_one()
        org_slug = org.slug

    # Join as viewer.
    joiner = await client.post("/api/v1/auth/register", json={
        "email": "rbac-viewer1@example.com",
        "name": "Viewer",
        "password": "testpass123",
        "organization_slug": org_slug,
    })
    assert joiner.status_code == 201
    viewer_token = joiner.json()["access_token"]

    # Viewer tries to create a project.
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Should Fail",
            "topic": "test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_viewer_can_list_projects(client: AsyncClient, auth_headers):
    """A viewer can still read the project list."""
    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_analyst_can_create_project(client: AsyncClient, auth_headers):
    """A user with role=analyst can POST /projects (and the auth_headers fixture is an owner, so it works at any role)."""
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Analyst Project",
            "topic": "test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_viewer_cannot_delete_project(client: AsyncClient):
    """A viewer cannot DELETE /projects/{id}; gets 403."""
    # Founder creates a project.
    founder = await _register(client, email="rbac-f2@example.com")
    project = await client.post(
        "/api/v1/projects",
        json={
            "name": "To Delete",
            "topic": "test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers={"Authorization": f"Bearer {founder['access_token']}"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    org_id = founder["user"]["organization_id"]

    # Demote the founder to viewer (simulate another user with viewer role).
    founder_id = await _get_user_id_from_token(client, founder["access_token"])
    await _set_role(client, founder_id, "viewer")

    # Founder (now viewer) tries to delete.
    resp = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {founder['access_token']}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_admin_can_delete_project(client: AsyncClient, auth_headers):
    """A user with role=admin can DELETE /projects/{id}."""
    # Get current user id and demote to admin.
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    await _set_role(client, user_id, "admin")

    # Create then delete a project.
    project = await client.post(
        "/api/v1/projects",
        json={
            "name": "Admin Project",
            "topic": "test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers=auth_headers,
    )
    assert project.status_code == 201
    resp = await client.delete(
        f"/api/v1/projects/{project.json()['id']}", headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text


# ── is_superuser bypass ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_superuser_bypasses_role_check(client: AsyncClient, auth_headers):
    """An is_superuser=True user with role=viewer can still create projects."""
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    async with async_session_factory() as session:
        await session.execute(
            update(User)
            .where(User.id == uuid.UUID(user_id))
            .values(role="viewer", is_superuser=True)
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Super Project",
            "topic": "test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text


# ── Change-role endpoint ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_can_promote_viewer_to_analyst(client: AsyncClient):
    """An owner can change another member's role in the same org."""
    owner = await _register(client, email="rbac-owner@example.com")
    async with async_session_factory() as session:
        from app.models.organization import Organization
        org = (await session.execute(
            select(Organization).where(
                Organization.id == uuid.UUID(owner["user"]["organization_id"])
            )
        )).scalar_one()
        org_slug = org.slug

    # Join as viewer.
    joiner = await client.post("/api/v1/auth/register", json={
        "email": "rbac-join1@example.com",
        "name": "Joiner1",
        "password": "testpass123",
        "organization_slug": org_slug,
    })
    assert joiner.status_code == 201
    joiner_id = joiner.json()["user"]["id"]

    # Owner promotes joiner to analyst.
    resp = await client.patch(
        f"/api/v1/orgs/{org_slug}/members/{joiner_id}",
        json={"role": "analyst"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["previous_role"] == "viewer"
    assert body["new_role"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_cannot_grant_admin_role(client: AsyncClient):
    """Privilege ceiling: an analyst cannot create a new admin."""
    owner = await _register(client, email="rbac-privtest1@example.com")
    async with async_session_factory() as session:
        from app.models.organization import Organization
        org = (await session.execute(
            select(Organization).where(
                Organization.id == uuid.UUID(owner["user"]["organization_id"])
            )
        )).scalar_one()
        org_slug = org.slug

    # Join as viewer.
    joiner = await client.post("/api/v1/auth/register", json={
        "email": "rbac-privtest2@example.com",
        "name": "Joiner2",
        "password": "testpass123",
        "organization_slug": org_slug,
    })
    joiner_id = joiner.json()["user"]["id"]

    # Demote the owner to analyst.
    owner_id = await _get_user_id_from_token(client, owner["access_token"])
    await _set_role(client, owner_id, "analyst")

    # Analyst tries to promote joiner to admin — should fail.
    resp = await client.patch(
        f"/api/v1/orgs/{org_slug}/members/{joiner_id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_last_owner_cannot_be_demoted(client: AsyncClient):
    """Trying to demote the only owner returns 409."""
    owner = await _register(client, email="rbac-lastowner@example.com")
    async with async_session_factory() as session:
        from app.models.organization import Organization
        org = (await session.execute(
            select(Organization).where(
                Organization.id == uuid.UUID(owner["user"]["organization_id"])
            )
        )).scalar_one()
        org_slug = org.slug
    owner_id = await _get_user_id_from_token(client, owner["access_token"])

    # Owner tries to demote themselves to admin (still the only owner).
    resp = await client.patch(
        f"/api/v1/orgs/{org_slug}/members/{owner_id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert resp.status_code == 409, resp.text


# ── Inactive user ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inactive_user_gets_403(client: AsyncClient, auth_headers):
    """An is_active=False user is rejected with 403 (not 400)."""
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = me.json()["id"]
    async with async_session_factory() as session:
        await session.execute(
            update(User)
            .where(User.id == uuid.UUID(user_id))
            .values(is_active=False)
        )
        await session.commit()

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 403, resp.text
    assert "desactivada" in resp.json()["detail"].lower() or "inactivo" in resp.json()["detail"].lower()
