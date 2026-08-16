from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInMemoryCount:
    def test_limits_basic(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        rl = RateLimitMiddleware(mock_app, requests_per_minute=60)
        count = rl._in_memory_count("1.2.3.4")
        assert count == 1
        count2 = rl._in_memory_count("1.2.3.4")
        assert count2 == 2

    def test_separate_ip_counts(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        rl = RateLimitMiddleware(mock_app)
        c1 = rl._in_memory_count("ip1")
        c2 = rl._in_memory_count("ip2")
        assert c1 == 1
        assert c2 == 1

    def test_upload_separate_from_general(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        rl = RateLimitMiddleware(mock_app)
        general = rl._in_memory_count("ip1")
        upload = rl._in_memory_count("ip1", is_upload=True)
        assert general == 1
        assert upload == 1


class TestDispatch:
    @pytest.mark.asyncio
    async def test_health_never_limited(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        rl = RateLimitMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.url.path = "/health"
        mock_request.method = "GET"
        response = await rl.dispatch(mock_request, mock_app)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_normal_request_passes(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        rl = RateLimitMiddleware(mock_app, requests_per_minute=60)
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.url.path = "/api/v1/documents"
        mock_request.method = "GET"
        response = await rl.dispatch(mock_request, mock_app)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limited(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        rl = RateLimitMiddleware(mock_app, requests_per_minute=1)
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.url.path = "/api/v1/documents"
        mock_request.method = "GET"
        resp1 = await rl.dispatch(mock_request, mock_app)
        assert resp1.status_code == 200
        resp2 = await rl.dispatch(mock_request, mock_app)
        assert resp2.status_code == 429

    @pytest.mark.asyncio
    async def test_upload_limit_stricter(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        rl = RateLimitMiddleware(mock_app)
        rl.uploads_per_minute = 2
        mock_request = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.url.path = "/api/v1/documents/upload"
        mock_request.method = "POST"
        mock_request.headers.get.return_value = ""
        for _ in range(2):
            resp = await rl.dispatch(mock_request, mock_app)
            assert resp.status_code == 200
        resp = await rl.dispatch(mock_request, mock_app)
        assert resp.status_code == 429


class TestRedisCount:
    @pytest.mark.asyncio
    async def test_redis_fallback_returns_none_when_disabled(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            from app.middleware.rate_limit import RateLimitMiddleware

            mock_app = AsyncMock()
            rl = RateLimitMiddleware(mock_app)
            count = await rl._redis_count("key")
            assert count is None

    @pytest.mark.asyncio
    async def test_redis_count_returns_int(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit._ensure_redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.incr.return_value = 5
                mock_client.expire.return_value = True
                mock_redis.return_value = mock_client
                from app.middleware.rate_limit import RateLimitMiddleware

                mock_app = AsyncMock()
                rl = RateLimitMiddleware(mock_app)
                count = await rl._redis_count("key")
                assert count == 5

    @pytest.mark.asyncio
    async def test_redis_error_returns_none(self):
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True):
            with patch("app.middleware.rate_limit._ensure_redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.incr.side_effect = ConnectionError("fail")
                mock_redis.return_value = mock_client
                from app.middleware.rate_limit import RateLimitMiddleware

                mock_app = AsyncMock()
                rl = RateLimitMiddleware(mock_app)
                count = await rl._redis_count("key")
                assert count is None
