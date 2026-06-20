"""Project service — business logic for surveillance-project CRUD and status machine."""

from __future__ import annotations

import re
import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from structlog import get_logger

from app.models.project import SurveillanceProject
from app.repositories.project_repository import ProjectRepository
from app.repositories.search_strategy_repository import SearchStrategyRepository
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate

logger = get_logger(__name__)


class ProjectStatusMachine:
    """Valid project-status transitions.

    States
        draft → collecting → processing → graph_ready → report_ready
        Any   → archived
        Any   → failed
        Any except draft/archived → processing  (regenerate)
    """

    VALID_TRANSITIONS: dict[str, set[str]] = {
        "draft": {"collecting", "archived", "failed"},
        "collecting": {"processing", "archived", "failed"},
        "processing": {"graph_ready", "failed", "archived"},
        "graph_ready": {"report_ready", "processing", "archived", "failed"},
        "report_ready": {"archived", "failed"},
        "archived": set(),
        "failed": {"draft", "collecting", "processing", "graph_ready", "report_ready", "archived"},
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Return ``True`` when *to_status* is reachable from *from_status*."""
        allowed = cls.VALID_TRANSITIONS.get(from_status, set())
        return to_status in allowed

    @classmethod
    def valid_next_steps(cls, from_status: str) -> list[str]:
        """Return the list of statuses reachable from *from_status*."""
        return sorted(cls.VALID_TRANSITIONS.get(from_status, set()))


class ProjectService:
    """Encapsulates business logic for surveillance projects."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProjectRepository(db)

    async def create_project(self, schema: ProjectCreate, org_id: uuid.UUID, user_id: uuid.UUID) -> ProjectResponse:
        """Create a new project with auto-generated slug and ``draft`` status."""
        slug = await self._resolve_schema_slug(schema, org_id)
        data = schema.model_dump(exclude_unset=True)
        data["slug"] = slug
        data["organization_id"] = org_id
        data["created_by"] = user_id
        data.setdefault("status", "draft")

        project = SurveillanceProject(**data)
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)

        logger.info("project_created", project_id=project.id, slug=project.slug, org_id=org_id)
        return ProjectResponse.model_validate(project)

    async def get_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> ProjectResponse:
        """Return a project scoped to *org_id*, or 404."""
        project = await self.repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse.model_validate(project)

    async def list_projects(
        self,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> ProjectListResponse:
        """Paginated list of projects for an organisation."""
        items, total = await self.repo.list_by_organization(
            org_id, page=page, page_size=page_size, status=status,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return ProjectListResponse(
            items=[ProjectResponse.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_project(self, project_id: uuid.UUID, schema: ProjectUpdate, org_id: uuid.UUID) -> ProjectResponse:
        """Update a project scoped to *org_id*."""
        project = await self.repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        data = schema.model_dump(exclude_unset=True)
        slug = data.pop("slug", None)
        if slug is not None:
            resolved = await self._resolve_slug(slug, org_id, exclude=project_id)
            if resolved != slug:
                logger.warning("slug_collision_on_update", project_id=project_id, requested=slug, resolved=resolved)
            data["slug"] = resolved

        for field, value in data.items():
            setattr(project, field, value)

        try:
            await self.db.flush()
            await self.db.refresh(project)
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Slug is already taken in this organisation")

        logger.info("project_updated", project_id=project.id, slug=project.slug)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> None:
        """Hard-delete a project (with org-boundary check)."""
        project = await self.repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        await self.db.delete(project)
        await self.db.flush()
        logger.info("project_deleted", project_id=project_id, org_id=org_id)

    async def transition_status(self, project_id: uuid.UUID, to_status: str, org_id: uuid.UUID) -> ProjectResponse:
        """Validate and apply a status transition."""
        project = await self.repo.get_with_org_check(project_id, org_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        from_status = project.status
        if not ProjectStatusMachine.can_transition(from_status, to_status):
            valid = ProjectStatusMachine.valid_next_steps(from_status)
            raise HTTPException(
                status_code=422,
                detail=f"Cannot transition from '{from_status}' to '{to_status}'. Valid transitions: {valid}",
            )

        project.status = to_status
        await self.db.flush()
        await self.db.refresh(project)

        logger.info("project_status_changed", project_id=project.id, from_status=from_status, to_status=to_status)
        return ProjectResponse.model_validate(project)

    async def archive_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> ProjectResponse:
        """Transition a project to ``archived``."""
        return await self.transition_status(project_id, "archived", org_id)

    async def duplicate_project(self, project_id: uuid.UUID, org_id: uuid.UUID, user_id: uuid.UUID) -> ProjectResponse:
        """Deep-copy a project (without documents, graphs, or reports)."""
        original = await self.repo.get_with_org_check(project_id, org_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Project not found")

        new_title = self._append_copy_suffix(original.name)
        slug = await self._resolve_slug(
            self._slugify(new_title),
            org_id,
            force_unique=True,
        )

        dup = SurveillanceProject(
            name=new_title,
            slug=slug,
            topic=original.topic,
            description=original.description,
            surveillance_type=original.surveillance_type,
            language=original.language,
            status="draft",
            organization_id=org_id,
            created_by=user_id,
        )
        self.db.add(dup)
        await self.db.flush()
        await self.db.refresh(dup)

        logger.info("project_duplicated", original_id=project_id, copy_id=dup.id, slug=dup.slug)
        return ProjectResponse.model_validate(dup)

    # ── Slug helpers ──────────────────────────────────────────────

    async def _resolve_schema_slug(self, schema: ProjectCreate, org_id: uuid.UUID) -> str:
        """Resolve the slug from the schema, or generate from title."""
        if schema.slug:
            return await self._resolve_slug(schema.slug, org_id)
        return await self._resolve_slug(self._slugify(schema.name or "untitled"), org_id)

    async def _resolve_slug(
        self, provided_slug: str, org_id: uuid.UUID, *, exclude: uuid.UUID | None = None, force_unique: bool = False,
    ) -> str:
        """Return an available slug — per-org unique.

        1. Use *provided_slug* if given, otherwise slugify *fallback_title*.
        2. If the slug is taken in this org, append a random suffix.
        3. Repeat until a free slug is found (or *force_unique* limits
           attempts to avoid an infinite loop).
        """
        slug = provided_slug
        for _ in range(20):
            existing = await self.repo.get_by_slug(slug, org_id)
            if existing is None or (exclude and existing.id == exclude):
                return slug
            # Collision — append random suffix
            suffix = self._random_suffix()
            slug = f"{provided_slug}-{suffix}"
            logger.warning("slug_collision", provided=provided_slug, resolved=slug, org_id=org_id)

        # Fallback: extremely unlikely, but protect against infinite loop
        fallback = f"{provided_slug}-{self._random_suffix(length=12)}"
        logger.warning("slug_resolution_fallback", provided=provided_slug, resolved=fallback, org_id=org_id)
        return fallback

    @staticmethod
    def _slugify(title: str) -> str:
        """Turn a title into a URL-safe slug."""
        slug = title.lower().strip()
        slug = re.sub(r"[^a-z0-9áéíóúñ\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")

    @staticmethod
    def _random_suffix(length: int = 6) -> str:
        """Return a short random hex string."""
        return secrets.token_hex(length // 2 + 1)[:length]

    @staticmethod
    def _append_copy_suffix(title: str) -> str:
        """Append ``(copy)`` — or ``(copy N)`` if it already ends with one."""
        import re as _re

        # Check if already ends with (copy N)
        m = _re.search(r"\s*\(copy\s+\d+\)\s*$", title)
        if m:
            n = int(_re.search(r"\d+", m.group()).group()) + 1
            return _re.sub(r"\s*\(copy\s+\d+\)\s*$", f" (copy {n})", title)

        # Check if already ends with (copy)
        if _re.search(r"\s*\(copy\)\s*$", title):
            return _re.sub(r"\s*\(copy\)\s*$", " (copy 2)", title)

        return f"{title} (copy)"
