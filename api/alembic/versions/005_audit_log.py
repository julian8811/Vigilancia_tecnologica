"""Add audit_log table.

Revision ID: 005_audit_log
Revises: 004_report_error_message
Create Date: 2026-06-29 12:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005_audit_log"
down_revision: Union[str, None] = "004_report_error_message"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_event", "audit_log", ["event"])
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_organization_id", "audit_log", ["organization_id"])
    op.create_index("ix_audit_log_request_id", "audit_log", ["request_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_request_id", table_name="audit_log")
    op.drop_index("ix_audit_log_organization_id", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_index("ix_audit_log_event", table_name="audit_log")
    op.drop_table("audit_log")
