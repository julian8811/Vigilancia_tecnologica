"""Corpus router RBAC tests.

Verifies the Phase 4 hardening:

* POST /corpus/rebuild and POST /corpus/seed-test-docs require
  ``analyst``+ (i.e. ``viewer`` is denied with 403).
* GET /corpus/summary and GET /corpus/ready remain open to every
  authenticated user, including ``viewer`` (read-only).
* An ``owner`` (rank 30 ≥ analyst 10) can call the mutating endpoints.

The viewer is injected via ``app.dependency_overrides`` so the test
does not need to spin up a second user through the register endpoint
(which would clash with the cookie-isolation in the
``auth_headers`` fixture).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_active_user
from app.main import app as fastapi_app
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_owner(client: AsyncClient) -> dict:
    """Register a fresh owner user via the public API and return a dict
    with the parsed response, the bearer token, and the org id.

    Returns a dict with keys: ``user_id``, ``org_id``, ``headers``.
    """
    import secrets

    email = f"corpus-{secrets.token_hex(4)}@example.com"
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "name": "Corpus Owner",
        "password": "testpass123",
        "organization_name": f"Corpus Org {email}",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    return {
        "user_id": data["user"]["id"],
        "org_id": data["user"]["organization_id"],
        "headers": {"Authorization": f"Bearer {resp.cookies.get('vg_access')}"},
    }


async def _create_project(client: AsyncClient, headers: dict[str, str]) -> dict:
    """Create a project as the owner and return its id + org id."""
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Corpus Test Project",
            "topic": "rbac corpus test",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Project create failed: {resp.text}"
    body = resp.json()
    return {"id": body["id"], "organization_id": body["organization_id"]}


def _build_viewer_user(*, org_id: uuid.UUID) -> User:
    """Return an in-memory ``User`` with role=viewer and the given org.

    Used as the return value of an overridden dependency so the route
    sees an authenticated viewer without going through the DB.
    """
    now = None  # server-defaulted; SQLAlchemy fills it on flush, but we
                 # never persist this instance, so the value is irrelevant.
    return User(
        id=uuid.uuid4(),
        email=f"viewer-{uuid.uuid4().hex}@example.com",
        name="Test Viewer",
        password_hash="x",  # never used
        organization_id=org_id,
        is_active=True,
        is_superuser=False,
        role="viewer",
        created_at=now,
        updated_at=now,
    )


def _override_current_user_with_viewer(org_id: uuid.UUID) -> None:
    """Install a viewer override on ``get_current_active_user``.

    Subsequent requests in this test will see an authenticated viewer
    bound to ``org_id``. The override is cleared by the ``client``
    fixture's teardown, but we also clear it explicitly to be safe
    when tests are reordered.
    """

    async def _viewer_dep() -> User:
        return _build_viewer_user(org_id=org_id)

    # Replace whatever the auth_headers fixture installed.
    fastapi_app.dependency_overrides[get_current_active_user] = _viewer_dep


def _clear_user_override() -> None:
    """Drop the ``get_current_active_user`` override so the next test
    starts from the fixture's default state."""
    fastapi_app.dependency_overrides.pop(get_current_active_user, None)


# ---------------------------------------------------------------------------
# Mutating endpoints require analyst+
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corpus_rebuild_requires_analyst(client: AsyncClient):
    """POST /corpus/rebuild as viewer must be 403.

    The owner registers and creates a project; the dependency is then
    swapped to a viewer. Without the RBAC gate, the endpoint would
    happily run the rebuild — this test must fail before the gate is
    added and pass after.
    """
    owner = await _register_owner(client)
    project = await _create_project(client, owner["headers"])
    _override_current_user_with_viewer(org_id=uuid.UUID(project["organization_id"]))
    try:
        resp = await client.post(
            f"/api/v1/projects/{project['id']}/corpus/rebuild",
            headers={"Authorization": "Bearer dummy"},
        )
    finally:
        _clear_user_override()

    assert resp.status_code == 403, (
        f"viewer should be forbidden from /corpus/rebuild, "
        f"got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_corpus_seed_requires_analyst(client: AsyncClient):
    """POST /corpus/seed-test-docs as viewer must be 403.

    Same pattern as the rebuild test. The endpoint must short-circuit
    on the RBAC check before hitting the development-only guard in
    ``CorpusService.seed_test_docs``.
    """
    owner = await _register_owner(client)
    project = await _create_project(client, owner["headers"])
    _override_current_user_with_viewer(org_id=uuid.UUID(project["organization_id"]))
    try:
        resp = await client.post(
            f"/api/v1/projects/{project['id']}/corpus/seed-test-docs?count=1",
            headers={"Authorization": "Bearer dummy"},
        )
    finally:
        _clear_user_override()

    assert resp.status_code == 403, (
        f"viewer should be forbidden from /corpus/seed-test-docs, "
        f"got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Owner (rank 30) passes the analyst gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corpus_rebuild_allows_owner(client: AsyncClient, auth_headers: dict[str, str]):
    """POST /corpus/rebuild as owner (rank 30) succeeds.

    The endpoint is allowed because owner ≥ analyst. With no documents
    extracted, the rebuild is a no-op but still returns 200 with a
    valid ``CorpusSummary`` (total_documents=0, corpus_ready=False).
    """
    # Use the auth_headers fixture (an owner) to create a project.
    project = await _create_project(client, auth_headers)

    resp = await client.post(
        f"/api/v1/projects/{project['id']}/corpus/rebuild",
        headers=auth_headers,
    )
    assert resp.status_code == 200, (
        f"owner should be allowed to call /corpus/rebuild, "
        f"got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["project_id"] == project["id"]
    assert body["total_documents"] == 0
    assert body["corpus_ready"] is False


# ---------------------------------------------------------------------------
# Read-only endpoints stay open to viewer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corpus_summary_and_ready_readonly(client: AsyncClient):
    """GET /corpus/summary and GET /corpus/ready remain open to viewer.

    The route still uses ``get_current_active_user`` (not
    ``_require_analyst``), so a viewer passes authentication. The
    dependency is swapped to a viewer bound to the owner's org so
    ``verify_project_org`` also passes.
    """
    owner = await _register_owner(client)
    project = await _create_project(client, owner["headers"])
    _override_current_user_with_viewer(org_id=uuid.UUID(project["organization_id"]))
    try:
        summary = await client.get(
            f"/api/v1/projects/{project['id']}/corpus/summary",
            headers={"Authorization": "Bearer dummy"},
        )
        ready = await client.get(
            f"/api/v1/projects/{project['id']}/corpus/ready",
            headers={"Authorization": "Bearer dummy"},
        )
    finally:
        _clear_user_override()

    assert summary.status_code == 200, (
        f"viewer should be allowed to read /corpus/summary, "
        f"got {summary.status_code}: {summary.text}"
    )
    assert ready.status_code == 200, (
        f"viewer should be allowed to read /corpus/ready, "
        f"got {ready.status_code}: {ready.text}"
    )
    # Body shape sanity check — we don't assert the values, just that
    # the endpoint returned a real CorpusSummary.
    summary_body = summary.json()
    assert summary_body["project_id"] == project["id"]
    assert "total_documents" in summary_body
