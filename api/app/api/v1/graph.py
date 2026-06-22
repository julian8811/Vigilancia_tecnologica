"""Graph router — Graphify knowledge-graph endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, verify_project_org
from app.models.user import User
from app.schemas.graph import (
    GraphEdgeListResponse,
    GraphEdgeResponse,
    GraphGenerateResponse,
    GraphNodeListResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphRunListResponse,
    GraphRunResponse,
)
from app.services.graph_service import GraphService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/graph", tags=["graph"])


def _get_service(db: AsyncSession) -> GraphService:
    return GraphService(db)


@router.post("/generate", response_model=GraphGenerateResponse)
async def generate_graph(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphGenerateResponse:
    """Trigger knowledge-graph generation via Graphify.

    MVP: runs synchronously via subprocess.
    """
    service = _get_service(db)
    return await service.generate(project_id, current_user.organization_id)


@router.get("/latest", response_model=GraphRunResponse | None)
async def latest_graph(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphRunResponse | None:
    """Return the most recent completed graph run."""
    service = _get_service(db)
    return await service.get_latest(project_id, current_user.organization_id)


@router.get("/runs", response_model=GraphRunListResponse)
async def list_runs(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphRunListResponse:
    """List historical graph runs for a project."""
    service = _get_service(db)
    return await service.list_runs(project_id, current_user.organization_id, page=page, page_size=page_size)


@router.get("/runs/{run_id}/nodes", response_model=GraphNodeListResponse)
async def list_nodes(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    node_type: str | None = Query(None, description="Filter by node type"),
    search: str | None = Query(None, description="Free-text search against labels"),
    min_centrality: float | None = Query(None, description="Minimum centrality score"),
    community_id: int | None = Query(None, description="Filter by community"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphNodeListResponse:
    """List graph nodes for a run, with optional filters."""
    service = _get_service(db)
    return await service.list_nodes(
        run_id, current_user.organization_id,
        page=page, page_size=page_size,
        node_type=node_type, search=search,
        min_centrality=min_centrality, community_id=community_id,
    )


@router.get("/runs/{run_id}/nodes/top", response_model=GraphNodeListResponse)
async def top_nodes(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    node_type: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphNodeListResponse:
    """Return the top N nodes by centrality score."""
    service = _get_service(db)
    return await service.list_nodes(
        run_id, current_user.organization_id,
        page=1, page_size=limit,
        node_type=node_type,
    )


@router.get("/runs/{run_id}/edges", response_model=GraphEdgeListResponse)
async def list_edges(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    edge_type: str | None = Query(None, description="Filter by edge type"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphEdgeListResponse:
    """List graph edges for a run."""
    service = _get_service(db)
    return await service.list_edges(
        run_id, current_user.organization_id,
        page=page, page_size=page_size, edge_type=edge_type,
    )


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(
    project_id: uuid.UUID,
    query: GraphQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> GraphQueryResponse:
    """Query the knowledge graph with filters."""
    service = _get_service(db)

    # Use the latest run if no run_id specified
    latest = await service.get_latest(project_id, current_user.organization_id)
    if latest is None:
        return GraphQueryResponse()

    return await service.query_graph(latest.id, current_user.organization_id, query)


@router.get("/paths")
async def find_paths(
    project_id: uuid.UUID,
    source: uuid.UUID = Query(..., description="Source node ID"),
    target: uuid.UUID = Query(..., description="Target node ID"),
    max_depth: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> list[GraphEdgeResponse]:
    """Find the shortest path between two nodes in the graph."""
    service = _get_service(db)

    latest = await service.get_latest(project_id, current_user.organization_id)
    if latest is None:
        return []

    return await service.find_path(latest.id, current_user.organization_id, source, target, max_depth)


# ── Raw file downloads (no JSON wrapper) ──────────────────────────


@router.get("/download-json")
async def download_graph_json(
    project_id: uuid.UUID,
    run_id: uuid.UUID = Query(..., description="Graph run ID"),
    _: User = Depends(verify_project_org),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the raw graph.json for a completed run."""
    service = _get_service(db)
    run = await service.get_run(run_id)
    if not run.graph_json_path:
        raise HTTPException(status_code=404, detail="No graph JSON file for this run")
    try:
        content = Path(run.graph_json_path).read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Graph JSON file not found on disk")
    return Response(content=content, media_type="application/json")


@router.get("/html")
async def get_graph_html(
    project_id: uuid.UUID,
    run_id: uuid.UUID = Query(..., description="Graph run ID"),
    _: User = Depends(verify_project_org),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Return the raw graph.html for a completed run."""
    service = _get_service(db)
    run = await service.get_run(run_id)
    if not run.graph_html_path:
        raise HTTPException(status_code=404, detail="No graph HTML file for this run")
    try:
        content = Path(run.graph_html_path).read_bytes()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Graph HTML file not found on disk")
    return Response(content=content, media_type="text/html")
