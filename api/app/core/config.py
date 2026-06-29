"""Application configuration sourced from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    LOG_LEVEL: str = "DEBUG"

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


settings = Settings()
