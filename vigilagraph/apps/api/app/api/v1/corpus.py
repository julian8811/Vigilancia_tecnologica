"""Corpus router — corpus management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.corpus import CorpusEntry, CorpusSummary
from app.services.corpus_service import CorpusService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/corpus", tags=["corpus"])


def _ensure_org(current_user: User) -> None:
    if current_user.organization_id is None:
        raise HTTPException(status_code=403, detail="User does not belong to an organisation")


def _get_service(db: AsyncSession) -> CorpusService:
    return CorpusService(db)


@router.get("/summary", response_model=CorpusSummary)
async def corpus_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CorpusSummary:
    """Return a summary of the current corpus state for a project."""
    _ensure_org(current_user)
    service = _get_service(db)
    return await service.summary(project_id, current_user.organization_id)


@router.post("/rebuild", response_model=CorpusSummary)
async def corpus_rebuild(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CorpusSummary:
    """Rebuild the corpus folder from extracted documents."""
    _ensure_org(current_user)
    service = _get_service(db)
    return await service.rebuild(project_id, current_user.organization_id)


@router.get("/ready", response_model=bool)
async def corpus_ready(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Check if the corpus is ready for graph processing."""
    _ensure_org(current_user)
    service = _get_service(db)
    return await service.ready(project_id, current_user.organization_id)


@router.post("/seed-test-docs", response_model=list[CorpusEntry])
async def seed_test_docs(
    project_id: uuid.UUID,
    count: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[CorpusEntry]:
    """Seed the corpus with test documents (development only)."""
    _ensure_org(current_user)
    service = _get_service(db)
    return await service.seed_test_docs(project_id, current_user.organization_id, count=count)
