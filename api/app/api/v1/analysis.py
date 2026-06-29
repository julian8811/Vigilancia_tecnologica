"""Analysis router — technologies, trends, actors, opportunities, and AI pipeline."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db, require_min_role, verify_project_org
from app.core.permissions import Role
from app.models.user import User
from app.repositories.analysis_repository import (
    ActorRepository,
    OpportunityRepository,
    TechnologyRepository,
    TrendRepository,
)
from app.schemas.analysis import (
    ActorListResponse,
    ActorResponse,
    AnalysisRunRequest,
    AnalysisRunResponse,
    OpportunityListResponse,
    OpportunityResponse,
    TechnologyListResponse,
    TechnologyResponse,
    TrendListResponse,
    TrendResponse,
)
from app.services.analysis_service import AnalysisService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects/{project_id}", tags=["análisis"])


# ── Run Analysis Pipeline ────────────────────────────────────

@router.post("/analysis/run", response_model=AnalysisRunResponse)
async def run_analysis(
    project_id: uuid.UUID,
    request: AnalysisRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_analyst),
    _: User = Depends(verify_project_org),
) -> AnalysisRunResponse:
    """Run the full AI analysis pipeline. Analyst+."""
    service = AnalysisService(db)
    result = await service.run_full_analysis(project_id, request)
    return result


# ── Technologies ─────────────────────────────────────────────

@router.get("/technologies", response_model=TechnologyListResponse)
async def list_technologies(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> TechnologyListResponse:
    repo = TechnologyRepository(db)
    items, total = await repo.list_by_project(project_id, page=page, page_size=page_size, category=category)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return TechnologyListResponse(
        items=[TechnologyResponse.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# ── Trends ──────────────────────────────────────────────────

@router.get("/trends", response_model=TrendListResponse)
async def list_trends(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    trend_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> TrendListResponse:
    repo = TrendRepository(db)
    items, total = await repo.list_by_project(project_id, page=page, page_size=page_size, trend_type=trend_type)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return TrendListResponse(
        items=[TrendResponse.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# ── Actors ──────────────────────────────────────────────────

@router.get("/actors", response_model=ActorListResponse)
async def list_actors(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> ActorListResponse:
    repo = ActorRepository(db)
    items, total = await repo.list_by_project(project_id, page=page, page_size=page_size, actor_type=actor_type)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ActorListResponse(
        items=[ActorResponse.model_validate(a) for a in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# ── Opportunities ──────────────────────────────────────────

@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    opportunity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(verify_project_org),
) -> OpportunityListResponse:
    repo = OpportunityRepository(db)
    items, total = await repo.list_by_project(
        project_id, page=page, page_size=page_size, opportunity_type=opportunity_type,
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(o) for o in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


_require_analyst = require_min_role(Role.ANALYST)
