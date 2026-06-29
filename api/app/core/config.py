"""Application configuration sourced from environment variables."""

from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Weak values that must NEVER be accepted in production.
_WEAK_JWT_SECRETS = frozenset(
    {
        "",
        "change-me-to-a-long-random-string",
        "test-secret",
        "secret",
        "changeme",
    }
)
_ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class Settings(BaseSettings):
    """Pydantic BaseSettings loading from env vars / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    ENV: str = "development"
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://vigilagraph:vigilagraph@localhost:5432/vigilagraph"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://vigilagraph:vigilagraph@localhost:5432/vigilagraph"

    # ── Auth / Security ──────────────────────────────────────────
    # Default kept for local dev and tests; production startup MUST override.
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    # Access token: short-lived, used for most API calls.
    JWT_EXPIRATION_MINUTES: int = 15
    # Refresh token: long-lived, used only by /auth/refresh to mint
    # a new access token. Rotated on every refresh.
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    # Names of the cookies set on /auth/login and /auth/register.
    ACCESS_TOKEN_COOKIE: str = "vg_access"
    REFRESH_TOKEN_COOKIE: str = "vg_refresh"
    # Name of the CSRF double-submit cookie. JS reads it via
    # document.cookie and echoes the value in the X-CSRF-Token header
    # on every mutating request. See app.core.csrf.
    CSRF_COOKIE_NAME: str = "vg_csrf"
    # When True, the cookies are marked Secure (HTTPS-only). Enable
    # in production; the api container is reachable on plain HTTP
    # locally so it stays False in dev.
    COOKIE_SECURE: bool = False

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── External Source APIs ─────────────────────────────────────
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    LENS_API_TOKEN: str = ""
    GEMINI_API_KEY: str = ""

    # ── Object Storage (S3-compatible) ───────────────────────────
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "vigilagraph-storage"
    S3_REGION: str = "us-east-1"

    # ── Graphify ─────────────────────────────────────────────────
    GRAPHIFY_COMMAND: str = "graphify"

    # ── Local Storage ────────────────────────────────────────────
    STORAGE_LOCAL_PATH: str = "/tmp/vigilagraph-storage"

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Derived properties ───────────────────────────────────────

    @property
    def is_development(self) -> bool:
        return self.ENV.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.FRONTEND_URL]
        if self.is_development:
            origins.extend(["http://localhost:3000", "http://localhost:5173"])
        return list(set(origins))

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse to boot in production with weak or default secrets.

        These checks are intentionally strict: any failure here aborts the
        process at import time, before the app can serve a single request.
        """
        if not self.is_production:
            return self

        errors: list[str] = []

        if self.JWT_SECRET in _WEAK_JWT_SECRETS:
            errors.append(
                "JWT_SECRET is set to a known weak value. "
                "Generate one with `openssl rand -hex 32` and set it in the env."
            )
        elif len(self.JWT_SECRET.encode("utf-8")) < 32:
            errors.append(
                f"JWT_SECRET must be at least 32 bytes (got {len(self.JWT_SECRET)})."
            )

        if self.JWT_ALGORITHM not in _ALLOWED_JWT_ALGORITHMS:
            errors.append(
                f"JWT_ALGORITHM must be one of {sorted(_ALLOWED_JWT_ALGORITHMS)} "
                f"(got {self.JWT_ALGORITHM!r}). The 'none' algorithm is not allowed."
            )

        if self.S3_ACCESS_KEY in ("", "minioadmin") or self.S3_SECRET_KEY in ("", "minioadmin"):
            errors.append(
                "S3_ACCESS_KEY and S3_SECRET_KEY must be set to real values in production "
                "(the minioadmin defaults are not safe)."
            )

        if errors:
            raise ValueError("Refusing to start in production: " + " | ".join(errors))

        return self


settings = Settings()
