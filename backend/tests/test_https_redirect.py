from unittest.mock import AsyncMock, MagicMock

import pytest


class TestHTTPSRedirectMiddleware:
    @pytest.mark.asyncio
    async def test_passes_https_requests(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        mw = HTTPSRedirectMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "https"
        mock_request.url.path = "/api/v1/anything"
        response = await mw.dispatch(mock_request, mock_app)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redirects_http(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        mock_app = AsyncMock()
        mw = HTTPSRedirectMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "http"
        mock_request.url.hostname = "example.com"
        mock_request.url.path = "/api/v1/data"
        mock_request.url.replace.return_value = mock_request.url
        response = await mw.dispatch(mock_request, mock_app)
        assert response.status_code == 307

    @pytest.mark.asyncio
    async def test_skips_localhost(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        mw = HTTPSRedirectMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "http"
        mock_request.url.hostname = "localhost"
        mock_request.url.path = "/api/v1/data"
        response = await mw.dispatch(mock_request, mock_app)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_health_endpoints(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        mock_app = AsyncMock()
        mock_app.return_value = MagicMock(status_code=200)
        mw = HTTPSRedirectMiddleware(mock_app)
        for path in ["/api/v1/health", "/health", "/ready"]:
            mock_request = MagicMock()
            mock_request.url.scheme = "http"
            mock_request.url.hostname = "example.com"
            mock_request.url.path = path
            response = await mw.dispatch(mock_request, mock_app)
            assert response.status_code == 200, f"failed for {path}"


class TestHSTSMiddleware:
    @pytest.mark.asyncio
    async def test_adds_hsts_on_https(self):
        from app.middleware.https_redirect import HSTSMiddleware
        mock_app = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_app.return_value = mock_response
        mw = HSTSMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "https"
        response = await mw.dispatch(mock_request, mock_app)
        assert "Strict-Transport-Security" in response.headers
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]
        assert "preload" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_skips_hsts_on_http(self):
        from app.middleware.https_redirect import HSTSMiddleware
        mock_app = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_app.return_value = mock_response
        mw = HSTSMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "http"
        response = await mw.dispatch(mock_request, mock_app)
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_adds_security_headers(self):
        from app.middleware.https_redirect import HSTSMiddleware
        mock_app = AsyncMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_app.return_value = mock_response
        mw = HSTSMiddleware(mock_app)
        mock_request = MagicMock()
        mock_request.url.scheme = "https"
        response = await mw.dispatch(mock_request, mock_app)
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
