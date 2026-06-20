"""Organization model — multi-tenant organisation."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="university | company | research_group | consultancy | government | other",
    )
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship("User", back_populates="organization", lazy="selectin")
    projects: Mapped[list["SurveillanceProject"]] = relationship(
        "SurveillanceProject", back_populates="organization", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug!r}>"
