"""CSRF double-submit cookie tests.

Covers the spec for csrf-protection:

* The `vg_csrf` cookie is set on every successful `register` / `login` /
  `refresh` response.
* The cookie's attributes are: `path=/`, `SameSite=Lax`, `HttpOnly=False`,
  `Secure=settings.COOKIE_SECURE`, `Max-Age=7 days` (matches `vg_refresh`).
* The token is a fresh `secrets.token_urlsafe(32)` value — 43 chars,
  URL-safe — and is rotated on every register and refresh.
* State-changing requests (`POST/PUT/PATCH/DELETE`) under `/api/v1/`
  MUST carry a matching `X-CSRF-Token` header; a missing cookie, a
  missing header, or a mismatch returns 403.
* The `register` / `login` / `refresh` endpoints are exempt so a fresh
  client can bootstrap the cookie on the first call.
* `GET`, `HEAD`, `OPTIONS` and `/health` are not subject to the check.
* The frontend (web/lib/api.ts) reads `vg_csrf` from `document.cookie`
  and echoes it as `X-CSRF-Token` on every mutating request.
"""

from __future__ import annotations

import secrets

import pytest
from httpx import AsyncClient

from app.core.config import settings


def _set_cookie_headers(response) -> list[str]:
    """Return the raw Set-Cookie lines for *response*."""
    return [v.decode() for k, v in response.headers.raw if k == b"set-cookie"]


def _cookie_attrs(set_cookie: str) -> dict[str, str]:
    """Parse a Set-Cookie header into a dict of attributes (lowercased keys)."""
    parts = [p.strip() for p in set_cookie.split(";")]
    out: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip().lower()] = v.strip()
        else:
            out[p.strip().lower()] = ""
    return out


def _csrf_cookie_set_cookie(response) -> str | None:
    """Return the raw Set-Cookie line for `vg_csrf`, or None."""
    for line in _set_cookie_headers(response):
        if line.split(";", 1)[0].strip().startswith(f"{settings.CSRF_COOKIE_NAME}="):
            return line
    return None


# ── 1. Cookie is set on every bootstrap endpoint ──────────────────────


@pytest.mark.asyncio
async def test_csrf_cookie_set_on_login(client: AsyncClient):
    """POST /auth/login sets the vg_csrf cookie."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-login@example.com",
        "name": "CSRF Login",
        "password": "secure123",
        "organization_name": "CSRF Login Org",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "csrf-login@example.com",
        "password": "secure123",
    })
    assert resp.status_code == 200, resp.text
    assert _csrf_cookie_set_cookie(resp) is not None, \
        "vg_csrf cookie should be set on /auth/login"
    assert settings.CSRF_COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_csrf_cookie_set_on_register(client: AsyncClient):
    """POST /auth/register sets the vg_csrf cookie."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "csrf-reg@example.com",
        "name": "CSRF Reg",
        "password": "secure123",
        "organization_name": "CSRF Reg Org",
    })
    assert resp.status_code == 201, resp.text
    assert _csrf_cookie_set_cookie(resp) is not None
    assert settings.CSRF_COOKIE_NAME in resp.cookies


@pytest.mark.asyncio
async def test_csrf_cookie_set_on_refresh(client: AsyncClient):
    """POST /auth/refresh rotates the vg_csrf cookie."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-ref@example.com",
        "name": "CSRF Ref",
        "password": "secure123",
        "organization_name": "CSRF Ref Org",
    })
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200, resp.text
    assert _csrf_cookie_set_cookie(resp) is not None
    assert settings.CSRF_COOKIE_NAME in resp.cookies


# ── 2. Cookie attributes ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csrf_cookie_attributes(client: AsyncClient):
    """The vg_csrf cookie has path=/, samesite=lax, httpOnly=false, secure=COOKIE_SECURE."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "csrf-attrs@example.com",
        "name": "CSRF Attrs",
        "password": "secure123",
        "organization_name": "CSRF Attrs Org",
    })
    set_cookie = _csrf_cookie_set_cookie(resp)
    assert set_cookie is not None
    attrs = _cookie_attrs(set_cookie)
    assert attrs.get("path") == "/"
    assert attrs.get("samesite", "").lower() == "lax"
    # httpOnly must NOT be present (so JS can read it).
    assert "httponly" not in attrs, \
        f"vg_csrf must be JS-readable; got attrs={attrs}"
    # Max-Age should be 7 days (matches vg_refresh) in seconds.
    expected_max_age = settings.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60
    assert int(attrs.get("max-age", 0)) == expected_max_age, \
        f"vg_csrf max-age should be {expected_max_age}s (7d), got {attrs.get('max-age')}"
    # Secure flag depends on settings.COOKIE_SECURE.
    if settings.COOKIE_SECURE:
        assert "secure" in attrs, "expected Secure flag when COOKIE_SECURE=True"
    else:
        assert "secure" not in attrs, "no Secure flag when COOKIE_SECURE=False"


# ── 3. Token rotation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csrf_rotation_on_register(client: AsyncClient):
    """Each successful /auth/register issues a new vg_csrf token."""
    a = await client.post("/api/v1/auth/register", json={
        "email": "csrf-rot-a@example.com",
        "name": "A",
        "password": "secure123",
        "organization_name": "A Org",
    })
    b = await client.post("/api/v1/auth/register", json={
        "email": "csrf-rot-b@example.com",
        "name": "B",
        "password": "secure123",
        "organization_name": "B Org",
    })
    assert a.status_code == 201 and b.status_code == 201
    token_a = a.cookies.get(settings.CSRF_COOKIE_NAME)
    token_b = b.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token_a and token_b
    assert token_a != token_b, "vg_csrf must rotate between registrations"


@pytest.mark.asyncio
async def test_csrf_rotation_on_refresh(client: AsyncClient):
    """/auth/refresh rotates the vg_csrf token."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-ref-rot@example.com",
        "name": "RefRot",
        "password": "secure123",
        "organization_name": "RefRot Org",
    })
    before = client.cookies.get(settings.CSRF_COOKIE_NAME)
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200, resp.text
    after = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert before and after
    assert before != after, "vg_csrf must rotate on /auth/refresh"


# ── 4. Token shape ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csrf_token_entropy(client: AsyncClient):
    """Token is `secrets.token_urlsafe(32)`: 43 chars, URL-safe base64 alphabet."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "csrf-entropy@example.com",
        "name": "Entropy",
        "password": "secure123",
        "organization_name": "Entropy Org",
    })
    token = resp.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token is not None
    # token_urlsafe(32) → ceil(32 * 4/3) = 43 chars; URL-safe alphabet.
    assert len(token) == 43, f"expected 43 chars, got {len(token)}: {token!r}"
    import string
    alphabet = string.ascii_letters + string.digits + "-_"
    for ch in token:
        assert ch in alphabet, f"non-URL-safe char {ch!r} in token {token!r}"


# ── 5. Validation: missing / mismatched token → 403 ──────────────────


@pytest.mark.asyncio
async def test_csrf_missing_header_returns_403(client: AsyncClient):
    """POST /projects without X-CSRF-Token → 403 (cookie present, header missing)."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-nohdr@example.com",
        "name": "NoHdr",
        "password": "secure123",
        "organization_name": "NoHdr Org",
    })
    # Cookie is in the jar; we deliberately do NOT send the header.
    resp = await client.post("/api/v1/projects", json={
        "name": "X",
        "topic": "Y",
        "surveillance_type": "technological",
        "language": "en",
    })
    assert resp.status_code == 403, resp.text
    assert "CSRF" in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_csrf_mismatch_returns_403(client: AsyncClient):
    """POST with the wrong X-CSRF-Token → 403."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-mis@example.com",
        "name": "Mis",
        "password": "secure123",
        "organization_name": "Mis Org",
    })
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "X",
            "topic": "Y",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers={"X-CSRF-Token": "definitely-not-the-real-token"},
    )
    assert resp.status_code == 403, resp.text
    assert "CSRF" in resp.json().get("detail", "")


@pytest.mark.asyncio
async def test_csrf_missing_cookie_returns_403(client: AsyncClient):
    """POST with X-CSRF-Token but no vg_csrf cookie → 403.

    The conftest's patched transport auto-injects cookies from its
    internal jar; calling ``client.cookies.clear()`` does not strip
    them from the request. So we craft a Cookie header manually with
    only the access token (auth) and omit the vg_csrf.
    """
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-nocookie@example.com",
        "name": "NoCookie",
        "password": "secure123",
        "organization_name": "NoCookie Org",
    })
    access = client.cookies.get(settings.ACCESS_TOKEN_COOKIE)
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert access and csrf
    # Send only the access token in the Cookie header. The patched
    # transport sees Cookie is already set and skips auto-injection,
    # so vg_csrf is absent from the request.
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "X",
            "topic": "Y",
            "surveillance_type": "technological",
            "language": "en",
        },
        headers={"Cookie": f"{settings.ACCESS_TOKEN_COOKIE}={access}", "X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403, resp.text
    assert "CSRF" in resp.json().get("detail", "")


# ── 6. Safe methods and exempt paths ─────────────────────────────────


@pytest.mark.asyncio
async def test_csrf_get_unaffected(client: AsyncClient):
    """GET /auth/me works without X-CSRF-Token."""
    await client.post("/api/v1/auth/register", json={
        "email": "csrf-get@example.com",
        "name": "Get",
        "password": "secure123",
        "organization_name": "Get Org",
    })
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_csrf_options_unaffected(client: AsyncClient):
    """OPTIONS preflight is not subject to the CSRF check."""
    # A preflight with Origin and Access-Control-Request-Method.
    resp = await client.options(
        "/api/v1/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    # 200 or 204 are both valid CORS preflight responses. Must NOT be 403.
    assert resp.status_code in (200, 204), \
        f"OPTIONS preflight returned {resp.status_code}; CSRF must not block it"


@pytest.mark.asyncio
async def test_csrf_auth_endpoints_exempt(client: AsyncClient):
    """login / register / refresh POSTs pass without X-CSRF-Token."""
    # /auth/register on a fresh client (no vg_csrf yet) should still work.
    reg = await client.post("/api/v1/auth/register", json={
        "email": "csrf-exempt@example.com",
        "name": "Exempt",
        "password": "secure123",
        "organization_name": "Exempt Org",
    })
    assert reg.status_code == 201, reg.text

    # /auth/login should also work without any CSRF token.
    log = await client.post("/api/v1/auth/login", json={
        "email": "csrf-exempt@example.com",
        "password": "secure123",
    })
    assert log.status_code == 200, log.text

    # /auth/refresh should also work.
    ref = await client.post("/api/v1/auth/refresh")
    assert ref.status_code == 200, ref.text


@pytest.mark.asyncio
async def test_csrf_health_unaffected(client: AsyncClient):
    """/health is not subject to the CSRF check."""
    resp = await client.get("/health")
    assert resp.status_code == 200, resp.text


# ── 7. Pure-function sanity for `secrets.token_urlsafe(32) ───────────


def test_token_shape():
    """secrets.token_urlsafe(32) → 43-char URL-safe token."""
    token = secrets.token_urlsafe(32)
    assert len(token) == 43
    import string
    alphabet = string.ascii_letters + string.digits + "-_"
    for ch in token:
        assert ch in alphabet
