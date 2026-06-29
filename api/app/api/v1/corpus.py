"""Corpus router — corpus management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, require_min_role, verify_project_org
from app.core.permissions import Role
from app.models.user import User
from app.schemas.corpus import CorpusEntry, CorpusSummary
from app.services.corpus_service import CorpusService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}/corpus", tags=["corpus"])


# Mutating endpoints (POST) gate on ``analyst``+; reads stay open
# to every authenticated user. Mirrors the pattern in projects.py,
# reports.py, and the rest of the mutating routers.
_require_analyst = require_min_role(Role.ANALYST)


def _get_service(db: AsyncSession) -> CorpusService:
    return CorpusService(db)


@router.get("/summary", response_model=CorpusSummary)
async def corpus_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> CorpusSummary:
    """Return a summary of the current corpus state for a project."""
    service = _get_service(db)
    return await service.summary(project_id, current_user.organization_id)


@router.post("/rebuild", response_model=CorpusSummary)
async def corpus_rebuild(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> CorpusSummary:
    """Rebuild the corpus folder from extracted documents."""
    service = _get_service(db)
    return await service.rebuild(project_id, current_user.organization_id)


@router.get("/ready", response_model=bool)
async def corpus_ready(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> bool:
    """Check if the corpus is ready for graph processing."""
    service = _get_service(db)
    return await service.ready(project_id, current_user.organization_id)


@router.post("/seed-test-docs", response_model=list[CorpusEntry])
async def seed_test_docs(
    project_id: uuid.UUID,
    count: int = Query(3, ge=1, le=10),
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> list[CorpusEntry]:
    """Seed the corpus with test documents (development only)."""
    service = _get_service(db)
    return await service.seed_test_docs(project_id, current_user.organization_id, count=count)
