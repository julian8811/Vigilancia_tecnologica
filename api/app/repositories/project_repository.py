"""Project repository — data access for surveillance projects."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import SurveillanceProject
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[SurveillanceProject]):
    """Repository for ``SurveillanceProject`` CRUD with org-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SurveillanceProject, session)

    async def get_by_slug(self, slug: str, organization_id: uuid.UUID) -> SurveillanceProject | None:
        """Return a project by slug within an organisation, or ``None``."""
        stmt = (
            select(SurveillanceProject)
            .where(SurveillanceProject.slug == slug)
            .where(SurveillanceProject.organization_id == organization_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_org_check(self, project_id: uuid.UUID, organization_id: uuid.UUID) -> SurveillanceProject | None:
        """Return a project only when it belongs to *organization_id*."""
        stmt = (
            select(SurveillanceProject)
            .where(SurveillanceProject.id == project_id)
            .where(SurveillanceProject.organization_id == organization_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[SurveillanceProject], int]:
        """Return a paginated list of projects for an organisation.

        Returns ``(items, total_count)``.
        """
        base = select(SurveillanceProject).where(SurveillanceProject.organization_id == organization_id)
        if status:
            base = base.where(SurveillanceProject.status == status)

        # Total count
        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        # Paginated items
        offset = (page - 1) * page_size
        stmt = base.order_by(SurveillanceProject.created_at.desc()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total

    async def count_by_organization(self, organization_id: uuid.UUID) -> int:
        """Return the total number of projects for an organisation."""
        stmt = (
            select(func.count(SurveillanceProject.id))
            .select_from(SurveillanceProject)
            .where(SurveillanceProject.organization_id == organization_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
