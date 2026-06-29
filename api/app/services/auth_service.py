"""Authentication service — registration and login orchestration."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.schemas.organization import OrganizationCreate

logger = get_logger(__name__)


def _role_for_new_user(creating_new_org: bool) -> str:
    """Pick the role for a freshly-registered user.

    Inlined here (rather than imported from app.core.permissions)
    because this branch is built before S11/RBAC lands. The default
    contract is: creating a new org -> "owner", joining an existing
    one -> "viewer". S11 replaces this with ``assign_role_on_register``
    from app.core.permissions; the two implementations agree.
    """
    return "owner" if creating_new_org else "viewer"


class AuthService:
    """Encapsulates the business logic for user registration and login."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)

    async def register_user(self, request: RegisterRequest) -> User:
        """Create a new user account. Returns the persisted User on success.

        Raises ``HTTPException(409)`` if the email is taken,
        ``HTTPException(400)`` if the named org does not exist.
        """
        # 1. Check email uniqueness
        existing = await self.user_repo.get_by_email(request.email)
        if existing:
            logger.warning("registration_email_taken", email=request.email)
            raise HTTPException(status_code=409, detail="Este correo ya está registrado")

        # 2. Create or resolve organisation
        creating_new_org = request.organization_slug is None
        if request.organization_slug:
            org = await self.org_repo.get_by_slug(request.organization_slug)
            if org is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Organización '{request.organization_slug}' no encontrada",
                )
        else:
            base_slug = self.org_repo.slugify(request.name)
            slug = await self._ensure_unique_slug(base_slug)
            org_schema = OrganizationCreate(
                name=f"{request.name}'s Organization",
                slug=slug,
            )
            org = await self.org_repo.create(org_schema)
            logger.info("org_created", org_id=org.id, slug=org.slug)

        # 3. Hash password
        password_hash = hash_password(request.password)

        # 4. Create user with the role determined by join-vs-create.
        role = _role_for_new_user(creating_new_org=creating_new_org)
        user = User(
            email=request.email,
            name=request.name,
            password_hash=password_hash,
            organization_id=org.id,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info(
            "user_created",
            user_id=user.id,
            email=user.email,
            role=role,
            created_new_org=creating_new_org,
        )
        return user

    async def login_user(
        self,
        request: LoginRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User | None, str | None]:
        """Authenticate an existing user.

        Returns ``(user, None)`` on success, ``(None, reason)`` on
        failure where *reason* is one of: ``"unknown_email"``,
        ``"inactive"``, ``"wrong_password"``. The router maps the
        reason onto an audit-log row and an HTTP 401.
        """
        user = await self.user_repo.get_by_email(request.email)
        if user is None:
            logger.info("login_failed", email=request.email, reason="unknown_email", ip=ip)
            return None, "unknown_email"

        if not user.is_active:
            logger.info("login_failed", email=request.email, reason="inactive", ip=ip)
            return None, "inactive"

        if not verify_password(request.password, user.password_hash):
            logger.info("login_failed", email=request.email, reason="wrong_password", ip=ip)
            return None, "wrong_password"

        logger.info("login_success", user_id=user.id, email=user.email, ip=ip)
        return user, None

    async def change_password(self, user: User, request: ChangePasswordRequest) -> None:
        """Verify the current password and set a new one."""
        if not verify_password(request.old_password, user.password_hash):
            logger.warning("password_change_failed", user_id=user.id, reason="wrong_old_password")
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

        user.password_hash = hash_password(request.new_password)
        await self.db.flush()
        logger.info("password_changed", user_id=user.id)

    async def _ensure_unique_slug(self, base_slug: str) -> str:
        """Return *base_slug* if available, otherwise append ``-1``,
        ``-2``, etc."""
        slug = base_slug
        counter = 1
        while await self.org_repo.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug
