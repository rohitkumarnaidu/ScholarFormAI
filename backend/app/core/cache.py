import hashlib
import json
import logging
import pickle
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def clear(self) -> bool: ...

    @abstractmethod
    def get_many(self, keys: list[str]) -> dict[str, Any]: ...

    @abstractmethod
    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool: ...

    @abstractmethod
    def increment(self, key: str, amount: int = 1) -> int: ...

    def make_key(self, prefix: str, key: str) -> str:
        if len(key) > 200:
            key = hashlib.sha256(key.encode()).hexdigest()
        return f"{prefix}:{key}"


class MemoryCache(CacheBackend):
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300, max_items: int = 10000, cleanup_interval: int = 60):
        self.default_ttl = default_ttl
        self.max_items = max_items
        self.cleanup_interval = cleanup_interval
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._last_cleanup = time.time()

    def _cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if exp < now]
            for k in expired:
                del self._store[k]
            self._last_cleanup = now
            if expired:
                logger.debug("Cache cleanup: removed %d expired entries", len(expired))

    def get(self, key: str) -> Any | None:
        self._cleanup()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if expiry < time.time():
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._cleanup()
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl
        with self._lock:
            if len(self._store) >= self.max_items and key not in self._store:
                self._evict()
            self._store[key] = (value, expiry)
        return True

    def _evict(self) -> None:
        if not self._store:
            return
        oldest_key = min(self._store.keys(), key=lambda k: self._store[k][1])
        del self._store[oldest_key]

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        self._cleanup()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            return entry[1] >= time.time()

    def clear(self) -> bool:
        with self._lock:
            self._store.clear()
        logger.debug("Cache cleared")
        return True

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        for key, value in mapping.items():
            self.set(key, value, ttl)
        return True

    def increment(self, key: str, amount: int = 1) -> int:
        with self._lock:
            entry = self._store.get(key)
            if entry is None or entry[1] < time.time():
                self._store[key] = (amount, time.time() + self.default_ttl)
                return amount
            new_value = entry[0] + amount
            self._store[key] = (new_value, entry[1])
            return new_value

    @property
    def size(self) -> int:
        self._cleanup()
        with self._lock:
            return len(self._store)

    @property
    def stats(self) -> dict[str, Any]:
        self._cleanup()
        with self._lock:
            now = time.time()
            active = sum(1 for _, exp in self._store.values() if exp >= now)
            return {
                "backend": "memory",
                "total_entries": len(self._store),
                "active_entries": active,
                "max_items": self.max_items,
                "default_ttl": self.default_ttl,
            }


class RedisCache(CacheBackend):
    """Redis-backed cache implementation."""

    def __init__(self, redis_url: str = "", default_ttl: int = 300, key_prefix: str = "amf"):
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client = None
        self._available = False

        redis_url = redis_url or settings.REDIS_URL
        if redis_url:
            self._connect(redis_url)

    def _connect(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._available = True
            logger.info("Redis cache connected to %s", redis_url)
        except ImportError:
            logger.warning("redis-py not installed. Install with: pip install redis")
            self._available = False
        except Exception as exc:
            logger.warning("Redis connection failed: %s", exc)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    def _prefix_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}" if self.key_prefix else key

    def get(self, key: str) -> Any | None:
        import asyncio

        try:
            if not self.available:
                return None
            result = asyncio.run(self._client.get(self._prefix_key(key)))
            if result is None:
                return None
            return pickle.loads(result) if isinstance(result, bytes) else json.loads(result)  # nosec B301
        except Exception as exc:
            logger.debug("Redis get failed: %s", exc)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        import asyncio

        try:
            if not self.available:
                return False
            ttl = ttl if ttl is not None else self.default_ttl
            serialized = json.dumps(value, default=str)
            asyncio.run(self._client.setex(self._prefix_key(key), ttl, serialized))
            return True
        except Exception as exc:
            logger.debug("Redis set failed: %s", exc)
            return False

    def delete(self, key: str) -> bool:
        import asyncio

        try:
            if not self.available:
                return False
            result = asyncio.run(self._client.delete(self._prefix_key(key)))
            return result > 0
        except Exception as exc:
            logger.debug("Redis delete failed: %s", exc)
            return False

    def exists(self, key: str) -> bool:
        import asyncio

        try:
            if not self.available:
                return False
            result = asyncio.run(self._client.exists(self._prefix_key(key)))
            return result > 0
        except Exception as exc:
            logger.debug("Redis exists failed: %s", exc)
            return False

    def clear(self) -> bool:
        import asyncio

        try:
            if not self.available:
                return False
            asyncio.run(self._client.flushdb())
            return True
        except Exception as exc:
            logger.debug("Redis flush failed: %s", exc)
            return False

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        import asyncio

        try:
            if not self.available:
                return {}
            prefixed = {self._prefix_key(k): k for k in keys}
            results = asyncio.run(self._client.mget(list(prefixed.keys())))
            return {
                prefixed[orig_key]: json.loads(val)
                for orig_key, val in zip(prefixed.keys(), results, strict=False)
                if val is not None
            }
        except Exception as exc:
            logger.debug("Redis mget failed: %s", exc)
            return {}

    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> bool:
        import asyncio

        try:
            if not self.available:
                return False
            ttl = ttl if ttl is not None else self.default_ttl
            pipe = self._client.pipeline()
            for key, value in mapping.items():
                pipe.setex(self._prefix_key(key), ttl, json.dumps(value, default=str))
            asyncio.run(pipe.execute())
            return True
        except Exception as exc:
            logger.debug("Redis mset failed: %s", exc)
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        import asyncio

        try:
            if not self.available:
                return 0
            result = asyncio.run(self._client.incrby(self._prefix_key(key), amount))
            return result
        except Exception as exc:
            logger.debug("Redis increment failed: %s", exc)
            return 0

    @property
    def stats(self) -> dict[str, Any]:
        import asyncio

        try:
            if not self.available:
                return {"backend": "redis", "available": False}
            info = asyncio.run(self._client.info())
            return {
                "backend": "redis",
                "available": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "total_connections": info.get("total_connections_received", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception:
            return {"backend": "redis", "available": False}


def cache(
    ttl: int = 300,
    key_prefix: str = "",
    backend: CacheBackend | None = None,
) -> Callable[[F], F]:
    """Decorator to cache function results. Works with sync and async functions."""

    def decorator(func: F) -> F:
        import asyncio
        import functools

        cache_backend = backend or _default_cache_backend()

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_cache_key(func, key_prefix, args, kwargs)
                cached = cache_backend.get(cache_key)
                if cached is not None:
                    logger.debug("Cache hit: %s", cache_key)
                    return cached
                result = await func(*args, **kwargs)
                cache_backend.set(cache_key, result, ttl)
                logger.debug("Cache set: %s (ttl=%d)", cache_key, ttl)
                return result

            return async_wrapper  # type: ignore
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_cache_key(func, key_prefix, args, kwargs)
                cached = cache_backend.get(cache_key)
                if cached is not None:
                    logger.debug("Cache hit: %s", cache_key)
                    return cached
                result = func(*args, **kwargs)
                cache_backend.set(cache_key, result, ttl)
                logger.debug("Cache set: %s (ttl=%d)", cache_key, ttl)
                return result

            return sync_wrapper  # type: ignore

    return decorator


def invalidate_cache(key_prefix: str, backend: CacheBackend | None = None) -> None:
    """Invalidate all cache entries matching a key prefix."""
    cb = backend or _default_cache_backend()
    if isinstance(cb, MemoryCache):
        with cb._lock:
            keys_to_delete = [k for k in cb._store if k.startswith(key_prefix)]
            for k in keys_to_delete:
                del cb._store[k]
            if keys_to_delete:
                logger.debug(
                    "Cache invalidated: %d entries with prefix '%s'",
                    len(keys_to_delete),
                    key_prefix,
                )
    elif isinstance(cb, RedisCache) and cb.available:
        import asyncio

        try:
            cursor = 0
            pattern = f"{cb.key_prefix}:{key_prefix}*"
            while True:
                cursor, keys = asyncio.run(cb._client.scan(cursor=cursor, match=pattern, count=100))
                if keys:
                    asyncio.run(cb._client.delete(*keys))
                if cursor == 0:
                    break
            logger.debug("Redis cache invalidated for prefix '%s'", key_prefix)
        except Exception as exc:
            logger.warning("Redis cache invalidation error: %s", exc)


def _build_cache_key(func: Callable, prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    func_key = f"{func.__module__}.{func.__qualname__}"
    arg_hash = hashlib.md5(pickle.dumps((args, kwargs))).hexdigest()  # nosec B301 B324
    return f"{prefix}:{func_key}:{arg_hash}" if prefix else f"{func_key}:{arg_hash}"


_cache_instance: CacheBackend | None = None


def get_cache_backend() -> CacheBackend:
    global _cache_instance
    if _cache_instance is not None:
        return _cache_instance
    if settings.REDIS_URL:
        _cache_instance = RedisCache(redis_url=settings.REDIS_URL)
        if _cache_instance.available:
            return _cache_instance
    _cache_instance = MemoryCache()
    logger.info("Using memory cache backend")
    return _cache_instance


def _default_cache_backend() -> CacheBackend:
    return get_cache_backend()
