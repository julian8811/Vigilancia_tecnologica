"""Role-based access control for VigilaGraph.

Roles are string identifiers stored on ``User.role``. The hierarchy is:

    owner   (3)  — full control of the org: invite, change roles, delete org
    admin   (2)  — full control of projects in the org
    analyst (1)  — create/edit projects, run analyses, generate reports
    viewer  (0)  — read-only access to projects in the org

``is_superuser=True`` bypasses every role check (cross-org admin
operations: audit log, future org management). It is set explicitly
on the user record and is not derivable from any role.

Permission matrix (effective role required to perform the action):

    Resource / Action                  | owner | admin | analyst | viewer
    -----------------------------------|-------|-------|---------|--------
    GET /projects                      |  yes  |  yes  |   yes   |  yes
    POST /projects                     |  yes  |  yes  |   yes   |  no
    PATCH /projects/{id}               |  yes  |  yes  |   yes   |  no
    DELETE /projects/{id}              |  yes  |  yes  |   no    |  no
    POST /projects/{id}/duplicate      |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/archive        |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/status         |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/collect        |  yes  |  yes  |   yes   |  no
    PUT  /projects/{id}/search-strategy |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/.../generate   |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/documents/...  |  yes  |  yes  |   yes   |  no
    DELETE /projects/{id}/documents/.. |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/reports        |  yes  |  yes  |   yes   |  no
    POST /projects/{id}/reports/../regen | yes |  yes  |   yes   |  no
    DELETE /projects/{id}/reports/..   |  yes  |  yes  |   yes   |  no
    GET  /projects/{id}/reports/../dl  |  yes  |  yes  |   yes   |  yes
    GET  /api/v1/admin/*               |  superuser only (cross-org)

When S11 ships, plan the following separately (out of scope for this
change):

  * Org-level member management (invite, list, change role, remove).
  * Per-resource ACLs (e.g. a project owner is not the org owner).
  * Time-bounded roles.
"""

from __future__ import annotations

from app.models.user import User

# Role string constants. Stored in User.role and compared by string.
# Don't rename these without a database migration.
class Role:
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.OWNER, cls.ADMIN, cls.ANALYST, cls.VIEWER]


# Higher number = more privilege. Used to compare a user's role to a
# minimum required role.
_ROLE_RANK: dict[str, int] = {
    Role.OWNER: 30,
    Role.ADMIN: 20,
    Role.ANALYST: 10,
    Role.VIEWER: 0,
}


def role_rank(role: str | None) -> int:
    """Return the numeric rank for a role string, or -1 if unknown.

    ``None`` (role not set) is treated as 0, equivalent to ``viewer``,
    so the principle of least privilege wins by default.
    """
    if role is None:
        return 0
    return _ROLE_RANK.get(role, -1)


def has_role_at_least(user: User, min_role: str) -> bool:
    """True when *user*'s role is at least *min_role*.

    ``is_superuser=True`` always passes. Unknown roles, including
    ``None``, fail the check unless ``is_superuser`` is set.
    """
    if user.is_superuser:
        return True
    return role_rank(user.role) >= role_rank(min_role)


def assign_role_on_register(*, creating_new_org: bool) -> str:
    """Pick the role to assign a freshly-registered user.

    * Creating a new org → ``owner`` (they are the first user of the
      org and the de-facto admin).
    * Joining an existing org → ``viewer`` (read-only until an
      ``owner``/``admin`` upgrades them via the future
      member-management endpoint).

    This is intentionally conservative: new users land as viewers so
    the org owner can audit who has write access.
    """
    if creating_new_org:
        return Role.OWNER
    return Role.VIEWER
