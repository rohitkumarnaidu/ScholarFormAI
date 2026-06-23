# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Per-API-key rate limiter using Redis sliding window counters.
Enforces per-minute, per-hour, and per-day limits with 429 responses.
"""
import time
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: float
    retry_after: Optional[float] = None


class ApiKeyRateLimiter:
    """
    Sliding window rate limiter for user API keys.

    Uses Redis for distributed rate limiting with fallback to in-memory
    when Redis is unavailable.

    Keys stored in Redis:
    - api_key:{key_id}:min:{timestamp} — per-minute counter
    - api_key:{key_id}:hour:{timestamp} — per-hour counter
    - api_key:{key_id}:day:{date} — per-day counter
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory_limits: dict[str, dict] = {}

    def set_redis_client(self, redis_client) -> None:
        self._redis = redis_client

    def _get_redis(self):
        if self._redis is None:
            try:
                from app.cache.redis_cache import get_redis_cache
                cache = get_redis_cache()
                self._redis = cache.client
            except Exception:
                self._redis = None
        return self._redis

    def check_rate_limit(
        self,
        key_id: str,
        per_minute: int = 60,
        per_hour: int = 1000,
        per_day: int = 10000,
    ) -> RateLimitResult:
        redis = self._get_redis()
        if redis:
            return self._check_redis(redis, key_id, per_minute, per_hour, per_day)
        return self._check_memory(key_id, per_minute, per_hour, per_day)

    def _check_redis(self, redis, key_id: str, per_min: int, per_hour: int, per_day: int) -> RateLimitResult:
        now = time.time()
        minute_window = int(now) // 60
        hour_window = int(now) // 3600
        day_window = int(now) // 86400

        min_key = f"api_key:{key_id}:min:{minute_window}"
        hour_key = f"api_key:{key_id}:hour:{hour_window}"
        day_key = f"api_key:{key_id}:day:{day_window}"

        pipe = redis.pipeline()
        pipe.incr(min_key)
        pipe.expire(min_key, 120)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)
        pipe.incr(day_key)
        pipe.expire(day_key, 172800)
        results = pipe.execute()

        min_count = results[0]
        hour_count = results[2]
        day_count = results[4]

        if min_count > per_min:
            reset_at = (minute_window + 1) * 60
            return RateLimitResult(
                allowed=False,
                limit=per_min,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(0, reset_at - now),
            )
        if hour_count > per_hour:
            reset_at = (hour_window + 1) * 3600
            return RateLimitResult(
                allowed=False,
                limit=per_hour,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(0, reset_at - now),
            )
        if day_count > per_day:
            reset_at = (day_window + 1) * 86400
            return RateLimitResult(
                allowed=False,
                limit=per_day,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(0, reset_at - now),
            )

        remaining_minute = max(0, per_min - min_count)
        remaining_hour = max(0, per_hour - hour_count)
        remaining_day = max(0, per_day - day_count)

        return RateLimitResult(
            allowed=True,
            limit=min(per_min, per_hour, per_day),
            remaining=min(remaining_minute, remaining_hour, remaining_day),
            reset_at=(minute_window + 1) * 60,
        )

    def _check_memory(self, key_id: str, per_min: int, per_hour: int, per_day: int) -> RateLimitResult:
        now = time.time()
        minute_window = int(now) // 60
        hour_window = int(now) // 3600
        day_window = int(now) // 86400

        if key_id not in self._memory_limits:
            self._memory_limits[key_id] = {"min": {}, "hour": {}, "day": {}}

        limits = self._memory_limits[key_id]

        min_count = limits["min"].get(minute_window, 0) + 1
        hour_count = limits["hour"].get(hour_window, 0) + 1
        day_count = limits["day"].get(day_window, 0) + 1

        limits["min"][minute_window] = min_count
        limits["hour"][hour_window] = hour_count
        limits["day"][day_window] = day_count

        self._cleanup_memory(key_id, minute_window, hour_window, day_window)

        if min_count > per_min:
            reset_at = (minute_window + 1) * 60
            return RateLimitResult(
                allowed=False, limit=per_min, remaining=0,
                reset_at=reset_at, retry_after=max(0, reset_at - now),
            )
        if hour_count > per_hour:
            reset_at = (hour_window + 1) * 3600
            return RateLimitResult(
                allowed=False, limit=per_hour, remaining=0,
                reset_at=reset_at, retry_after=max(0, reset_at - now),
            )
        if day_count > per_day:
            reset_at = (day_window + 1) * 86400
            return RateLimitResult(
                allowed=False, limit=per_day, remaining=0,
                reset_at=reset_at, retry_after=max(0, reset_at - now),
            )

        return RateLimitResult(
            allowed=True,
            limit=min(per_min, per_hour, per_day),
            remaining=min(per_min - min_count, per_hour - hour_count, per_day - day_count),
            reset_at=(minute_window + 1) * 60,
        )

    def _cleanup_memory(self, key_id: str, min_w: int, hour_w: int, day_w: int) -> None:
        limits = self._memory_limits.get(key_id, {})
        for window_type, current_window in [("min", min_w), ("hour", hour_w), ("day", day_w)]:
            window_data = limits.get(window_type, {})
            stale = [w for w in window_data if w < current_window]
            for w in stale:
                del window_data[w]

    def get_usage(self, key_id: str) -> dict:
        redis = self._get_redis()
        if redis:
            return self._get_redis_usage(redis, key_id)
        return self._get_memory_usage(key_id)

    def _get_redis_usage(self, redis, key_id: str) -> dict:
        now = time.time()
        minute_window = int(now) // 60
        hour_window = int(now) // 3600
        day_window = int(now) // 86400

        min_key = f"api_key:{key_id}:min:{minute_window}"
        hour_key = f"api_key:{key_id}:hour:{hour_window}"
        day_key = f"api_key:{key_id}:day:{day_window}"

        pipe = redis.pipeline()
        pipe.get(min_key)
        pipe.get(hour_key)
        pipe.get(day_key)
        results = pipe.execute()

        return {
            "requests_this_minute": int(results[0] or 0),
            "requests_this_hour": int(results[1] or 0),
            "requests_today": int(results[2] or 0),
        }

    def _get_memory_usage(self, key_id: str) -> dict:
        limits = self._memory_limits.get(key_id, {})
        now = time.time()
        min_w = int(now) // 60
        hour_w = int(now) // 3600
        day_w = int(now) // 86400

        return {
            "requests_this_minute": limits.get("min", {}).get(min_w, 0),
            "requests_this_hour": limits.get("hour", {}).get(hour_w, 0),
            "requests_today": limits.get("day", {}).get(day_w, 0),
        }


_rate_limiter: Optional[ApiKeyRateLimiter] = None


def get_api_key_rate_limiter() -> ApiKeyRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ApiKeyRateLimiter()
    return _rate_limiter
