"""initial_models — create all VigilaGraph core tables.

Revision ID: 001
Revises:
Create Date: 2026-06-18 10:00:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

# pgvector Vector type
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Organizations ─────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=True, comment="university | company | research_group | consultancy | government | other"),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Multi-tenant organisations",
    )

    # ── Users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_superuser", sa.Boolean(), default=False, nullable=False),
        sa.Column("role", sa.String(20), nullable=True, comment="owner | admin | analyst | viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="User accounts and authentication",
    )

    # ── Surveillance Projects ─────────────────────────────────────
    op.create_table(
        "surveillance_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, index=True),
        sa.Column("topic", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("surveillance_type", sa.String(50), nullable=True, comment="tecnologica | cientifica | competitiva | patentaria | normativa | mercado | academica | mixta"),
        sa.Column("language", sa.String(10), default="es", nullable=False),
        sa.Column("status", sa.String(20), default="draft", nullable=False, comment="draft | collecting | processing | graph_ready | report_ready | archived | failed"),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column("country_focus", sa.String(100), nullable=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Surveillance projects belonging to organisations",
    )

    # ── Search Strategies ─────────────────────────────────────────
    op.create_table(
        "search_strategies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("keywords_en", sa.Text, nullable=True),
        sa.Column("keywords_es", sa.Text, nullable=True),
        sa.Column("synonyms", sa.Text, nullable=True),
        sa.Column("excluded_terms", sa.Text, nullable=True),
        sa.Column("sources_selected", sa.String(255), nullable=True, comment="openalex | semantic_scholar | lens | web"),
        sa.Column("boolean_queries", sa.Text, nullable=True),
        sa.Column("generated_by_ai", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Keyword and source configuration per project",
    )

    # ── Documents ─────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("document_type", sa.String(30), nullable=True, comment="paper | patent | webpage | report | standard | thesis | book | dataset | manual_upload | other"),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("doi", sa.String(255), nullable=True, comment="External ID from OpenAlex / Semantic Scholar / Lens"),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("authors", postgresql.JSONB, nullable=True, comment="List of author names"),
        sa.Column("institutions", postgresql.JSONB, nullable=True),
        sa.Column("publication_year", sa.Integer, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("file_type", sa.String(20), nullable=True, comment="html | pdf | markdown | docx | json"),
        sa.Column("file_path", sa.String(500), nullable=True, comment="Path in S3 object storage"),
        sa.Column("text_path", sa.String(500), nullable=True, comment="Path to extracted text in corpus"),
        sa.Column("checksum", sa.String(64), nullable=True, comment="MD5 hash for deduplication"),
        sa.Column("processing_status", sa.String(20), default="pending", nullable=False, comment="pending | extracting | extracted | failed"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Surveillance-source documents",
    )
    op.create_index("ix_documents_project_checksum", "documents", ["project_id", "checksum"])

    # ── Document Chunks ───────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True, comment="OpenAI text-embedding-ada-002 embedding (1536 dims)"),
        comment="Text chunks with vector embeddings for semantic search",
    )
    op.create_index("ix_document_chunks_doc_idx", "document_chunks", ["document_id", "chunk_index"])

    # ── Graph Runs ────────────────────────────────────────────────
    op.create_table(
        "graph_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(20), default="pending", nullable=False, comment="pending | running | completed | failed"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("graphify_version", sa.String(50), nullable=True),
        sa.Column("input_corpus_path", sa.String(500), nullable=True),
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("graph_json_path", sa.String(500), nullable=True),
        sa.Column("graph_html_path", sa.String(500), nullable=True),
        sa.Column("graph_report_path", sa.String(500), nullable=True),
        sa.Column("node_count", sa.Integer, nullable=True),
        sa.Column("edge_count", sa.Integer, nullable=True),
        sa.Column("community_count", sa.Integer, nullable=True),
        sa.Column("stats", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Graphify execution runs for knowledge-graph generation",
    )

    # ── Graph Nodes ───────────────────────────────────────────────
    op.create_table(
        "graph_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("graph_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("external_node_id", sa.String(255), nullable=False, comment="Node ID from the Graphify graph.json output"),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=True, comment="technology | paper | author | institution | concept | ..."),
        sa.Column("community_id", sa.Integer, nullable=True),
        sa.Column("centrality_score", sa.Float, nullable=True, comment="Centrality score 0.0 - 1.0"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        comment="Nodes in the knowledge graph (from Graphify output)",
    )

    # ── Graph Edges ───────────────────────────────────────────────
    op.create_table(
        "graph_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("graph_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_node_id", UUID(as_uuid=True), sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_node_id", UUID(as_uuid=True), sa.ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("edge_type", sa.String(50), nullable=True, comment="mentions | cites | authored_by | developed_by | uses_method | related_to | ..."),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        comment="Edges (relationships) in the knowledge graph",
    )
    op.create_index("ix_graph_edges_source_target", "graph_edges", ["source_node_id", "target_node_id"])

    # ── Technologies ──────────────────────────────────────────────
    op.create_table(
        "technologies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("trl_level", sa.Integer, nullable=True, comment="Technology Readiness Level 1-9"),
        sa.Column("evidence_score", sa.Float, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Identified technologies from the surveillance corpus",
    )
    op.create_index("ix_technologies_project_id", "technologies", ["project_id"])

    # ── Trends ────────────────────────────────────────────────────
    op.create_table(
        "trends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("momentum", sa.String(20), nullable=True, comment="emerging | growing | stable | declining | uncertain"),
        sa.Column("trend_type", sa.String(100), nullable=True),
        sa.Column("growth_signal", sa.String(50), nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Detected technology trends from the surveillance corpus",
    )
    op.create_index("ix_trends_project_id", "trends", ["project_id"])

    # ── Actors ────────────────────────────────────────────────────
    op.create_table(
        "actors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=True, comment="author | institution | company | government | research_group | startup | ngo | funder"),
        sa.Column("relevance", sa.Float, nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Key actors identified in the surveillance corpus",
    )
    op.create_index("ix_actors_project_id", "actors", ["project_id"])

    # ── Opportunities ─────────────────────────────────────────────
    op.create_table(
        "opportunities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("opportunity_type", sa.String(50), nullable=True, comment="research | commercial | technology_transfer | patent | funding | partnership | product_development | education | policy"),
        sa.Column("potential", sa.String(20), nullable=True, comment="high | medium | low"),
        sa.Column("effort", sa.String(20), nullable=True, comment="high | medium | low"),
        sa.Column("priority", sa.String(10), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("related_documents", postgresql.JSONB, nullable=True, default=list, comment="UUIDs of related Document records"),
        sa.Column("related_nodes", postgresql.JSONB, nullable=True, default=list, comment="UUIDs of related GraphNode records"),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="Identified opportunities from the surveillance corpus",
    )
    op.create_index("ix_opportunities_project_id", "opportunities", ["project_id"])

    # ── Reports ───────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=True, comment="completo | ejecutivo | academico | empresarial | patentario | comparativo"),
        sa.Column("status", sa.String(20), default="pending", nullable=False, comment="pending | generating | completed | failed"),
        sa.Column("format", sa.String(10), default="html", nullable=False, comment="html | pdf | markdown | docx | json"),
        sa.Column("content", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("html_path", sa.String(500), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("markdown_path", sa.String(500), nullable=True),
        sa.Column("docx_path", sa.String(500), nullable=True),
        sa.Column("json_path", sa.String(500), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="AI-generated analysis reports",
    )
    op.create_index("ix_reports_project_id", "reports", ["project_id"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("reports")
    op.drop_table("opportunities")
    op.drop_table("actors")
    op.drop_table("trends")
    op.drop_table("technologies")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("graph_runs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("search_strategies")
    op.drop_table("surveillance_projects")
    op.drop_table("users")
    op.drop_table("organizations")
