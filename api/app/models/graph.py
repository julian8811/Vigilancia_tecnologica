"""Graph models — Graphify knowledge-graph runs, nodes, and edges."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime,  Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GraphRun(Base):
    __tablename__ = "graph_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False,
        comment="pending | running | completed | failed",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    graphify_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_corpus_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    graph_json_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    graph_html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    graph_report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    node_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edge_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    community_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped["SurveillanceProject"] = relationship(
        "SurveillanceProject", back_populates="graph_runs", lazy="selectin",
    )
    nodes: Mapped[list["GraphNode"]] = relationship(
        "GraphNode", back_populates="run", cascade="all, delete-orphan", lazy="selectin",
    )
    edges: Mapped[list["GraphEdge"]] = relationship(
        "GraphEdge", back_populates="run", cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<GraphRun {self.id!r} status={self.status!r}>"


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_runs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    external_node_id: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Node ID from the Graphify graph.json output",
    )
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    node_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="technology | paper | author | institution | concept | ...",
    )
    community_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    centrality_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Centrality score 0.0 - 1.0",
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # ── Relationships ─────────────────────────────────────────────
    run: Mapped["GraphRun"] = relationship("GraphRun", back_populates="nodes", lazy="selectin")

    def __repr__(self) -> str:
        return f"<GraphNode {self.external_node_id!r} type={self.node_type!r}>"


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_runs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    edge_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="mentions | cites | authored_by | developed_by | uses_method | related_to | ...",
    )
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # ── Relationships ─────────────────────────────────────────────
    run: Mapped["GraphRun"] = relationship("GraphRun", back_populates="edges", lazy="selectin")

    def __repr__(self) -> str:
        return f"<GraphEdge {self.source_node_id!r} -> {self.target_node_id!r}>"
