"""SQLAlchemy declarative base and metadata."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all VigilaGraph ORM models."""

    pass
