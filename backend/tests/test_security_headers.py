from unittest.mock import AsyncMock, MagicMock

import pytest


class TestSecurityHeadersMiddleware:
    @pytest.fixture
    def middleware(self):
        from app.middleware.security_headers import SecurityHeadersMiddleware
        return SecurityHeadersMiddleware

    async def test_sets_standard_security_headers(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = "/api/v1/health"
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    async def test_docs_route_relaxes_csp(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = "/docs"
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp
        assert "unpkg.com" in csp

    async def test_redoc_route_relaxes_csp(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = "/redoc"
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp

    async def test_openapi_json_relaxes_csp(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = "/openapi.json"
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp

    async def test_non_docs_route_restrictive_csp(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = "/api/v1/process"
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" not in csp
        assert "unpkg.com" not in csp

    async def test_empty_path_falls_to_non_docs(self, middleware):
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.url.path = ""
        mw = middleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        assert "cdn.jsdelivr.net" not in response.headers["Content-Security-Policy"]


class TestMaxBodySizeMiddleware:
    @pytest.fixture
    def mw_class(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware
        return MaxBodySizeMiddleware

    async def test_under_limit_passes_through(self, mw_class):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"100")],
        }
        mw = mw_class(app, max_size=1024)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)

    async def test_over_limit_returns_413(self, mw_class):
        app = MagicMock()
        receive = AsyncMock()
        send = AsyncMock()
        scope = {
            "type": "http",
            "headers": [(b"content-length", b"99999")],
        }
        mw = mw_class(app, max_size=1024)
        await mw(scope, receive, send)
        app.assert_not_called()
        assert send.awaited
        start_call = None
        for call in send.call_args_list:
            args = call[0][0]
            if args.get("type") == "http.response.start":
                start_call = args
                break
        assert start_call is not None, "No http.response.start call found"
        assert start_call["status"] == 413

    async def test_non_http_scope_passes_through(self, mw_class):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "websocket"}
        mw = mw_class(app)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)

    async def test_no_content_length_header_passes_through(self, mw_class):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "http", "headers": []}
        mw = mw_class(app)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)

    async def test_invalid_content_length_passes_through(self, mw_class):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "http", "headers": [(b"content-length", b"not-a-number")]}
        mw = mw_class(app)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)
