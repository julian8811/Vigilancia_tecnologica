"""Admin router — endpoints restricted to superusers.

Currently exposes the audit-log reader. Future routes for user
management, org-level settings, and feature flags belong here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["administración"])


class AuditLogEntry(BaseModel):
    """Public shape of one audit-log row."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    event: str
    actor_id: uuid.UUID | None
    organization_id: uuid.UUID | None
    target_type: str | None
    target_id: uuid.UUID | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    event_metadata: dict | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int


async def require_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency: refuse non-superusers with 403."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    return current_user


@router.get("/audit-log", response_model=AuditLogListResponse)
async def list_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event: str | None = Query(None, description="Filter by event name, exact match"),
    actor_id: uuid.UUID | None = Query(None, description="Filter by actor user id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
) -> AuditLogListResponse:
    """List audit-log entries, newest first.

    Restricted to superusers. Once S11 (RBAC) lands, gate this on a
    real ``admin`` role check instead of ``is_superuser``.
    """
    base = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_q = select(AuditLog)

    if event:
        base = base.where(AuditLog.event == event)
        count_q = count_q.where(AuditLog.event == event)
    if actor_id:
        base = base.where(AuditLog.actor_id == actor_id)
        count_q = count_q.where(AuditLog.actor_id == actor_id)

    total = (await db.execute(count_q)).scalars().all()
    total_count = len(total)
    total_pages = max(1, (total_count + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    rows = (await db.execute(base.offset(offset).limit(page_size))).scalars().all()

    return AuditLogListResponse(
        items=[AuditLogEntry.model_validate(r) for r in rows],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
