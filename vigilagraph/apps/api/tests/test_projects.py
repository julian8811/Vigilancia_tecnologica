"""Project CRUD endpoint tests — create, list, get, update, delete, and org boundaries."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict[str, str]):
    """A user can create a project → 201."""
    resp = await client.post("/api/v1/projects", json={
        "name": "My Project",
        "topic": "biological control",
        "description": "A test project",
        "surveillance_type": "technological",
        "language": "en",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "My Project"
    assert data["topic"] == "biological control"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_project_no_org(client: AsyncClient):
    """User without org cannot create a project → 403."""
    resp = await client.post("/api/v1/projects", json={
        "name": "Orphan",
        "topic": "test",
        "surveillance_type": "technological",
        "language": "en",
    })
    assert resp.status_code == 401, resp.text  # no token at all


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers: dict[str, str]):
    """List projects returns paginated results."""
    # Create two projects
    await client.post("/api/v1/projects", json={
        "name": "Project A", "topic": "t1", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    await client.post("/api/v1/projects", json={
        "name": "Project B", "topic": "t2", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)

    resp = await client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Get a single project by ID."""
    created = await client.post("/api/v1/projects", json={
        "name": "Specific", "topic": "t", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    resp = await client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Specific"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers: dict[str, str]):
    """Non-existent project → 404."""
    import uuid
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Update project name/topic."""
    created = await client.post("/api/v1/projects", json={
        "name": "Old Name", "topic": "old", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    resp = await client.patch(f"/api/v1/projects/{pid}", json={
        "name": "New Name", "topic": "new topic",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "New Name"
    assert resp.json()["topic"] == "new topic"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Delete project → 200."""
    created = await client.post("/api/v1/projects", json={
        "name": "Delete Me", "topic": "t", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    # Verify gone
    get_resp = await client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Duplicate creates a copy with different name."""
    created = await client.post("/api/v1/projects", json={
        "name": "Original", "topic": "bio", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    resp = await client.post(f"/api/v1/projects/{pid}/duplicate", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    # Name should differ (service appends " (copy)" or similar)
    assert resp.json()["name"] != "Original"


@pytest.mark.asyncio
async def test_archive_project(client: AsyncClient, auth_headers: dict[str, str]):
    """Archive transitions status to archived."""
    created = await client.post("/api/v1/projects", json={
        "name": "Archive Me", "topic": "t", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    resp = await client.post(f"/api/v1/projects/{pid}/archive", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_project_status_transition(client: AsyncClient, auth_headers: dict[str, str]):
    """Status machine allows valid transitions."""
    created = await client.post("/api/v1/projects", json={
        "name": "Status Test", "topic": "t", "surveillance_type": "technological", "language": "en",
    }, headers=auth_headers)
    pid = created.json()["id"]

    # draft → failed (no special side-effects)
    resp = await client.post(f"/api/v1/projects/{pid}/status", json={
        "status": "failed",
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_project_org_boundary(client: AsyncClient):
    """Users from different orgs cannot see each other's projects."""
    import uuid

    # User A creates project
    headers_a = await _register_user(client, "org-a@example.com", "OrgA")
    created = await client.post("/api/v1/projects", json={
        "name": "Secret A", "topic": "t", "surveillance_type": "technological", "language": "en",
    }, headers=headers_a)
    pid = created.json()["id"]

    # User B cannot access it
    headers_b = await _register_user(client, "org-b@example.com", "OrgB")
    resp = await client.get(f"/api/v1/projects/{pid}", headers=headers_b)
    assert resp.status_code == 404, resp.text


async def _register_user(client: AsyncClient, email: str, org_name: str) -> dict[str, str]:
    """Helper: register and return auth headers."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "name": "Test",
        "password": "testpass",
        "organization_name": org_name,
    })
    assert resp.status_code == 201, resp.text
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass",
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
