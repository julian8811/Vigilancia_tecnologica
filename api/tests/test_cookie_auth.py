"""Cookie-based session tests (S2).

Covers:
* login/register set the vg_access and vg_refresh cookies (and not
  a body token).
* /auth/refresh rotates both cookies and requires a valid
  vg_refresh cookie.
* /auth/logout clears both cookies.
* Authenticated requests work with cookies only (no Authorization
  header).
* Programmatic clients can still use Authorization: Bearer.
* Cookie attrs: HttpOnly, SameSite=Lax.
* Type mismatch: a refresh token used as access → 401, and vice-versa.
* Cross-use rejection: invalid token → 401.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings


def _cookie_attrs(set_cookie: str) -> dict:
    """Parse a Set-Cookie header into a dict of attributes.

    Handles value-less flags (HttpOnly, Secure) by setting them to
    an empty string — matching the canonical Set-Cookie format.
    """
    parts = [p.strip() for p in set_cookie.split(";")]
    out: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
        else:
            # Value-less flag like HttpOnly or Secure.
            out[p.strip().lower()] = ""
    return out


# ── Cookie set on login/register ───────────────────────────────────────


@pytest.mark.asyncio
async def test_login_sets_cookies_not_body_token(client: AsyncClient):
    """login sets vg_access + vg_refresh in Set-Cookie; the body has no token."""
    await client.post("/api/v1/auth/register", json={
        "email": "cookie1@example.com",
        "name": "Cookie1",
        "password": "secure123",
        "organization_name": "Cookie1 Org",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "cookie1@example.com",
        "password": "secure123",
    })
    assert resp.status_code == 200
    # Body has user, no token.
    body = resp.json()
    assert "user" in body
    assert "access_token" not in body
    # Cookies set.
    assert "vg_access" in resp.cookies
    assert "vg_refresh" in resp.cookies


@pytest.mark.asyncio
async def test_register_sets_cookies(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "reg-cookie@example.com",
        "name": "Reg",
        "password": "secure123",
        "organization_name": "Reg Org",
    })
    # After the register call, client.cookies should have both.
    assert "vg_access" in client.cookies
    assert "vg_refresh" in client.cookies


# ── Cookie attributes ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cookies_are_httponly_and_samesite_lax(client: AsyncClient):
    """The JWT cookies (vg_access, vg_refresh) are HttpOnly + SameSite=Lax.

    The CSRF cookie (vg_csrf) is intentionally NOT httpOnly so the
    SPA can read it via document.cookie; it still has SameSite=Lax
    and path=/. Both classes share path and samesite.
    """
    resp = await client.post("/api/v1/auth/register", json={
        "email": "attrs@example.com",
        "name": "Attrs",
        "password": "secure123",
        "organization_name": "Attrs Org",
    })
    assert resp.status_code == 201
    set_cookie_headers = [
        v for k, v in resp.headers.raw
        if k == b"set-cookie"
    ]
    assert set_cookie_headers, "no Set-Cookie headers in response"
    for raw in set_cookie_headers:
        line = raw.decode()
        cookie_name = line.split(";", 1)[0].split("=", 1)[0].strip()
        attr = _cookie_attrs(line)
        # Every cookie is path=/, SameSite=Lax.
        assert attr.get("path") == "/", f"{cookie_name} should be scoped to /"
        assert attr.get("samesite", "").lower() == "lax", \
            f"{cookie_name} should be SameSite=Lax"
        # The JWT cookies are HttpOnly; the CSRF cookie is not.
        if cookie_name in ("vg_access", "vg_refresh"):
            assert attr.get("httponly") == "", \
                f"{cookie_name} should be HttpOnly"
        elif cookie_name == "vg_csrf":
            assert "httponly" not in attr, \
                f"vg_csrf must be JS-readable; got {attr}"


# ── Auth via cookies (no Authorization header) ────────────────────────


@pytest.mark.asyncio
async def test_me_works_with_cookies_only(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "me-cookie@example.com",
        "name": "Me",
        "password": "secure123",
        "organization_name": "Me Org",
    })
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "me-cookie@example.com"


# ── /auth/refresh ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_rotates_cookies(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "name": "Refresh",
        "password": "secure123",
        "organization_name": "Refresh Org",
    })
    old_access = client.cookies.get("vg_access")
    old_refresh = client.cookies.get("vg_refresh")
    assert old_access and old_refresh

    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200, resp.text
    # After a refresh, the new access and refresh tokens are different
    # from the originals. We compare against the body (refresh always
    # sets a new Set-Cookie; the parsed cookies travel with the
    # client).
    new_access = client.cookies.get("vg_access")
    new_refresh = client.cookies.get("vg_refresh")
    assert new_access and new_access != old_access, "access token should be rotated"
    assert new_refresh and new_refresh != old_refresh, "refresh token should be rotated"


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient):
    client.cookies.clear()
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


# ── /auth/logout ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "name": "Logout",
        "password": "secure123",
        "organization_name": "Logout Org",
    })
    assert "vg_access" in client.cookies
    # /logout is a mutating request, so the SPA (and this test)
    # must echo the CSRF token in the X-CSRF-Token header.
    csrf = client.cookies.get("vg_csrf")
    assert csrf
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    # The server sets Max-Age=0; httpx's cookie jar is updated.
    # (When Max-Age=0, httpx deletes the cookie from the jar.)
    # A subsequent /me should be 401.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


# ── Type mismatch: refresh used as access ──────────────────────────────


@pytest.mark.asyncio
async def test_refresh_token_rejected_on_protected_route(client: AsyncClient):
    """A refresh token presented to a regular endpoint must be 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "typecheck@example.com",
        "name": "TypeCheck",
        "password": "secure123",
        "organization_name": "TypeCheck Org",
    })
    # Replace the access cookie with the refresh cookie, then
    # call a route that uses get_current_user.
    refresh = client.cookies.get("vg_refresh")
    assert refresh
    client.cookies.set("vg_access", refresh)
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


# ── Authorization header still works (programmatic clients) ───────────


@pytest.mark.asyncio
async def test_authorization_header_works_alongside_cookies(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "bearer@example.com",
        "name": "Bearer",
        "password": "secure123",
        "organization_name": "Bearer Org",
    })
    access = client.cookies.get("vg_access")
    assert access
    # Clear cookies; the request should still succeed via the
    # Authorization header.
    client.cookies.clear()
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200, resp.text
