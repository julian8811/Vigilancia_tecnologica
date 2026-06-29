"""Projects router — CRUD, status transitions, and search-strategy endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import (
    get_current_active_user,
    get_db,
    require_min_role,
    verify_project_org,
)
from app.core.permissions import Role
from app.models.user import User
from app.repositories.collection_run_repository import CollectionRunRepository
from app.schemas.collection_run import CollectionRunListResponse
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.schemas.search_strategy import SearchStrategyResponse, SearchStrategyUpdate
from app.services.project_service import ProjectService
from app.services.search_strategy_service import SearchStrategyService


class StatusTransitionRequest(BaseModel):
    """Request body for transitioning project status."""
    status: str

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["proyectos"])


# Reusable dependencies: gate routes by minimum role. ``viewer`` is
# implicit (any authenticated user passes via get_current_active_user),
# so the named gates below start at ``analyst``.
_require_analyst = require_min_role(Role.ANALYST)
_require_admin = require_min_role(Role.ADMIN)


def _build_list_response(items: list[ProjectResponse], total: int, page: int, page_size: int) -> ProjectListResponse:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filtrar por estado"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """List projects for the current user's organisation. Viewer+."""
    if current_user.organization_id is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    service = ProjectService(db)
    return await service.list_projects(
        current_user.organization_id, page=page, page_size=page_size, status=status,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new surveillance project. Analyst+."""
    if current_user.organization_id is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    service = ProjectService(db)
    return await service.create_project(data, current_user.organization_id, current_user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Return a single project (org-bound). Viewer+."""
    service = ProjectService(db)
    return await service.get_project(project_id, current_user.organization_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Update an existing project. Analyst+."""
    service = ProjectService(db)
    return await service.update_project(project_id, data, current_user.organization_id)


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> dict:
    """Hard-delete a project. Admin+."""
    service = ProjectService(db)
    await service.delete_project(project_id, current_user.organization_id)
    return {"detail": "Proyecto eliminado"}


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Duplicate a project (without documents, graphs, or reports). Analyst+."""
    service = ProjectService(db)
    return await service.duplicate_project(project_id, current_user.organization_id, current_user.id)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Archive a project (transition to ``archived`` status). Analyst+."""
    service = ProjectService(db)
    return await service.archive_project(project_id, current_user.organization_id)


@router.post("/{project_id}/status", response_model=ProjectResponse)
async def transition_project_status(
    project_id: uuid.UUID,
    body: StatusTransitionRequest,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Transition a project's status. Analyst+."""
    service = ProjectService(db)
    return await service.transition_status(project_id, body.status, current_user.organization_id)


@router.post("/{project_id}/collect", response_model=ProjectResponse)
async def collect_project(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> ProjectResponse:
    """Trigger document collection for a project. Analyst+."""
    service = ProjectService(db)
    return await service.transition_status(project_id, "collecting", current_user.organization_id)


@router.get("/{project_id}/collection-runs", response_model=CollectionRunListResponse)
async def list_collection_runs(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> CollectionRunListResponse:
    """Return paginated collection runs. Viewer+."""
    repo = CollectionRunRepository(db)
    items, total = await repo.list_by_project(project_id, page=page, page_size=page_size)
    return CollectionRunListResponse(items=items, total=total)


@router.get("/{project_id}/search-strategy", response_model=SearchStrategyResponse | None)
async def get_search_strategy(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> SearchStrategyResponse | None:
    """Return the search strategy. Viewer+."""
    service = SearchStrategyService(db)
    return await service.get_strategy(project_id, current_user.organization_id)


@router.put("/{project_id}/search-strategy", response_model=SearchStrategyResponse)
async def update_search_strategy(
    project_id: uuid.UUID,
    data: SearchStrategyUpdate,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> SearchStrategyResponse:
    """Update (or create) the search strategy. Analyst+."""
    service = SearchStrategyService(db)
    return await service.update_strategy(project_id, data, current_user.organization_id)


@router.post("/{project_id}/search-strategy/generate", response_model=SearchStrategyResponse)
async def generate_search_strategy(
    project_id: uuid.UUID,
    current_user: User = Depends(_require_analyst),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(verify_project_org),
) -> SearchStrategyResponse:
    """Generate the search strategy. Analyst+."""
    service = SearchStrategyService(db)
    return await service.generate_strategy(project_id, current_user.organization_id)
