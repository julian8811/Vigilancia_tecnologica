# ADR-003: RBAC enforced on mutating endpoints

**Status:** Implemented.

**Context:** The `User` model has `role` and `is_superuser` columns. The `require_min_role(min_role)` dependency is defined in `app/api/deps.py:203-229`.

**Decision:** All mutating endpoints (POST, PUT, PATCH, DELETE) now gate via `require_min_role(Role.ANALYST)`. Read-only endpoints remain open to `viewer`. Superusers bypass all checks.

**Consequences:** (+) RBAC is now wired across all routers. (-) The exact permission matrix needs review before multi-tenant public release.
