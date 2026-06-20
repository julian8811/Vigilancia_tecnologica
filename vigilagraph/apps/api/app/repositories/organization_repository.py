"""Organization repository — data access for the organizations table."""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for ``Organization`` CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Organization, session)

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Return an organization by its slug, or ``None``."""
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Return ``True`` if the slug is already taken."""
        stmt = select(func.count(Organization.id)).select_from(Organization).where(Organization.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar() > 0

    @staticmethod
    def slugify(text: str) -> str:
        """Convert arbitrary text to a URL-safe slug.

        Examples:
            "Julian's Organization" -> "julians-organization"
            "Acme Corp."           -> "acme-corp"
        """
        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug)
        return slug.strip("-")
