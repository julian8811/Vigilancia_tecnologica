"""Redis-backed sliding-window rate limiter for auth endpoints.

The limiter is implemented as a FastAPI dependency factory. Each call
to ``build_limiter`` returns a dependency that enforces a sliding-window
rate limit using a Redis sorted set:

* ``ZADD key now <unique-member>`` records the current request.
* ``ZREMRANGEBYSCORE key 0 (now - window)`` drops entries that fell
  outside the window.
* ``ZCARD key`` returns the count of requests in the window.
* ``EXPIRE key window`` lets the key self-evict when idle.

The member MUST be unique per call (e.g. ``f"{now_ms}-{uuid4()}"``).
Using the score as the member would cause back-to-back requests in
the same millisecond to overwrite each other in the sorted set and
the count would never increase. The unique-member trick is what
makes the sliding window correct.

The four operations are wrapped in a Lua script so they execute
atomically on the Redis side — no risk of a concurrent request
slipping between the count and the add.

Keys:
* ``rl:{endpoint}:{ip}`` for register and refresh.
* ``rl:{endpoint}:{ip}:{email}`` for login (so a single attacker
  cannot lock out a victim by spamming their email; the email is
  included in the key so different credentials on the same IP get
  independent counters).

No-op behavior:
* If ``_redis`` is ``None`` (i.e. ``settings.REDIS_URL`` is empty at
  startup), the dep logs a single ``rate_limit_disabled`` warning and
  returns ``None`` (the request continues). The app boots and serves
  traffic without Redis.

429 response:
* ``{"detail": "Too many requests"}`` with the three
  ``X-RateLimit-Limit``, ``X-RateLimit-Remaining`` and
  ``X-RateLimit-Reset`` headers.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Module-level singleton: set at startup if REDIS_URL is configured.
# Public for test monkey-patching and for the main.py lifespan to
# populate it on boot. Tests inject a ``fakeredis.aioredis.FakeRedis``
# instance via ``set_redis`` in a fixture.
_redis: Any = None  # redis.asyncio.Redis | None

# Logged once at module level (NOT in the dep body) to avoid a flood
# when a 100 RPS attacker hits a non-Redis deployment.
_disabled_logged: bool = False

# Lua script: atomic sliding-window counter on a sorted set.
# KEYS[1] = the per-client key
# ARGV[1] = now in milliseconds (string)
# ARGV[2] = window in milliseconds (string)
# ARGV[3] = a unique member (uuid string) so back-to-back requests
#           in the same millisecond don't overwrite each other.
LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local member = ARGV[3]
redis.call('ZADD', key, now, member)
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
redis.call('EXPIRE', key, math.floor(window / 1000))
return count
"""


async def set_redis(client: Any) -> None:
    """Replace the module-level Redis client (used by tests and startup)."""
    global _redis
    _redis = client


async def get_redis() -> Any:
    """Return the current Redis client (or ``None`` when disabled)."""
    return _redis


def _client_ip(request: Request) -> str:
    """Extract the client IP from a request, falling back to ``"unknown"``."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _parse_email_from_body(request: Request) -> str:
    """Best-effort email extraction for the login key.

    The body is re-parsed here even though the route handler will
    parse it again — Starlette caches the body in ``request._body``,
    so reading it twice is a no-op after the first parse.

    If the body is missing, malformed, or not JSON, the email is
    ``"unknown"`` — the key still isolates the IP from the broader
    server-side traffic.
    """
    try:
        body = getattr(request, "_body", None)
        if not body:
            return "unknown"
        import json
        data = json.loads(body)
        email = data.get("email")
        if isinstance(email, str) and email:
            return email
    except (ValueError, AttributeError):
        pass
    return "unknown"


def _build_429(limit: int, reset_at: int) -> JSONResponse:
    """Return the standard 429 JSONResponse with the three headers."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
        headers={
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_at),
        },
    )


def build_limiter(
    endpoint: str,
    limit: int,
    window_seconds: int,
    *,
    key_includes_email: bool = False,
) -> Callable[[Request], Any]:
    """Return a FastAPI dependency that enforces a sliding-window limit.

    The returned dependency:

    * Returns ``None`` on success (FastAPI ignores the return type).
    * Returns a ``JSONResponse(429, ...)`` when the limit is exceeded.
    * Is a no-op when ``_redis`` is ``None`` (logs once at startup).

    The dep is intentionally async to match FastAPI's expectation;
    ``time.time()`` is non-blocking so we don't need a real awaitable
    clock source.
    """
    window_ms = window_seconds * 1000

    async def _deps(request: Request) -> Response | None:
        global _disabled_logged

        r = await get_redis()
        if r is None:
            if not _disabled_logged:
                logger.warning(
                    "rate_limit_disabled: REDIS_URL not set; rate limiting is a no-op"
                )
                _disabled_logged = True
            return None

        ip = _client_ip(request)
        key = f"rl:{endpoint}:{ip}"
        if key_includes_email:
            email = _parse_email_from_body(request)
            key = f"{key}:{email}"

        now_seconds = time.time()
        now_ms = int(now_seconds * 1000)
        reset_at = int(now_seconds) + window_seconds
        member = f"{now_ms}-{uuid.uuid4().hex}"

        try:
            count = await r.eval(
                LUA_SCRIPT, 1, key, str(now_ms), str(window_ms), member
            )
        except Exception as exc:
            # Fail-open: if Redis is unreachable mid-request we do
            # not want to lock everyone out. Log and continue.
            logger.warning("rate_limit_error: %s", exc, exc_info=True)
            return None

        if int(count) > limit:
            return _build_429(limit, reset_at)

        return None

    return _deps


# ── Pre-built limiters ─────────────────────────────────────────────────

# 5 requests per 60 seconds per IP+email. Including the email means
# an attacker cannot lock out a victim by repeatedly POSTing to
# /auth/login with the victim's email — the victim's legitimate
# logins live under a different key.
login_rate_limit = build_limiter(
    "auth.login", limit=5, window_seconds=60, key_includes_email=True
)

# 3 requests per 60 seconds per IP. Brute-force account creation is
# the main concern here.
register_rate_limit = build_limiter(
    "auth.register", limit=3, window_seconds=60
)

# 10 requests per 60 seconds per IP. Refresh is a cheap endpoint
# (validates a JWT) so we allow a higher rate, but still cap it to
# limit replay attacks.
refresh_rate_limit = build_limiter(
    "auth.refresh", limit=10, window_seconds=60
)
