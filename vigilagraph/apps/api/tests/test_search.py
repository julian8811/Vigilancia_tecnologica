"""Search endpoint tests — collect-from-search (bulk import) and health."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from .conftest import create_test_project


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """GET /health returns service status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_collect_from_search(client: AsyncClient, auth_headers: dict[str, str]):
    """Import search results as documents via collect-from-search."""
    project = await create_test_project(client, auth_headers)
    pid = project["id"]

    resp = await client.post(
        f"/api/v1/projects/{pid}/collect-from-search",
        json={
            "results": [
                {
                    "title": "AI for Biological Control",
                    "doi": "10.1234/ai-bio-2024",
                    "abstract": "A study on AI applications in biological pest control.",
                    "authors": ["Alice", "Bob"],
                    "url": "https://doi.org/10.1234/ai-bio-2024",
                },
                {
                    "title": "Deep Learning in Agriculture",
                    "doi": "10.5678/dl-agri-2024",
                    "abstract": "Using CNNs for crop disease detection.",
                    "authors": ["Charlie"],
                    "url": "https://doi.org/10.5678/dl-agri-2024",
                },
            ],
            "source": "openalex",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["inserted"] == 2

    # Verify documents are listed
    list_resp = await client.get(
        f"/api/v1/projects/{pid}/documents",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_collect_from_search_dedup(client: AsyncClient, auth_headers: dict[str, str]):
    """Importing the same DOI twice skips the duplicate."""
    project = await create_test_project(client, auth_headers)
    pid = project["id"]

    payload = {
        "results": [
            {
                "title": "Duplicate Study",
                "doi": "10.9999/dup-2024",
                "abstract": "Same DOI",
                "authors": ["Me"],
            },
        ],
        "source": "openalex",
    }

    first = await client.post(
        f"/api/v1/projects/{pid}/collect-from-search",
        json=payload,
        headers=auth_headers,
    )
    assert first.status_code == 201
    assert first.json()["inserted"] == 1

    second = await client.post(
        f"/api/v1/projects/{pid}/collect-from-search",
        json=payload,
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["inserted"] == 0
