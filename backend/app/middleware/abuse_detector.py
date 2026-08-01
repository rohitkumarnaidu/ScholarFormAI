# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
import time
from collections import defaultdict

from app.cache.redis_cache import RedisCache
from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


class AbuseDetector:
    def __init__(self) -> None:
        self._redis = RedisCache().client
        self._memory: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._redis_warning_logged = False

    def _increment_bucket(self, key: str, window_seconds: int) -> int:
        if self._redis:
            try:
                bucket = int(time.time() / window_seconds)
                redis_key = f"{key}:{bucket}"
                count = self._redis.incr(redis_key)
                if count == 1:
                    self._redis.expire(redis_key, window_seconds + 5)
                return int(count)
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning("Abuse detector: Redis unavailable (%s). Using in-memory.", type(exc).__name__)
                    self._redis_warning_logged = True

        memory_key = (key, str(window_seconds))
        now = time.time()
        cutoff = now - window_seconds
        self._memory[memory_key] = [ts for ts in self._memory[memory_key] if ts > cutoff]
        self._memory[memory_key].append(now)
        return len(self._memory[memory_key])

    async def record_generation_request(self, ip_address: str) -> None:
        if not ip_address:
            ip_address = "unknown"
        count = self._increment_bucket(f"abuse:gen:{ip_address}", window_seconds=300)
        if count > 10:
            await audit_log_service.log(
                user_id=None,
                action="admin_action",
                resource_type="abuse_flag",
                resource_id=None,
                ip_address=ip_address,
                details={"type": "generation_spike", "count": count, "window_seconds": 300},
            )

    async def record_llm_call(self, user_id: str | None) -> None:
        subject = str(user_id) if user_id else "anonymous"
        count = self._increment_bucket(f"abuse:llm:{subject}", window_seconds=600)
        if count > 50:
            await audit_log_service.log(
                user_id=str(user_id) if user_id else None,
                action="admin_action",
                resource_type="abuse_flag",
                resource_id=None,
                ip_address=None,
                details={"type": "llm_overuse", "count": count, "window_seconds": 600},
            )


abuse_detector = AbuseDetector()
