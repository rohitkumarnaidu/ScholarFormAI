# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache.redis_cache import RedisCache
from app.security.jwks_verifier import verify_jwt

logger = logging.getLogger(__name__)


class TierRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Tier-aware daily rate limiting for guest uploads and generation starts.

    - Guest: 5 requests/day (UTC)
    - Authenticated users: unlimited for now
    """

    def __init__(self, app, guest_daily_limit: int = 5):
        super().__init__(app)
        self.guest_daily_limit = int(guest_daily_limit)
        self._redis = RedisCache().client
        self._memory_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self._redis_warning_logged = False

    def _should_skip(self, request: Request) -> bool:
        path = request.url.path or ""
        if path.startswith("/health") or path.startswith("/ready"):
            return True
        if "/status" in path:
            return True
        if path.startswith("/api/v1/templates"):
            return True
        if path.startswith("/api/v1/health"):
            return True
        return False

    def _is_limited_endpoint(self, request: Request) -> bool:
        if request.method != "POST":
            return False
        path = request.url.path or ""
        return path in {
            "/api/v1/documents/upload",
            "/api/v1/generator/sessions",
        }

    def _get_user_id(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        token = auth_header[7:].strip()
        if not token:
            return None
        try:
            payload = verify_jwt(token)
            return payload.get("sub")
        except Exception:
            return None

    def _utc_day_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    def _seconds_until_next_day(self) -> int:
        now = datetime.now(timezone.utc)
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

        user_id = self._get_user_id(request)
        if user_id:
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
