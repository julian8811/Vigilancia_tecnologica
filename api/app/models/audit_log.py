"""Audit log model — append-only record of sensitive operations.

Every authentication, password change, project mutation, and report
generation is recorded here for compliance and incident response. The
table is intentionally append-only; rows are never updated or
deleted by application code. Retention policy is the operator's
responsibility (cron `DELETE FROM audit_log WHERE created_at < ...`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    # e.g. "login_success", "login_failed", "password_change",
    # "project_create", "project_delete", "report_generate"
    event: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Nullable: a login_failed for an unknown email has no actor.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # The org the actor acted in. Useful for org-scoped queries.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # Optional reference to the object the event acted on.
    # e.g. ("project", "<uuid>") for project_create.
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    # Request metadata for correlation with logs and access logs.
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Free-form structured payload. NEVER put passwords, tokens, or
    # other secrets here. Common fields: {"email": "..."},
    # {"reason": "wrong_password"}, {"project_name": "..."}.
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # column name kept as `metadata` for SQL friendliness
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.event} actor={self.actor_id} target={self.target_type}:{self.target_id}>"
