"""FastAPI dependencies — DB sessions, auth, role checking, and org-bound project verification."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_db() -> AsyncSession:
    """Provide an async database session with automatic commit/rollback.

    Usage::

        async def my_route(db: AsyncSession = Depends(get_db)): ...

    The session is committed on success and rolled back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
) -> User:
    """Decode the JWT and return the corresponding ``User`` ORM instance.

    Accepts the token from either:

    * The ``Authorization: Bearer ...`` header (for programmatic
      clients, server-to-server, and tests).
    * The ``vg_access`` cookie (set by ``/auth/login`` and
      ``/auth/register``).

    Raises ``401 UNAUTHORIZED`` when the token is missing, invalid,
    or the user no longer exists.
    """
    # Prefer the cookie so cookie-only clients (the web app) work
    # without sending an Authorization header. Header takes
    # precedence when present — that lets API clients use a Bearer
    # token without the cookie round-trip.
    from app.core.config import settings

    cookie_token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    raw_token = token or cookie_token
    if not raw_token:
        raise credentials_exception

    try:
        payload = decode_access_token(raw_token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be active.

    Raises ``400 BAD REQUEST`` when the account is deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


async def verify_project_org(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify the user belongs to the same org as the project.

    Returns the current user on success; raises 403/404 otherwise.
    Always raises 404 (not 403) to avoid leaking project existence.
    """
    if current_user.organization_id is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    repo = ProjectRepository(db)
    project = await repo.get_with_org_check(project_id, current_user.organization_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return current_user


def require_roles(*roles: str):
    """Factory that returns a dependency ensuring the user has one of the
    required roles.

    Usage::

        @router.get("/admin")
        async def admin_only(
            current_user: User = Depends(require_roles("owner", "admin")),
        ): ...
    """

    async def _role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_role = getattr(current_user, "role", None)
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requiere uno de estos roles: {roles}",
            )
        return current_user

    return _role_checker
