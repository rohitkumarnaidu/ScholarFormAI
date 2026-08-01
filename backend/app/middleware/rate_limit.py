# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Rate-limiting middleware.

Design goals:
  • Expose an in-memory `request_counts` dict (per-IP sliding window) so unit
    tests can inspect and seed it without a running Redis instance.
  • Optionally accelerate the count using Redis for multi-worker deployments;
    if Redis is unavailable the middleware falls back silently to in-memory.
  • Keep the module-level `redis` attribute so tests that patch it still work:
        with patch("app.middleware.rate_limit.redis", mock_redis): ...
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache.redis_cache import RedisCache
from app.config.settings import settings

# ---------------------------------------------------------------------------
# Module-level Redis client (lazily initialised, patched in tests)
# ---------------------------------------------------------------------------
REDIS_URL = settings.REDIS_URL
REDIS_ENABLED = bool(settings.REDIS_ENABLED)
_redis_backend = RedisCache()
redis = _redis_backend.client  # kept for test-patch compat
logger = logging.getLogger(__name__)


def _ensure_redis():
    """Return (and lazily create) the module-level redis client."""
    global redis
    if not REDIS_ENABLED:
        return None
    return redis


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiting middleware.

    Tracks requests using an in-memory dict (`request_counts`) — the primary
    source of truth for unit tests and single-worker deployments.  Redis is
    used as an optional distributed back-end; it is tried on every request
    and silently skipped if unavailable.

    Attributes
    ----------
    request_counts : Dict[str, List[float]]
        Maps each client IP to a list of request timestamps (epoch seconds)
        within the current sliding window.  Tests can read and write this
        directly to pre-seed state or verify counts.
    """

    WINDOW_SECONDS: int = 60  # sliding window size

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.uploads_per_minute = int(settings.UPLOADS_PER_MINUTE)
        # In-memory stores:
        # - request_counts keeps legacy/general API counters (used by tests)
        # - upload_request_counts isolates stricter upload limits from general traffic
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        self.upload_request_counts: dict[str, list[float]] = defaultdict(list)
        self._redis_warning_logged = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _in_memory_count(self, ip: str, *, is_upload: bool = False) -> int:
        """Evict stale timestamps and add a new one; return current count."""
        counter_store = self.upload_request_counts if is_upload else self.request_counts
        now = time.time()
        cutoff = now - self.WINDOW_SECONDS
        counter_store[ip] = [ts for ts in counter_store[ip] if ts > cutoff]
        counter_store[ip].append(now)
        return len(counter_store[ip])

    async def _redis_count(self, key: str) -> int | None:
        """Try to increment the Redis counter; return count or None on error."""
        if not REDIS_ENABLED:
            return None
        try:
            r = _ensure_redis()
            if r is None:
                return None
            count = r.incr(key)
            if inspect.isawaitable(count):
                count = await count
            count = int(count)
            if count == 1:
                expire_result = r.expire(key, self.WINDOW_SECONDS + 1)
                if inspect.isawaitable(expire_result):
                    await expire_result
            return count
        except Exception as exc:
            if not self._redis_warning_logged:
                logger.warning(
                    "Rate limiter: Redis unavailable (%s). Using in-memory count only.",
                    type(exc).__name__,
                )
                self._redis_warning_logged = True
            return None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Health checks are never rate-limited
        if request.url.path == "/health":
            return await call_next(request)

        is_upload = request.url.path == "/api/v1/documents/upload" and request.method == "POST"

        if is_upload:
            rate_subject = client_ip
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header[7:].strip()
                if raw_token:
                    token_fingerprint = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]
                    rate_subject = f"{client_ip}:{token_fingerprint}"
            limit = self.uploads_per_minute
            redis_key = f"ratelimit:upload:{rate_subject}:{int(time.time() / 60)}"
            error_msg = f"Maximum {limit} uploads per minute allowed."
        else:
            rate_subject = client_ip
            limit = self.requests_per_minute
            redis_key = f"ratelimit:general:{rate_subject}:{int(time.time() / 60)}"
            error_msg = f"Maximum {limit} requests per minute allowed."

        # Always update the in-memory window (tests rely on request_counts for general traffic)
        count = self._in_memory_count(rate_subject, is_upload=is_upload)

        # Optionally cross-check with Redis (for multi-worker accuracy)
        redis_count = await self._redis_count(redis_key)
        if redis_count is not None:
            count = max(count, redis_count)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": error_msg,
                    "retry_after": self.WINDOW_SECONDS,
                },
            )

        return await call_next(request)
