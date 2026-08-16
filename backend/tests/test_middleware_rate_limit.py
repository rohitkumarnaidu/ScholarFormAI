import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRateLimitInMemory:
    @pytest.fixture
    def middleware(self):
        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_settings.REDIS_ENABLED = False
            mock_settings.UPLOADS_PER_MINUTE = 10
            from app.middleware.rate_limit import RateLimitMiddleware

            app = MagicMock()
            mw = RateLimitMiddleware(app, requests_per_minute=60)
            mw._redis_warning_logged = False
            return mw

    def test_in_memory_count_new(self, middleware):
        count = middleware._in_memory_count("127.0.0.1")
        assert count == 1

    def test_in_memory_count_multiple(self, middleware):
        middleware._in_memory_count("127.0.0.1")
        count = middleware._in_memory_count("127.0.0.1")
        assert count == 2

    def test_in_memory_count_evicts_stale(self, middleware):
        now = time.time()
        old_ts = now - 120
        middleware.request_counts["127.0.0.1"] = [old_ts]
        count = middleware._in_memory_count("127.0.0.1")
        assert count == 1

    def test_in_memory_upload_count(self, middleware):
        count = middleware._in_memory_count("127.0.0.1", is_upload=True)
        assert count == 1

    def test_in_memory_separate_stores(self, middleware):
        middleware._in_memory_count("127.0.0.1", is_upload=False)
        middleware._in_memory_count("127.0.0.1", is_upload=True)
        assert len(middleware.request_counts["127.0.0.1"]) == 1
        assert len(middleware.upload_request_counts["127.0.0.1"]) == 1


class TestRateLimitRedis:
    @pytest.mark.asyncio
    async def test_redis_count_disabled(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            from app.middleware.rate_limit import RateLimitMiddleware

            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            count = await mw._redis_count("key")
        assert count is None

    @pytest.mark.asyncio
    async def test_redis_count_no_client(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit.redis", None):
                from app.middleware.rate_limit import RateLimitMiddleware

                mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
                count = await mw._redis_count("key")
        assert count is None

    @pytest.mark.asyncio
    async def test_redis_count_success(self):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit.redis", mock_redis):
                from app.middleware.rate_limit import RateLimitMiddleware

                mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
                count = await mw._redis_count("ratelimit:general:ip:12345")
        assert count == 1

    @pytest.mark.asyncio
    async def test_redis_count_handles_error(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit.redis", MagicMock()) as mock_redis:
                mock_redis.incr.side_effect = Exception("redis error")
                from app.middleware.rate_limit import RateLimitMiddleware

                mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
                mw._redis_warning_logged = False
                count = await mw._redis_count("key")
        assert count is None

    @pytest.mark.asyncio
    async def test_redis_count_async_incr(self):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = AsyncMock(return_value=1)()
        mock_redis.expire.return_value = True
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit.redis", mock_redis):
                from app.middleware.rate_limit import RateLimitMiddleware

                mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
                count = await mw._redis_count("key")
        assert count == 1


class TestRateLimitDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_health_path_passes(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "GET"
        mock_call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_dispatch_under_limit(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents"
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_dispatch_over_limit(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=1)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents"
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_call_next = AsyncMock(return_value="response")

        await mw.dispatch(mock_request, mock_call_next)
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_dispatch_upload_with_auth(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents/upload"
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "POST"
        mock_request.headers = {"authorization": "Bearer test-token-123"}
        mock_call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_dispatch_upload_over_limit(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
        mw.uploads_per_minute = 1
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents/upload"
        mock_request.client.host = "127.0.0.1"
        mock_request.method = "POST"
        mock_request.headers = {}
        mock_call_next = AsyncMock(return_value="response")

        await mw.dispatch(mock_request, mock_call_next)
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result.status_code == 429

    @pytest.mark.asyncio
    async def test_dispatch_unknown_client(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents"
        mock_request.client = None
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(mock_request, mock_call_next)
        assert result == "response"
