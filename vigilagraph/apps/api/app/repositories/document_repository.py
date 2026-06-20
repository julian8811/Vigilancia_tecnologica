"""Document repository — data access for surveillance-source documents."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for ``Document`` CRUD with project-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Document, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        document_type: str | None = None,
        processing_status: str | None = None,
    ) -> tuple[list[Document], int]:
        """Return a paginated list of documents for a project.

        Returns ``(items, total_count)``.
        """
        base = select(Document).where(Document.project_id == project_id)
        if document_type:
            base = base.where(Document.file_type == document_type)
        if processing_status:
            base = base.where(Document.processing_status == processing_status)

        # Total count
        count_q = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar_one()

        # Paginated items
        offset = (page - 1) * page_size
        stmt = base.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().unique().all())

        return items, total

    async def list_by_project_simple(self, project_id: uuid.UUID) -> list[Document]:
        """Return all documents for a project (unpaginated)."""
        stmt = select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_checksum(self, project_id: uuid.UUID, checksum: str) -> Document | None:
        """Return a document matching *checksum* within a project, or ``None``."""
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .where(Document.checksum == checksum)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_project(self, project_id: uuid.UUID) -> int:
        """Return the total number of documents in a project."""
        stmt = (
            select(func.count(Document.id))
            .select_from(Document)
            .where(Document.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_type(self, project_id: uuid.UUID) -> dict[str, int]:
        """Return a map of ``document_type → count`` for a project."""
        stmt = (
            select(Document.file_type, func.count(Document.id))
            .where(Document.project_id == project_id)
            .group_by(Document.file_type)
        )
        result = await self.session.execute(stmt)
        return {row[0] or "unknown": row[1] for row in result.all()}
