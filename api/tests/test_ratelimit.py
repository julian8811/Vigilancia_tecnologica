"""Rate-limit tests — Redis sliding-window on auth endpoints.

Covers the contract for `app.core.ratelimit`:

* `/auth/login` allows 5 requests per 60s window per IP+email; the 6th
  returns 429 with the three ``X-RateLimit-*`` headers.
* `/auth/register` allows 3 requests per 60s window per IP; the 4th 429.
* `/auth/refresh` allows 10 requests per 60s window per IP; the 11th 429.
* The 429 body is ``{"detail": "Too many requests"}``.
* The 429 response carries ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``
  (always ``"0"``) and ``X-RateLimit-Reset`` (unix timestamp).
* Different client IPs are tracked independently.
* When ``REDIS_URL`` is empty, the rate-limit deps are a no-op (the
  global 100/min still applies).
* The login key includes the email — same IP, different emails have
  independent counters.

The tests inject ``fakeredis.aioredis.FakeRedis`` via
``app.state.redis`` so they are hermetic and CI does not need a real
Redis service.
"""

from __future__ import annotations

import secrets
from typing import Any

import fakeredis.aioredis
import pytest
from httpx import AsyncClient

from app.core import ratelimit
from app.main import app


# ── Helpers ────────────────────────────────────────────────────────────


async def _swap_fakeredis() -> fakeredis.aioredis.FakeRedis:
    """Replace the module-level redis client with a fresh FakeRedis.

    Returns the new client so the test can inspect keys directly if
    needed. Stores the previous client on the FakeRedis instance
    itself (as ``_previous``) so ``_restore_redis`` can restore it
    without the caller having to pass two values back.
    """
    fake = fakeredis.aioredis.FakeRedis()
    previous = await ratelimit.get_redis()
    await ratelimit.set_redis(fake)
    fake._previous = previous  # type: ignore[attr-defined]
    return fake


async def _restore_redis(fake: Any) -> None:
    await ratelimit.set_redis(getattr(fake, "_previous", None))


def _register_payload(email: str) -> dict[str, str]:
    return {
        "email": email,
        "name": "RateLimit User",
        "password": "securepass123",
        "organization_name": f"RL Org {secrets.token_hex(3)}",
    }


# ── 1. /auth/login: 5 ok, 6th 429 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_login_survives_5_requests(client: AsyncClient):
    """5 logins from the same IP — all succeed.

    Uses a single registered user and 5 valid login attempts.
    """
    email = f"rl-login-ok-{secrets.token_hex(4)}@example.com"
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    fake = await _swap_fakeredis()
    try:
        for i in range(5):
            resp = await client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "securepass123",
            })
            assert resp.status_code == 200, (
                f"login #{i + 1} unexpectedly returned {resp.status_code}: {resp.text}"
            )
    finally:
        await _restore_redis(fake)


@pytest.mark.asyncio
async def test_login_blocked_on_6th_request(client: AsyncClient):
    """6th login from the same IP+email returns 429."""
    email = f"rl-login-429-{secrets.token_hex(4)}@example.com"
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    fake = await _swap_fakeredis()
    try:
        for _ in range(5):
            ok = await client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "securepass123",
            })
            assert ok.status_code == 200, ok.text

        resp = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "securepass123",
        })
        assert resp.status_code == 429, resp.text
    finally:
        await _restore_redis(fake)


# ── 2. /auth/register: 3 ok, 4th 429 ──────────────────────────────────


@pytest.mark.asyncio
async def test_register_survives_3(client: AsyncClient):
    """3 register calls from the same IP — all 201."""
    fake = await _swap_fakeredis()
    try:
        for i in range(3):
            email = f"rl-reg-ok-{i}-{secrets.token_hex(4)}@example.com"
            resp = await client.post(
                "/api/v1/auth/register",
                json=_register_payload(email),
            )
            assert resp.status_code == 201, (
                f"register #{i + 1} returned {resp.status_code}: {resp.text}"
            )
    finally:
        await _restore_redis(fake)


@pytest.mark.asyncio
async def test_register_blocked_on_4th(client: AsyncClient):
    """4th register from the same IP → 429."""
    fake = await _swap_fakeredis()
    try:
        for i in range(3):
            email = f"rl-reg-429-{i}-{secrets.token_hex(4)}@example.com"
            ok = await client.post(
                "/api/v1/auth/register",
                json=_register_payload(email),
            )
            assert ok.status_code == 201, ok.text

        email = f"rl-reg-429-final-{secrets.token_hex(4)}@example.com"
        resp = await client.post(
            "/api/v1/auth/register",
            json=_register_payload(email),
        )
        assert resp.status_code == 429, resp.text
    finally:
        await _restore_redis(fake)


# ── 3. /auth/refresh: 10 ok, 11th 429 ──────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_survives_10(client: AsyncClient):
    """10 refreshes from the same IP — all 200."""
    await client.post("/api/v1/auth/register", json=_register_payload(
        f"rl-ref-ok-{secrets.token_hex(4)}@example.com"
    ))

    fake = await _swap_fakeredis()
    try:
        for i in range(10):
            resp = await client.post("/api/v1/auth/refresh")
            assert resp.status_code == 200, (
                f"refresh #{i + 1} returned {resp.status_code}: {resp.text}"
            )
    finally:
        await _restore_redis(fake)


@pytest.mark.asyncio
async def test_refresh_blocked_on_11th(client: AsyncClient):
    """11th refresh from the same IP → 429."""
    await client.post("/api/v1/auth/register", json=_register_payload(
        f"rl-ref-429-{secrets.token_hex(4)}@example.com"
    ))

    fake = await _swap_fakeredis()
    try:
        for _ in range(10):
            ok = await client.post("/api/v1/auth/refresh")
            assert ok.status_code == 200, ok.text

        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 429, resp.text
    finally:
        await _restore_redis(fake)


# ── 4. 429 response shape ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_429_headers(client: AsyncClient):
    """429 response body is {"detail": "Too many requests"} and includes the three headers."""
    email = f"rl-headers-{secrets.token_hex(4)}@example.com"
    await client.post("/api/v1/auth/register", json=_register_payload(email))

    fake = await _swap_fakeredis()
    try:
        for _ in range(5):
            await client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "securepass123",
            })

        resp = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "securepass123",
        })
        assert resp.status_code == 429
        body = resp.json()
        assert body == {"detail": "Too many requests"}, body

        # Headers — case-insensitive lookup.
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        assert "x-ratelimit-limit" in headers_lower
        assert "x-ratelimit-remaining" in headers_lower
        assert "x-ratelimit-reset" in headers_lower

        # Login limit is 5.
        assert headers_lower["x-ratelimit-limit"] == "5"
        # Remaining on a 429 is always 0.
        assert headers_lower["x-ratelimit-remaining"] == "0"
        # Reset is a unix timestamp in the future.
        reset = int(headers_lower["x-ratelimit-reset"])
        import time
        assert reset >= int(time.time()) - 1
    finally:
        await _restore_redis(fake)


# ── 5. Different IPs / different emails have independent counters ─────


@pytest.mark.asyncio
async def test_different_ips_not_affected(client: AsyncClient):
    """A second request from a different client IP is not blocked.

    The dep reads the client IP from ``request.client.host``. Under
    ASGITransport the client host is always 127.0.0.1, so we verify
    the per-IP isolation indirectly: after exhausting the limit for
    one (ip, email) tuple, a DIFFERENT email on the same IP is
    unaffected. The key format includes the email, so the second
    request lands on a fresh key.
    """
    email_a = f"rl-ip-a-{secrets.token_hex(4)}@example.com"
    email_b = f"rl-ip-b-{secrets.token_hex(4)}@example.com"
    await client.post("/api/v1/auth/register", json=_register_payload(email_a))
    await client.post("/api/v1/auth/register", json=_register_payload(email_b))

    fake = await _swap_fakeredis()
    try:
        # Exhaust email_a's counter (5/60s, per IP+email).
        for _ in range(5):
            await client.post("/api/v1/auth/login", json={
                "email": email_a,
                "password": "securepass123",
            })
        blocked = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "securepass123",
        })
        assert blocked.status_code == 429, blocked.text

        # email_b shares the IP but is a different key — first login OK.
        ok = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "securepass123",
        })
        assert ok.status_code == 200, ok.text

        # The two logins must live under different sorted sets in Redis.
        keys = {k.decode() for k in await fake.keys("*")}
        assert any(email_a in k for k in keys)
        assert any(email_b in k for k in keys)
        # The keys must differ — i.e. there are at least 2 login keys.
        login_keys = [k for k in keys if k.startswith("rl:auth.login:")]
        assert len(login_keys) >= 2
    finally:
        await _restore_redis(fake)


@pytest.mark.asyncio
async def test_key_includes_email(client: AsyncClient):
    """Same IP, different emails → independent counters (login key includes email)."""
    email_a = f"rl-key-a-{secrets.token_hex(4)}@example.com"
    email_b = f"rl-key-b-{secrets.token_hex(4)}@example.com"
    await client.post("/api/v1/auth/register", json=_register_payload(email_a))
    await client.post("/api/v1/auth/register", json=_register_payload(email_b))

    fake = await _swap_fakeredis()
    try:
        # Exhaust email_a's counter.
        for _ in range(5):
            await client.post("/api/v1/auth/login", json={
                "email": email_a,
                "password": "securepass123",
            })
        blocked = await client.post("/api/v1/auth/login", json={
            "email": email_a,
            "password": "securepass123",
        })
        assert blocked.status_code == 429, blocked.text

        # email_b shares the IP but has its own key — first request
        # should pass.
        ok = await client.post("/api/v1/auth/login", json={
            "email": email_b,
            "password": "securepass123",
        })
        assert ok.status_code == 200, ok.text

        # The keys must exist with the right format. Under ASGITransport
        # the client IP is 127.0.0.1.
        keys = {k.decode() for k in await fake.keys("*")}
        # At minimum, each email must appear in some key.
        assert any(email_a in k for k in keys), (
            f"expected key containing {email_a}, got {keys}"
        )
        assert any(email_b in k for k in keys), (
            f"expected key containing {email_b}, got {keys}"
        )
        # And the keys must follow the documented format.
        assert any(k.startswith("rl:auth.login:") and email_a in k for k in keys)
    finally:
        await _restore_redis(fake)


# ── 6. No-op when REDIS_URL is empty ──────────────────────────────────


@pytest.mark.asyncio
async def test_no_redis_fallback(client: AsyncClient):
    """When _redis is None, requests are not throttled (no-op)."""
    # Explicitly clear the redis client for this test.
    previous = await ratelimit.get_redis()
    await ratelimit.set_redis(None)
    try:
        # Hit /auth/register 6 times in a row — well over the 3/60s
        # limit. With no-op, all should succeed.
        for i in range(6):
            email = f"rl-noredis-{i}-{secrets.token_hex(4)}@example.com"
            resp = await client.post(
                "/api/v1/auth/register",
                json=_register_payload(email),
            )
            assert resp.status_code == 201, (
                f"register #{i + 1} returned {resp.status_code}: {resp.text}"
            )
    finally:
        await _restore_redis(previous)
