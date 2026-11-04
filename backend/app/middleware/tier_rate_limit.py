# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache.redis_cache import RedisCache
from app.middleware.rbac import resolve_user_role
from app.security.jwks_verifier import verify_jwt

logger = logging.getLogger(__name__)


class TierRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Tier-aware daily rate limiting for guest uploads and generation starts,
    and per-minute rate limiting by user subscription tier for authenticated users.

    - Guest: 5 requests/day (UTC)
    - Free user: 60 requests/minute
    - Pro user: 300 requests/minute
    - Enterprise: 1000 requests/minute
    - Admin: unlimited
    """

    def __init__(self, app, guest_daily_limit: int = 5):
        super().__init__(app)
        self.guest_daily_limit = int(guest_daily_limit)
        self._redis = RedisCache().client
        self._memory_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._redis_warning_logged = False

    def _should_skip(self, request: Request) -> bool:
        path = request.url.path or ""
        if path.startswith("/health") or path.startswith("/ready"):
            return True
        if "/status" in path:
            return True
        if path.startswith("/api/v1/templates"):
            return True
        return bool(path.startswith("/api/v1/health"))

    def _is_limited_endpoint(self, request: Request) -> bool:
        if request.method != "POST":
            return False
        path = request.url.path or ""
        return path in {
            "/api/v1/documents/upload",
            "/api/v1/generator/sessions",
        }

    def _get_user_payload(self, request: Request) -> dict | None:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        token = auth_header[7:].strip()
        if not token:
            return None
        try:
            return verify_jwt(token)
        except Exception:
            return None

    def _get_user_id(self, request: Request) -> str | None:
        payload = self._get_user_payload(request)
        if isinstance(payload, dict):
            return payload.get("sub")
        return None

    def _utc_day_key(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%d")

    def _seconds_until_next_day(self) -> int:
        now = datetime.now(UTC)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((tomorrow - now).total_seconds())

    def _increment_guest_count(self, subject: str) -> int:
        day_key = self._utc_day_key()
        redis_key = f"tierlimit:guest:{subject}:{day_key}"
        if self._redis:
            try:
                count = self._redis.incr(redis_key)
                if count == 1:
                    self._redis.expire(redis_key, self._seconds_until_next_day())
                return int(count)
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning(
                        "Tier rate limit: Redis unavailable (%s). Using in-memory counts.", type(exc).__name__
                    )
                    self._redis_warning_logged = True

        memory_key = (subject, day_key)
        self._memory_counts[memory_key] += 1
        return self._memory_counts[memory_key]

    async def dispatch(self, request: Request, call_next):
        if self._should_skip(request) or not self._is_limited_endpoint(request):
            return await call_next(request)

        payload = self._get_user_payload(request)
        if payload and isinstance(payload, dict):
            user_id = payload.get("sub")
            if user_id:
                role = resolve_user_role(payload)
                if role == "admin":
                    return await call_next(request)

                tier_limits = {
                    "free": 60,
                    "pro": 300,
                    "enterprise": 1000,
                }
                limit = tier_limits.get(role, 60)
                if self._redis:
                    redis_key = f"ratelimit:user:{user_id}"
                    try:
                        count = self._redis.incr(redis_key)
                        if count == 1:
                            self._redis.expire(redis_key, 60)
                        if count > limit:
                            return JSONResponse(
                                status_code=429,
                                content={
                                    "error": "Rate limit exceeded",
                                    "upgrade_url": "/settings?tab=billing",
                                },
                            )
                    except Exception:
                        pass
                return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        count = self._increment_guest_count(client_ip)
        if count > self.guest_daily_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "upgrade_url": "/settings?tab=billing",
                },
            )

        return await call_next(request)
