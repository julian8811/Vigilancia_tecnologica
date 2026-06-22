"""Graph schemas — request/response for Graphify runs, nodes, and edges."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GraphRunResponse(BaseModel):
    """Graphify execution run read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    graphify_version: str | None = None
    input_corpus_path: str | None = None
    output_path: str | None = None
    graph_json_path: str | None = None
    graph_html_path: str | None = None
    graph_report_path: str | None = None
    node_count: int | None = None
    edge_count: int | None = None
    community_count: int | None = None
    stats: dict | None = None
    created_at: datetime


class GraphRunListResponse(BaseModel):
    """Paginated graph-run list wrapper."""
    items: list[GraphRunResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GraphNodeResponse(BaseModel):
    """Graph node read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    external_node_id: str
    label: str
    node_type: str | None = None
    community_id: int | None = None
    centrality_score: float | None = None
    metadata_json: dict | None = None


class GraphNodeListResponse(BaseModel):
    """Paginated graph-node list wrapper."""
    items: list[GraphNodeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GraphEdgeResponse(BaseModel):
    """Graph edge read model."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str | None = None
    weight: float | None = None
    metadata_json: dict | None = None


class GraphEdgeListResponse(BaseModel):
    """Paginated graph-edge list wrapper."""
    items: list[GraphEdgeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GraphQueryRequest(BaseModel):
    """Parameters for querying the knowledge graph."""
    search: str | None = Field(None, description="Free-text search against node labels")
    node_types: list[str] | None = Field(None, description="Filter by node type(s): technology, paper, author, ...")
    min_centrality: float | None = Field(None, description="Minimum centrality score filter")
    community_id: int | None = None
    limit: int = 50


class GraphQueryResponse(BaseModel):
    """Graph query results."""
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


class GraphGenerateResponse(BaseModel):
    """Response returned after triggering graph generation."""
    message: str
    run_id: uuid.UUID
    status: str
