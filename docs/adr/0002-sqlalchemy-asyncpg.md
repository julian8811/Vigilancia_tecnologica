# ADR-002: SQLAlchemy 2.0 + asyncpg

**Status:** Accepted.

**Context:** The backend needs Postgres + pgvector for vector storage. We need async I/O throughout the request path.

**Decision:** Use SQLAlchemy 2.0 with the async dialect (`asyncpg`). Pydantic v2 for request/response schemas. Alembic for migrations.

**Consequences:** Pydantic v2 has stricter validation than v1 — caught several issues at boot time. Async SQLAlchemy 2.0 is well-supported but has rough edges around relationships; we keep them shallow.
