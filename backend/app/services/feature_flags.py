# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Feature Flag Service — Database-backed feature flags with Redis caching.

Usage:
    from app.services.feature_flags import get_feature_flag

    if get_feature_flag("new_upload_flow", user_id="user-123"):
        # Show new upload flow
    else:
        # Show old upload flow
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# In-memory feature flag store (fallback when DB/Redis unavailable)
_DEFAULT_FLAGS: dict[str, Any] = {
    "new_upload_flow": False,
    "ai_suggestions": True,
    "batch_processing": True,
    "api_key_manager": True,
    "dark_mode_beta": False,
    "export_latex": True,
    "export_jats": False,
    "collaborative_editing": False,
    "advanced_analytics": False,
}


class FeatureFlagService:
    """Manages feature flags with DB persistence and Redis caching."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._cache: dict[str, Any] = dict(_DEFAULT_FLAGS)

    def get_flag(self, name: str, default: Any = None, user_id: str | None = None) -> Any:
        """
        Get a feature flag value.

        Resolution order:
        1. Redis cache (fastest)
        2. In-memory cache
        3. Database (authoritative)
        4. Default value
        """
        # Check Redis cache
        if self._redis:
            try:
                import redis

                r = self._redis if isinstance(self._redis, redis.Redis) else None
                if r:
                    cached = r.get(f"flag:{name}")
                    if cached is not None:
                        return json.loads(cached)
            except Exception:
                pass  # intentionally ignored

        # Check in-memory cache
        if name in self._cache:
            return self._cache[name]

        # Check database
        if self._db:
            try:
                value = self._load_from_db(name, user_id)
                if value is not None:
                    self._cache[name] = value
                    self._set_redis_cache(name, value)
                    return value
            except Exception:
                pass  # intentionally ignored

        return default if default is not None else _DEFAULT_FLAGS.get(name)

    def set_flag(self, name: str, value: Any, user_id: str | None = None) -> None:
        """Set a feature flag value."""
        self._cache[name] = value
        self._set_redis_cache(name, value)

        if self._db:
            try:
                self._save_to_db(name, value, user_id)
            except Exception as e:
                logger.error("Failed to save feature flag to DB: %s", e)

    def get_all_flags(self, user_id: str | None = None) -> dict[str, Any]:
        """Get all feature flags."""
        flags = dict(_DEFAULT_FLAGS)
        flags.update(self._cache)

        if self._db:
            try:
                db_flags = self._load_all_from_db(user_id)
                flags.update(db_flags)
            except Exception:
                pass  # intentionally ignored

        return flags

    def _set_redis_cache(self, name: str, value: Any) -> None:
        if self._redis:
            try:
                import redis

                r = self._redis if isinstance(self._redis, redis.Redis) else None
                if r:
                    r.setex(f"flag:{name}", 300, json.dumps(value))  # 5 min TTL
            except Exception:
                pass  # intentionally ignored

    def _load_from_db(self, name: str, user_id: str | None) -> Any | None:
        """Load flag from database. Override for actual DB implementation."""
        return None

    def _save_to_db(self, name: str, value: Any, user_id: str | None) -> None:
        """Save flag to database. Override for actual DB implementation."""
        pass

    def _load_all_from_db(self, user_id: str | None) -> dict:
        """Load all flags from database. Override for actual DB implementation."""
        return {}


_feature_service: FeatureFlagService | None = None


def get_feature_flag_service() -> FeatureFlagService:
    global _feature_service
    if _feature_service is None:
        _feature_service = FeatureFlagService()
    return _feature_service


def get_feature_flag(name: str, default: Any = None, user_id: str | None = None) -> Any:
    """Convenience function to get a feature flag."""
    return get_feature_flag_service().get_flag(name, default, user_id)
