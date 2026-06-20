"""FastAPI dependencies — DB sessions, auth, and role checking."""

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
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT from the ``Authorization`` header and return the
    corresponding ``User`` ORM instance.

    Raises ``401 UNAUTHORIZED`` when the token is missing, invalid, or
    the user no longer exists.
    """
    try:
        payload = decode_access_token(token)
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
        raise HTTPException(status_code=400, detail="Inactive user")
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
                detail=f"Requires one of {roles}",
            )
        return current_user

    return _role_checker
