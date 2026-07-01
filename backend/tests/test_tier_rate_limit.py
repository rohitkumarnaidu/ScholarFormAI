# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.responses import JSONResponse

from app.middleware.tier_rate_limit import TierRateLimitMiddleware


@pytest.mark.asyncio
async def test_guest_daily_limit_blocks():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents/upload"
    request.headers = {}
    request.client.host = "1.2.3.4"

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    first = await middleware.dispatch(request, call_next)
    second = await middleware.dispatch(request, call_next)

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_tier_limit_skips_health():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/health"
    request.headers = {}
    request.client.host = "1.2.3.4"

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


class TestShouldSkip:
    def test_health_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/health"
        assert middleware._should_skip(request) is True

    def test_ready_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/ready"
        assert middleware._should_skip(request) is True

    def test_status_in_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/api/v1/documents/status"
        assert middleware._should_skip(request) is True

    def test_templates_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/api/v1/templates/abc"
        assert middleware._should_skip(request) is True

    def test_api_health_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/api/v1/health"
        assert middleware._should_skip(request) is True

    def test_regular_path_not_skipped(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/api/v1/documents/upload"
        assert middleware._should_skip(request) is False


class TestIsLimitedEndpoint:
    def test_post_upload(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents/upload"
        assert middleware._is_limited_endpoint(request) is True

    def test_post_generator(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/generator/sessions"
        assert middleware._is_limited_endpoint(request) is True

    def test_get_method_not_limited(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/documents/upload"
        assert middleware._is_limited_endpoint(request) is False

    def test_non_limited_path(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents"
        assert middleware._is_limited_endpoint(request) is False


class TestGetUserId:
    def test_no_auth_header(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {}
        assert middleware._get_user_id(request) is None

    def test_basic_auth_not_bearer(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {"authorization": "Basic dXNlcjpwYXNz"}
        assert middleware._get_user_id(request) is None

    def test_empty_token(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {"authorization": "Bearer "}
        assert middleware._get_user_id(request) is None

    def test_invalid_token(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {"authorization": "Bearer invalidtoken"}
        with patch("app.middleware.tier_rate_limit.verify_jwt") as mock_verify:
            mock_verify.side_effect = Exception("bad")
            result = middleware._get_user_id(request)
        assert result is None


class TestUtcDayKey:
    def test_returns_string(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        key = middleware._utc_day_key()
        assert isinstance(key, str)
        assert len(key) == 8


class TestSecondsUntilNextDay:
    def test_returns_positive_int(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        seconds = middleware._seconds_until_next_day()
        assert seconds > 0


class TestIncrementGuestCount:
    def test_in_memory_initial(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        middleware._redis = None
        count = middleware._increment_guest_count("1.2.3.4")
        assert count == 1

    def test_in_memory_multiple(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        middleware._redis = None
        middleware._increment_guest_count("1.2.3.4")
        count = middleware._increment_guest_count("1.2.3.4")
        assert count == 2

    def test_in_memory_separate_ips(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        middleware._redis = None
        middleware._increment_guest_count("1.2.3.4")
        count = middleware._increment_guest_count("5.6.7.8")
        assert count == 1

    def test_redis_increment(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 3
        middleware._redis = mock_redis
        count = middleware._increment_guest_count("1.2.3.4")
        assert count == 3

    def test_redis_first_call_sets_expiry(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        middleware._redis = mock_redis
        count = middleware._increment_guest_count("1.2.3.4")
        assert count == 1
        mock_redis.expire.assert_called_once()

    def test_redis_failure_falls_to_memory(self):
        middleware = TierRateLimitMiddleware(MagicMock())
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = RuntimeError("redis down")
        middleware._redis = mock_redis
        middleware._redis_warning_logged = False
        count = middleware._increment_guest_count("1.2.3.4")
        assert count == 1
        assert middleware._redis_warning_logged is True


@pytest.mark.asyncio
async def test_authenticated_user_passes():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents/upload"
    request.headers = {"authorization": "Bearer valid-token"}
    request.client.host = "1.2.3.4"

    with patch("app.middleware.tier_rate_limit.verify_jwt", return_value={"sub": "user-abc"}):
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_method_on_limited_path_passes():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "GET"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents/upload"
    request.headers = {}

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_non_limited_path_passes():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents"
    request.headers = {}

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dispatch_no_client_uses_unknown():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=0)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents/upload"
    request.headers = {}
    request.client = None

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
