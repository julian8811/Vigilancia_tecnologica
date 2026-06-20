"""Search-strategy repository — keyword configuration per project."""

from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_strategy import SearchStrategy
from app.repositories.base import BaseRepository


class SearchStrategyRepository(BaseRepository[SearchStrategy]):
    """Repository for ``SearchStrategy`` CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SearchStrategy, session)

    async def get_by_project(self, project_id: uuid.UUID) -> SearchStrategy | None:
        """Return the search strategy for a project, or ``None``."""
        stmt = select(SearchStrategy).where(SearchStrategy.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, project_id: uuid.UUID, schema: BaseModel) -> SearchStrategy:
        """Create or update the search strategy for a project.

        Because ``project_id`` is unique in the table, at most one
        strategy exists per project.
        """
        existing = await self.get_by_project(project_id)
        data = schema.model_dump(exclude_unset=True)
        # Remove project_id from data if it was included — we set it explicitly
        data.pop("project_id", None)

        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        instance = self.model(project_id=project_id, **data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
