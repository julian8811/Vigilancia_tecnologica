"""Report repository — CRUD for report records."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Report, session)

    async def list_by_project(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 50,
    ) -> tuple[list[Report], int]:
        query = (
            select(Report)
            .where(Report.project_id == project_id)
            .order_by(Report.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_q = select(func.count()).select_from(Report).where(Report.project_id == project_id)
        items = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(count_q)).scalar() or 0
        return list(items), total
