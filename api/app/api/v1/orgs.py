"""Org-member management router.

Lets org admins (or superusers) change a member's role within the
organisation. The list and delete endpoints are intentionally out
of scope for this initial RBAC change — they belong in a separate
"Org management" surface along with invitations.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_min_role
from app.core.permissions import Role, has_role_at_least
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/orgs/{org_slug}/members", tags=["organización"])


class ChangeRoleRequest(BaseModel):
    """Payload for changing a member's role."""

    role: str = Field(..., description=f"One of: {', '.join(Role.all())}")


@router.patch("/{user_id}", status_code=200)
async def change_member_role(
    org_slug: str,
    user_id: uuid.UUID,
    body: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_min_role(Role.ADMIN)),
) -> dict:
    """Change a member's role in the org.

    The actor must be admin+ in the org (or superuser). The target
    user must already belong to the org. A non-superuser admin
    cannot promote another user to a role above their own; e.g.
    an admin cannot create a new owner — only an existing owner
    or a superuser can.
    """
    if body.role not in Role.all():
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Opciones: {', '.join(Role.all())}",
        )

    org = (await db.execute(select(Organization).where(Organization.slug == org_slug))).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if not actor.is_superuser and actor.organization_id != org.id:
        raise HTTPException(status_code=403, detail="No pertenecés a esta organización")

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if target.organization_id != org.id:
        raise HTTPException(
            status_code=404,
            detail="El usuario no pertenece a esta organización",
        )

    # Privilege ceiling: a non-superuser admin cannot grant a role
    # higher than their own. Owners can do anything except demote
    # the last owner (handled below).
    if not actor.is_superuser and not has_role_at_least(actor, body.role):
        raise HTTPException(
            status_code=403,
            detail=f"No podés asignar un rol superior al tuyo ({actor.role})",
        )

    # Last-owner protection: if demoting the only owner, refuse.
    if target.role == Role.OWNER and body.role != Role.OWNER:
        owner_count_q = (
            select(User)
            .where(User.organization_id == org.id)
            .where(User.role == Role.OWNER)
        )
        owners = (await db.execute(owner_count_q)).scalars().all()
        if len(owners) <= 1:
            raise HTTPException(
                status_code=409,
                detail="No podés degradar al último owner de la organización",
            )

    previous = target.role
    target.role = body.role
    await db.flush()

    return {
        "detail": "Rol actualizado",
        "user_id": str(target.id),
        "previous_role": previous,
        "new_role": target.role,
    }
