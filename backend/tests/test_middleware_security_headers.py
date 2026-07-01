import pytest
from unittest.mock import MagicMock, AsyncMock


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_default_headers(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await mw.dispatch(request, call_next)
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Referrer-Policy" in result.headers
        assert "Permissions-Policy" in result.headers
        assert "Content-Security-Policy" in result.headers

    @pytest.mark.asyncio
    async def test_docs_route_allows_cdn(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/docs"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await mw.dispatch(request, call_next)
        csp = result.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp

    @pytest.mark.asyncio
    async def test_redoc_route_allows_cdn(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/redoc"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await mw.dispatch(request, call_next)
        csp = result.headers["Content-Security-Policy"]
        assert "unpkg.com" in csp

    @pytest.mark.asyncio
    async def test_openapi_json_allows_cdn(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        mw = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock()
        request.url.path = "/openapi.json"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        result = await mw.dispatch(request, call_next)
        csp = result.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp


class TestMaxBodySizeMiddleware:
    @pytest.mark.asyncio
    async def test_non_http_scope_passes(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app)
        scope = {"type": "websocket"}
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_content_length_under_limit(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=1000)
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"500")],
        }
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_content_length_over_limit(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        sent = []
        async def send_fn(msg):
            sent.append(msg)
        mw = MaxBodySizeMiddleware(AsyncMock(), max_size=100)
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"500")],
        }
        receive = MagicMock()
        await mw(scope, receive, send_fn)
        assert len(sent) >= 1
        assert sent[0].get("type") == "http.response.start"
        assert sent[0].get("status") == 413

    @pytest.mark.asyncio
    async def test_no_content_length_header(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app)
        scope = {
            "type": "http",
            "headers": [],
        }
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_content_length(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"not-a-number")],
        }
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        assert app.call_count >= 1
