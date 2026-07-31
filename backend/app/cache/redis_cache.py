# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import redis
import json
import logging
import hashlib
from typing import Optional, Any

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based caching service for document processing results.
    Uses lazy initialization - client is created on first use, not at import time.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, redis_url: str | None = None):
        self._client: Optional[redis.Redis] = None
        self._initialized = False
        self._init_kwargs = {"host": host, "port": port, "db": db}
        if redis_url is not None:
            self._init_kwargs["redis_url"] = redis_url

    def _ensure_client(self) -> Optional[redis.Redis]:
        """Lazily create the Redis client on first use."""
        if self._initialized:
            return self._client

        self._initialized = True

        try:
            from app.config.settings import settings

            redis_enabled = bool(getattr(settings, "REDIS_ENABLED", False))
        except Exception:
            redis_enabled = False

        if not redis_enabled:
            logger.info("Redis cache disabled via REDIS_ENABLED=false. Using in-memory/no-cache mode.")
            self._client = None
            return self._client

        try:
            from app.config.settings import settings

            redis_url = (
                getattr(settings, "REDIS_URL", None)
                or f"redis://{getattr(settings, 'REDIS_HOST', 'localhost')}:{int(getattr(settings, 'REDIS_PORT', 6379))}"
            )
            self._client = redis.Redis.from_url(
                redis_url,
                db=self._init_kwargs["db"],
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
                retry_on_timeout=False,
            )
            self._client.ping()
            logger.info("Connected to Redis at %s", redis_url)
        except Exception as e:
            logger.info("Redis cache unavailable (%s). Caching disabled; pipeline continues normally.", e)
            self._client = None

        return self._client

    @property
    def client(self) -> Optional[redis.Redis]:
        return self._ensure_client()

    def _generate_key(self, content: str, prefix: str = "grobid") -> str:
        """Generate a deterministic key based on content hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"{prefix}:{content_hash}"

    def get_grobid_result(self, file_content: str) -> Optional[dict]:
        """Retrieve cached GROBID results for the given file content."""
        client = self._ensure_client()
        if not client:
            return None

        key = self._generate_key(file_content)
        try:
            cached_data = client.get(key)
            if cached_data:
                logger.info(f"Cache hit for key: {key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error reading from Redis cache: {e}")

        return None

    def set_grobid_result(self, file_content: str, result: dict, ttl: int = 3600):
        """Cache GROBID results for the given file content with TTL."""
        client = self._ensure_client()
        if not client:
            return

        key = self._generate_key(file_content)
        try:
            client.setex(key, ttl, json.dumps(result))
            logger.info(f"Cached results for key: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error writing to Redis cache: {e}")

    def get_llm_result(self, cache_key: str) -> Optional[str]:
        """Retrieve cached LLM result."""
        client = self._ensure_client()
        if not client:
            return None
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                logger.info(f"LLM Cache hit for key: {cache_key}")
                return cached_data
        except Exception as e:
            logger.error(f"Error reading from LLM Redis cache: {e}")
        return None

    def set_llm_result(self, cache_key: str, text: str, ttl: int = 86400):
        """Cache LLM text result for 24h by default."""
        client = self._ensure_client()
        if not client:
            return
        try:
            client.setex(cache_key, ttl, text)
            logger.info(f"Cached LLM results for key: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error writing to LLM Redis cache: {e}")

    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        client = self._ensure_client()
        if not client:
            return
        try:
            client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting from Redis cache: {e}")

    def clear(self) -> None:
        """Clear all cached entries."""
        client = self._ensure_client()
        if not client:
            return
        try:
            client.flushdb()
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")

    def health(self) -> dict:
        """Return cache health status."""
        client = self._ensure_client()
        if not client:
            return {"status": "unavailable"}
        try:
            client.ping()
            return {"status": "available"}
        except Exception as e:
            return {"status": "unavailable", "detail": str(e)}


# Global instance - lazily initialized on first use
redis_cache = RedisCache()


def get_redis_cache() -> RedisCache:
    """Return the global RedisCache singleton."""
    return redis_cache
