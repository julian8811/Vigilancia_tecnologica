"""Audit log service — append records of sensitive operations.

The service uses the REQUEST'S database session, so audit rows commit
and roll back together with the business operation. The trade-off is
that a row written for a failed operation (e.g. login_failed that
raises HTTPException) is rolled back too. We accept this because:

  * The structlog line for the failure is still emitted (and not
    rolled back) and ships to centralised log storage.
  * A separate-session design breaks SQLite test concurrency and
    adds a Postgres round-trip per audit row in production.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.models.audit_log import AuditLog

logger = get_logger(__name__)


@dataclass
class AuditContext:
    """Per-request context the audit service uses to enrich records.

    Built by ``get_audit_context`` in app.api.deps from the inbound
    Request. All fields are best-effort: an unauthenticated request
    has no actor_id, an internal call has no IP, etc.
    """

    actor_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


# Canonical event names. Use these constants everywhere instead of
# string literals so refactors and queries stay in sync.
class AuditEvent:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    REGISTER_FAILED = "register_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_CHANGE_FAILED = "password_change_failed"
    PROJECT_CREATE = "project_create"
    PROJECT_DELETE = "project_delete"
    REPORT_GENERATE = "report_generate"


class AuditService:
    """Append-only writer for the audit_log table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        event: str,
        *,
        context: AuditContext | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append one audit-log row. Never raises."""
        ctx = context or AuditContext()
        row = AuditLog(
            event=event,
            actor_id=ctx.actor_id,
            organization_id=ctx.organization_id,
            target_type=target_type,
            target_id=target_id,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
            event_metadata=metadata,
        )
        try:
            self.db.add(row)
            await self.db.flush()
        except SQLAlchemyError as exc:
            logger.warning(
                "audit_log_write_failed",
                event_name=event,
                error=str(exc),
            )
