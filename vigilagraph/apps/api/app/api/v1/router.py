"""V1 API router — mounts all v1 endpoint sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.projects import router as projects_router
from app.api.v1.corpus import router as corpus_router
from app.api.v1.graph import router as graph_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(projects_router)
router.include_router(documents_router)
router.include_router(corpus_router)
router.include_router(graph_router)


@router.get("/health")
async def health() -> dict[str, str]:
    """Health-check endpoint — returns service status."""
    return {"status": "ok", "version": "1.0.0"}
