"""Generic base repository with CRUD helpers for SQLAlchemy async."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.db.base import Base

ModelT = TypeVar("ModelT", bound="Base")
_ModelT = TypeVar("_ModelT", bound="Base")


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common CRUD helpers.

    Subclass and set ``model`` to the SQLAlchemy model class, or pass
    it at construction time.
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelT | None:
        """Return a single record by primary key, or ``None``."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[ModelT]:
        """Return all records matching the provided keyword filters."""
        stmt = select(self.model)
        for key, value in filters.items():
            column = getattr(self.model, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def create(self, schema: BaseModel) -> ModelT:
        """Build an ORM instance from *schema*, add it to the session and
        return it after a flush + refresh."""
        data = schema.model_dump(exclude_unset=True)
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, schema: BaseModel) -> ModelT:
        """Fetch the record by *id*, apply non-unset fields from
        *schema*, flush, refresh and return it.

        Raises ``ValueError`` when the record does not exist.
        """
        instance = await self.get(id)
        if instance is None:
            msg = f"{self.model.__name__} with id {id} not found"
            raise ValueError(msg)
        data = schema.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> None:
        """Delete the record identified by *id*."""
        instance = await self.get(id)
        if instance is not None:
            await self.session.delete(instance)
            await self.session.flush()
