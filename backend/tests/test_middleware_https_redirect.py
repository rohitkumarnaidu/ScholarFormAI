import pytest
from unittest.mock import MagicMock, AsyncMock


class TestHTTPSRedirectMiddleware:
    @pytest.fixture
    def middleware(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        return HTTPSRedirectMiddleware(MagicMock())

    @pytest.mark.asyncio
    async def test_https_passes_through(self, middleware):
        request = MagicMock()
        request.url.scheme = "https"
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_localhost_passes_through(self, middleware):
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_127_0_0_1_passes_through(self, middleware):
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "127.0.0.1"
        request.url.path = "/api/v1/something"
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_health_path_passes_through(self, middleware):
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "example.com"
        request.url.path = "/health"
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_http_redirects_to_https(self, middleware):
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "example.com"
        request.url.path = "/api/v1/endpoint"
        request.url.replace.return_value = request.url
        call_next = AsyncMock()
        from starlette.responses import RedirectResponse
        result = await middleware.dispatch(request, call_next)
        assert isinstance(result, RedirectResponse)

    @pytest.mark.parametrize("path", ["/api/v1/health", "/api/v1/health/live", "/ready", "/readyz"])
    @pytest.mark.asyncio
    async def test_health_paths_bypassed(self, middleware, path):
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "example.com"
        request.url.path = path
        call_next = AsyncMock(return_value="response")
        result = await middleware.dispatch(request, call_next)
        assert result == "response"


class TestHSTSMiddleware:
    @pytest.fixture
    def middleware(self):
        from app.middleware.https_redirect import HSTSMiddleware
        return HSTSMiddleware(MagicMock())

    @pytest.mark.asyncio
    async def test_hsts_added_to_https(self, middleware):
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await middleware.dispatch(request, call_next)
        assert "Strict-Transport-Security" in result.headers
        assert "includeSubDomains" in result.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_hsts_not_added_to_http(self, middleware):
        request = MagicMock()
        request.url.scheme = "http"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await middleware.dispatch(request, call_next)
        assert "Strict-Transport-Security" not in result.headers

    @pytest.mark.asyncio
    async def test_security_headers_added(self, middleware):
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await middleware.dispatch(request, call_next)
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_custom_hsts_params(self):
        from app.middleware.https_redirect import HSTSMiddleware
        mw = HSTSMiddleware(MagicMock(), max_age=12345, include_subdomains=False, preload=False)
        assert mw.max_age == 12345
        assert mw.include_subdomains is False
        assert mw.preload is False
