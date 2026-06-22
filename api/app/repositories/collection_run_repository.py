"""CollectionRun repository — data access for external-source collection runs."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection_run import CollectionRun
from app.repositories.base import BaseRepository


class CollectionRunRepository(BaseRepository[CollectionRun]):
    """Repository for ``CollectionRun`` CRUD, scoped to a project."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CollectionRun, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CollectionRun], int]:
        """Return a paginated list of collection runs for a project, newest first.

        Returns ``(items, total_count)``.
        """
        base = select(CollectionRun).where(CollectionRun.project_id == project_id)

        # Total count
        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        # Paginated items
        offset = (page - 1) * page_size
        stmt = base.order_by(CollectionRun.created_at.desc()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total
