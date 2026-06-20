"""Projects router — CRUD, status transitions, and search-strategy endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.schemas.search_strategy import SearchStrategyResponse, SearchStrategyUpdate
from app.services.project_service import ProjectService
from app.services.search_strategy_service import SearchStrategyService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


def _ensure_org(current_user: User) -> None:
    """Raise 403 if the user has no organisation."""
    if current_user.organization_id is None:
        raise HTTPException(status_code=403, detail="User does not belong to an organisation")


def _build_list_response(items: list[ProjectResponse], total: int, page: int, page_size: int) -> ProjectListResponse:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by project status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """List projects for the current user's organisation."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.list_projects(
        current_user.organization_id, page=page, page_size=page_size, status=status,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new surveillance project."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.create_project(data, current_user.organization_id, current_user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Return a single project (org-bound)."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.get_project(project_id, current_user.organization_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update an existing project."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.update_project(project_id, data, current_user.organization_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard-delete a project (org-bound)."""
    _ensure_org(current_user)
    service = ProjectService(db)
    await service.delete_project(project_id, current_user.organization_id)


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Duplicate a project (without documents, graphs, or reports)."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.duplicate_project(project_id, current_user.organization_id, current_user.id)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Archive a project (transition to ``archived`` status)."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.archive_project(project_id, current_user.organization_id)


@router.post("/{project_id}/status", response_model=ProjectResponse)
async def transition_project_status(
    project_id: uuid.UUID,
    new_status: str = Query(..., description="Target status to transition to"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Transition a project's status (validated by the status machine)."""
    _ensure_org(current_user)
    service = ProjectService(db)
    return await service.transition_status(project_id, new_status, current_user.organization_id)


@router.get("/{project_id}/search-strategy", response_model=SearchStrategyResponse | None)
async def get_search_strategy(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SearchStrategyResponse | None:
    """Return the search strategy for a project (or ``null``)."""
    _ensure_org(current_user)
    service = SearchStrategyService(db)
    return await service.get_strategy(project_id, current_user.organization_id)


@router.put("/{project_id}/search-strategy", response_model=SearchStrategyResponse)
async def update_search_strategy(
    project_id: uuid.UUID,
    data: SearchStrategyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SearchStrategyResponse:
    """Update (or create) the search strategy for a project."""
    _ensure_org(current_user)
    service = SearchStrategyService(db)
    return await service.update_strategy(project_id, data, current_user.organization_id)


@router.post("/{project_id}/search-strategy/generate", response_model=SearchStrategyResponse)
async def generate_search_strategy(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SearchStrategyResponse:
    """Generate (MVP stub) or regenerate the search strategy from the
    project topic.  Real AI-powered generation lands in Change 4."""
    _ensure_org(current_user)
    service = SearchStrategyService(db)
    return await service.generate_strategy(project_id, current_user.organization_id)
