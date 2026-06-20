"""collection_runs — add source_name to documents, create collection_runs table.

Revision ID: 002
Revises: 001
Create Date: 2026-06-20 01:30:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # ── Document column ────────────────────────────────────────────
    op.add_column(
        "documents",
        sa.Column(
            "source_name",
            sa.String(50),
            server_default="manual_upload",
            nullable=False,
            comment="manual_upload | openalex | semantic_scholar | lens | web",
        ),
    )
    op.create_index(
        "ix_documents_source_lookup",
        "documents",
        ["project_id", "source_name", "source_id"],
    )

    # ── Collection runs table ──────────────────────────────────────
    op.create_table(
        "collection_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("surveillance_projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_name", sa.String(50), nullable=False, comment="openalex | semantic_scholar | lens | web"),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False, comment="pending | running | completed | failed"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("docs_found", sa.Integer, server_default="0", nullable=False, comment="Total documents returned by the source"),
        sa.Column("docs_inserted", sa.Integer, server_default="0", nullable=False, comment="Documents actually inserted (after dedup)"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        comment="External source collection runs per project",
    )


def downgrade() -> None:
    op.drop_table("collection_runs")
    op.drop_index("ix_documents_source_lookup", table_name="documents")
    op.drop_column("documents", "source_name")
