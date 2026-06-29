"""Authentication service — registration and login orchestration."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserResponse
from app.services.audit_service import AuditContext, AuditEvent, AuditService

logger = get_logger(__name__)


class AuthService:
    """Encapsulates the business logic for user registration and login."""

    def __init__(self, db: AsyncSession, audit_context: AuditContext | None = None) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)
        # Audit log writes use their own session so they persist even
        # when the business transaction rolls back (e.g. login_failed
        # raises HTTPException, the parent tx rolls back, but the
        # login_failed audit row should still be recorded).
        self.audit = AuditService(db)
        self.audit_context = audit_context or AuditContext()

    async def register(self, request: RegisterRequest) -> TokenResponse:
        """Create a new user account.

        Flow:
          1. Check email uniqueness
          2. Create organisation (use provided slug or auto-generate)
          3. Hash the password
          4. Create the user with role ``owner``
          5. Issue a JWT
          6. Return ``TokenResponse``
        """
        # 1. Check email uniqueness
        existing = await self.user_repo.get_by_email(request.email)
        if existing:
            await self.audit.record(
                AuditEvent.REGISTER_FAILED,
                context=self.audit_context,
                metadata={"email": request.email, "reason": "email_taken"},
            )
            logger.warning("registration_email_taken", email=request.email)
            raise HTTPException(status_code=409, detail="Este correo ya está registrado")

        # 2. Create or resolve organisation
        try:
            if request.organization_slug:
                org = await self.org_repo.get_by_slug(request.organization_slug)
                if org is None:
                    await self.audit.record(
                        AuditEvent.REGISTER_FAILED,
                        context=self.audit_context,
                        metadata={
                            "email": request.email,
                            "reason": "unknown_organization_slug",
                            "slug": request.organization_slug,
                        },
                    )
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
        except HTTPException:
            raise
        except Exception as exc:
            await self.audit.record(
                AuditEvent.REGISTER_FAILED,
                context=self.audit_context,
                metadata={"email": request.email, "reason": "org_creation_error", "error": str(exc)},
            )
            raise

        # 3. Hash password
        password_hash = hash_password(request.password)

        # 4. Create user directly (schema maps password → password_hash)
        user = User(
            email=request.email,
            name=request.name,
            password_hash=password_hash,
            organization_id=org.id,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info("user_created", user_id=user.id, email=user.email)

        # 5. Issue JWT
        token = create_access_token(subject=str(user.id))

        # 6. Audit (success). Recorded AFTER the user is committed in
        # memory so the row carries the new actor_id. The audit service
        # shares the session, so the row commits with the user.
        await self.audit.record(
            AuditEvent.REGISTER,
            context=AuditContext(
                actor_id=user.id,
                organization_id=org.id,
                ip=self.audit_context.ip,
                user_agent=self.audit_context.user_agent,
                request_id=self.audit_context.request_id,
            ),
            metadata={"email": user.email},
        )

        # 7. Return response
        user_resp = UserResponse.model_validate(user)
        return TokenResponse(access_token=token, user=user_resp)

    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate an existing user."""
        user = await self.user_repo.get_by_email(request.email)
        if user is None:
            await self.audit.record(
                AuditEvent.LOGIN_FAILED,
                context=self.audit_context,
                metadata={"email": request.email, "reason": "unknown_email"},
            )
            logger.info("login_failed", email=request.email, reason="unknown_email")
            raise HTTPException(status_code=401, detail="Correo o contraseña inválidos")

        if not user.is_active:
            await self.audit.record(
                AuditEvent.LOGIN_FAILED,
                context=AuditContext(
                    actor_id=user.id,
                    organization_id=user.organization_id,
                    ip=self.audit_context.ip,
                    user_agent=self.audit_context.user_agent,
                    request_id=self.audit_context.request_id,
                ),
                metadata={"email": user.email, "reason": "inactive"},
            )
            logger.info("login_failed", email=request.email, reason="inactive")
            raise HTTPException(status_code=401, detail="Cuenta desactivada")

        if not verify_password(request.password, user.password_hash):
            await self.audit.record(
                AuditEvent.LOGIN_FAILED,
                context=AuditContext(
                    actor_id=user.id,
                    organization_id=user.organization_id,
                    ip=self.audit_context.ip,
                    user_agent=self.audit_context.user_agent,
                    request_id=self.audit_context.request_id,
                ),
                metadata={"email": user.email, "reason": "wrong_password"},
            )
            logger.info("login_failed", email=request.email, reason="wrong_password")
            raise HTTPException(status_code=401, detail="Correo o contraseña inválidos")

        token = create_access_token(subject=str(user.id))
        logger.info("login_success", user_id=user.id, email=user.email)

        await self.audit.record(
            AuditEvent.LOGIN_SUCCESS,
            context=AuditContext(
                actor_id=user.id,
                organization_id=user.organization_id,
                ip=self.audit_context.ip,
                user_agent=self.audit_context.user_agent,
                request_id=self.audit_context.request_id,
            ),
            metadata={"email": user.email},
        )

        user_resp = UserResponse.model_validate(user)
        return TokenResponse(access_token=token, user=user_resp)

    async def change_password(self, user: User, request: ChangePasswordRequest) -> None:
        """Verify the current password and set a new one."""
        if not verify_password(request.old_password, user.password_hash):
            await self.audit.record(
                AuditEvent.PASSWORD_CHANGE_FAILED,
                context=self.audit_context,
                metadata={"reason": "wrong_old_password"},
            )
            logger.warning("password_change_failed", user_id=user.id, reason="wrong_old_password")
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

        user.password_hash = hash_password(request.new_password)
        await self.db.flush()
        await self.audit.record(AuditEvent.PASSWORD_CHANGE, context=self.audit_context)
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
