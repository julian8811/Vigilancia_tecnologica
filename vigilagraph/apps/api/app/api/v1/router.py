"""V1 API router — mounts all v1 endpoint sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1")


@router.get("/health")
async def health() -> dict[str, str]:
    """Health-check endpoint — returns service status."""
    return {"status": "ok", "version": "1.0.0"}
