"""Audit log service — append records of sensitive operations.

The service uses its OWN database session (not the request's) so that
audit rows are persisted even when the parent business operation
rolls back. The trade-off is one extra Postgres connection per audit
event, which is acceptable for the volume this app will see.

The service never raises. Audit logging is best-effort: if the
underlying database write fails, we log the error at warning level
and let the business operation continue.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from structlog import get_logger

from app.db.session import async_session_factory
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
    """Append-only writer for the audit_log table.

    Each ``record()`` call opens its own session and commits
    immediately, decoupling the audit row from the request's
    transaction. Use a single instance for the lifetime of the app
    (or instantiate per-request — it has no state).
    """

    async def record(
        self,
        event: str,
        *,
        context: AuditContext | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist one audit-log row. Never raises."""
        ctx = context or AuditContext()
        try:
            async with async_session_factory() as session:
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
                session.add(row)
                await session.commit()
        except SQLAlchemyError as exc:
            logger.warning(
                "audit_log_write_failed",
                event=event,
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "audit_log_unexpected_error",
                event=event,
                error=str(exc),
            )
