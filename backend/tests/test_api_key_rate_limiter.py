import time
from unittest.mock import MagicMock, call, patch

import pytest


class TestRateLimitResult:
    def test_basic_construction(self):
        from app.services.api_key_rate_limiter import RateLimitResult

        r = RateLimitResult(allowed=True, limit=60, remaining=30, reset_at=1000.0)
        assert r.allowed is True
        assert r.retry_after is None


class TestGetRedis:
    def test_returns_none_when_unavailable(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        with patch("app.cache.redis_cache.get_redis_cache", side_effect=Exception("no redis")):
            assert limiter._get_redis() is None

    def test_lazy_loads_from_cache(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        mock_cache = MagicMock()
        mock_cache.client = "redis-client"
        with patch("app.cache.redis_cache.get_redis_cache", return_value=mock_cache):
            result = limiter._get_redis()
        assert result == "redis-client"
        assert limiter._redis == "redis-client"

    def test_returns_existing_client(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        limiter._redis = "existing"
        result = limiter._get_redis()
        assert result == "existing"


class TestSetRedisClient:
    def test_updates_client(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        limiter.set_redis_client("new-client")
        assert limiter._redis == "new-client"


class TestCheckRedis:
    @pytest.fixture
    def limiter(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        return ApiKeyRateLimiter(redis_client=MagicMock())

    def test_allows_within_limits(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [5, True, 50, True, 200, True]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is True
        assert result.remaining == 55

    def test_blocks_minute_limit(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [61, True, 50, True, 200, True]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.limit == 60
        assert result.retry_after is not None

    def test_blocks_hour_limit(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [5, True, 1001, True, 200, True]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is False
        assert result.limit == 1000

    def test_blocks_day_limit(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [5, True, 50, True, 10001, True]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is False
        assert result.limit == 10000

    def test_pipeline_commands(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [1, True, 1, True, 1, True]
        limiter._redis.pipeline.return_value = pipe
        limiter.check_rate_limit("key-1")
        min_key = "api_key:key-1:min:" + str(int(time.time()) // 60)
        hour_key = "api_key:key-1:hour:" + str(int(time.time()) // 3600)
        day_key = "api_key:key-1:day:" + str(int(time.time()) // 86400)
        pipe.incr.assert_has_calls([call(min_key), call(hour_key), call(day_key)])


class TestCheckMemory:
    @pytest.fixture
    def limiter(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        l = ApiKeyRateLimiter()
        l._get_redis = MagicMock(return_value=None)
        return l

    def test_allows_first_request(self, limiter):
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is True
        assert result.remaining >= 59

    def test_blocks_minute_limit(self, limiter):
        min_w = int(time.time()) // 60
        limiter._memory_limits["key-1"] = {
            "min": {min_w: 60},
            "hour": {int(time.time()) // 3600: 1},
            "day": {int(time.time()) // 86400: 1},
        }
        result = limiter.check_rate_limit("key-1", per_minute=60)
        assert result.allowed is False

    def test_blocks_hour_limit(self, limiter):
        hour_w = int(time.time()) // 3600
        limiter._memory_limits["key-1"] = {
            "min": {int(time.time()) // 60: 1},
            "hour": {hour_w: 1000},
            "day": {int(time.time()) // 86400: 1},
        }
        result = limiter.check_rate_limit("key-1", per_hour=1000)
        assert result.allowed is False

    def test_blocks_day_limit(self, limiter):
        day_w = int(time.time()) // 86400
        limiter._memory_limits["key-1"] = {
            "min": {int(time.time()) // 60: 1},
            "hour": {int(time.time()) // 3600: 1},
            "day": {day_w: 10001},
        }
        result = limiter.check_rate_limit("key-1", per_day=10000)
        assert result.allowed is False

    def test_cleanup_removes_stale_windows(self, limiter):
        limiter._memory_limits["key-1"] = {
            "min": {100: 5, 99999999: 1},
            "hour": {100: 5, 99999999: 1},
            "day": {100: 5, 99999999: 1},
        }
        limiter.check_rate_limit("key-1")
        assert 100 not in limiter._memory_limits["key-1"]["min"]
        assert 100 not in limiter._memory_limits["key-1"]["hour"]
        assert 100 not in limiter._memory_limits["key-1"]["day"]

    def test_persists_across_calls(self, limiter):
        limiter.check_rate_limit("key-1")
        limiter.check_rate_limit("key-1")
        assert limiter._memory_limits["key-1"]["min"][int(time.time()) // 60] == 2


class TestCheckRateLimit:
    def test_uses_redis_when_available(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.execute.return_value = [1, True, 1, True, 1, True]
        mock_redis.pipeline.return_value = pipe
        limiter = ApiKeyRateLimiter(redis_client=mock_redis)
        result = limiter.check_rate_limit("key-1")
        assert result.allowed is True

    def test_falls_back_to_memory(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        limiter._get_redis = MagicMock(return_value=None)
        result = limiter.check_rate_limit("key-1")
        assert result.allowed is True


class TestGetUsage:
    def test_redis_path(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.execute.return_value = [5, 50, 200]
        mock_redis.pipeline.return_value = pipe
        limiter = ApiKeyRateLimiter(redis_client=mock_redis)
        result = limiter.get_usage("key-1")
        assert result["requests_this_minute"] == 5
        assert result["requests_this_hour"] == 50
        assert result["requests_today"] == 200

    def test_memory_path(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        limiter._get_redis = MagicMock(return_value=None)
        limiter.check_rate_limit("key-1")
        limiter.check_rate_limit("key-1")
        result = limiter.get_usage("key-1")
        assert result["requests_this_minute"] >= 2

    @pytest.fixture
    def limiter(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        return ApiKeyRateLimiter(redis_client=MagicMock())

    def test_exact_limit_not_exceeded(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [60, True, 50, True, 200, True]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.check_rate_limit("key-1", per_minute=60)
        assert result.allowed is True

    def test_usage_tracking_redis_empty_keys(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [None, None, None]
        limiter._redis.pipeline.return_value = pipe
        result = limiter.get_usage("key-1")
        assert result["requests_this_minute"] == 0
        assert result["requests_this_hour"] == 0
        assert result["requests_today"] == 0


class TestGetRedisFallback:
    def test_lazy_load_failure_sets_none(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        with patch("app.cache.redis_cache.get_redis_cache", side_effect=ImportError("no module")):
            assert limiter._get_redis() is None
        assert limiter._redis is None

    def test_set_redis_client_overrides(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        new_client = MagicMock()
        limiter.set_redis_client(new_client)
        limiter._get_redis()
        assert limiter._redis is new_client


class TestMemoryEdgeCases:
    def test_empty_memory_usage(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        result = limiter._get_memory_usage("nonexistent_key")
        assert result["requests_this_minute"] == 0

    def test_cleanup_empty_key_does_not_raise(self):
        from app.services.api_key_rate_limiter import ApiKeyRateLimiter

        limiter = ApiKeyRateLimiter()
        limiter._cleanup_memory("no_such_key", 100, 100, 100)
        # Should not raise


class TestGetApiKeyRateLimiter:
    def test_returns_singleton(self):
        from app.services.api_key_rate_limiter import get_api_key_rate_limiter

        r1 = get_api_key_rate_limiter()
        r2 = get_api_key_rate_limiter()
        assert r1 is r2
