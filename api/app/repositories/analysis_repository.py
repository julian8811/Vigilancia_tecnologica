"""Repositories for analysis models (Technology, Trend, Actor, Opportunity)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Actor, Opportunity, Technology, Trend
from app.repositories.base import BaseRepository


class TechnologyRepository(BaseRepository[Technology]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Technology, session)

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50, category: str | None = None,
    ) -> tuple[list[Technology], int]:
        query = select(Technology).where(Technology.project_id == project_id)
        count_q = select(func.count()).select_from(Technology).where(Technology.project_id == project_id)
        if category:
            query = query.where(Technology.category == category)
            count_q = count_q.where(Technology.category == category)
        query = query.order_by(Technology.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_q)).scalar() or 0
        return list(items), total

    async def bulk_insert(self, technologies: list[Technology]) -> None:
        self.session.add_all(technologies)
        await self.session.flush()

    async def delete_by_project(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Technology).where(Technology.project_id == project_id)
        )
        return result.rowcount


class TrendRepository(BaseRepository[Trend]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Trend, session)

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50, trend_type: str | None = None,
    ) -> tuple[list[Trend], int]:
        query = select(Trend).where(Trend.project_id == project_id)
        count_q = select(func.count()).select_from(Trend).where(Trend.project_id == project_id)
        if trend_type:
            query = query.where(Trend.trend_type == trend_type)
            count_q = count_q.where(Trend.trend_type == trend_type)
        query = query.order_by(Trend.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_q)).scalar() or 0
        return list(items), total

    async def bulk_insert(self, trends: list[Trend]) -> None:
        self.session.add_all(trends)
        await self.session.flush()

    async def delete_by_project(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Trend).where(Trend.project_id == project_id)
        )
        return result.rowcount


class ActorRepository(BaseRepository[Actor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Actor, session)

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50, actor_type: str | None = None,
    ) -> tuple[list[Actor], int]:
        query = select(Actor).where(Actor.project_id == project_id)
        count_q = select(func.count()).select_from(Actor).where(Actor.project_id == project_id)
        if actor_type:
            query = query.where(Actor.actor_type == actor_type)
            count_q = count_q.where(Actor.actor_type == actor_type)
        query = query.order_by(Actor.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_q)).scalar() or 0
        return list(items), total

    async def bulk_insert(self, actors: list[Actor]) -> None:
        self.session.add_all(actors)
        await self.session.flush()

    async def delete_by_project(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Actor).where(Actor.project_id == project_id)
        )
        return result.rowcount


class OpportunityRepository(BaseRepository[Opportunity]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Opportunity, session)

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50, opportunity_type: str | None = None,
    ) -> tuple[list[Opportunity], int]:
        query = select(Opportunity).where(Opportunity.project_id == project_id)
        count_q = select(func.count()).select_from(Opportunity).where(Opportunity.project_id == project_id)
        if opportunity_type:
            query = query.where(Opportunity.opportunity_type == opportunity_type)
            count_q = count_q.where(Opportunity.opportunity_type == opportunity_type)
        query = query.order_by(Opportunity.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_q)).scalar() or 0
        return list(items), total

    async def bulk_insert(self, opportunities: list[Opportunity]) -> None:
        self.session.add_all(opportunities)
        await self.session.flush()

    async def delete_by_project(self, project_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Opportunity).where(Opportunity.project_id == project_id)
        )
        return result.rowcount
