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

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / Security ──────────────────────────────────────────
    JWT_SECRET: str = "change-me-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # ── OpenAI ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

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

    # ── Celery ───────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: str = "json"

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
