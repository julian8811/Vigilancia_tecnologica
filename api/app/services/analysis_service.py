"""Analysis service — triggers AI analysis in-process and returns persisted results."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.repositories.analysis_repository import (
    ActorRepository,
    OpportunityRepository,
    TechnologyRepository,
    TrendRepository,
)
from app.repositories.project_repository import ProjectRepository
from app.schemas.analysis import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    ActorListResponse,
    ActorResponse,
    TechnologyListResponse,
    TechnologyResponse,
    TrendListResponse,
    TrendResponse,
    OpportunityListResponse,
    OpportunityResponse,
)
from app.tasks.analysis import run_analysis

logger = get_logger(__name__)


class AnalysisService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.tech_repo = TechnologyRepository(db)
        self.trend_repo = TrendRepository(db)
        self.actor_repo = ActorRepository(db)
        self.opp_repo = OpportunityRepository(db)

    async def run_full_analysis(
        self,
        project_id: uuid.UUID,
        request: AnalysisRunRequest,
    ) -> AnalysisRunResponse:
        """Run AI analysis in-process and return immediately.

        The analysis runs as a background asyncio task.
        """
        project = await self.project_repo.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        topic = request.topic or project.topic or project.name

        asyncio.create_task(run_analysis(self.db, str(project_id), topic))

        logger.info("analysis_dispatched", project_id=str(project_id))
        return AnalysisRunResponse(message="Analysis started", status="running")

    async def list_technologies(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 50, category: str | None = None,
    ) -> TechnologyListResponse:
        items, total = await self.tech_repo.list_by_project(project_id, page=page, page_size=page_size, category=category)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return TechnologyListResponse(
            items=[TechnologyResponse.model_validate(t) for t in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def list_trends(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 50, trend_type: str | None = None,
    ) -> TrendListResponse:
        items, total = await self.trend_repo.list_by_project(project_id, page=page, page_size=page_size, trend_type=trend_type)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return TrendListResponse(
            items=[TrendResponse.model_validate(t) for t in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def list_actors(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 50, actor_type: str | None = None,
    ) -> ActorListResponse:
        items, total = await self.actor_repo.list_by_project(project_id, page=page, page_size=page_size, actor_type=actor_type)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return ActorListResponse(
            items=[ActorResponse.model_validate(a) for a in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    async def list_opportunities(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 50, opportunity_type: str | None = None,
    ) -> OpportunityListResponse:
        items, total = await self.opp_repo.list_by_project(project_id, page=page, page_size=page_size, opportunity_type=opportunity_type)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return OpportunityListResponse(
            items=[OpportunityResponse.model_validate(o) for o in items],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        )
