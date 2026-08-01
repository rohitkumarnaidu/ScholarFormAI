from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_context():
    with patch("app.middleware.request_id.bind_context") as mock_bind, \
         patch("app.middleware.request_id.reset_context") as mock_reset:
        mock_bind.return_value = ("token",)
        yield mock_bind, mock_reset


class TestRequestIdMiddleware:
    @pytest.fixture
    def middleware_class(self):
        from app.middleware.request_id import RequestIdMiddleware
        return RequestIdMiddleware

    async def test_non_http_passes_through(self, middleware_class, _reset_context):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "websocket"}
        mw = middleware_class(app)
        await mw(scope, receive, send)
        app.assert_awaited_once_with(scope, receive, send)

    async def test_sets_request_id_in_state(self, middleware_class, _reset_context):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
        mw = middleware_class(app)
        await mw(scope, receive, send)
        assert "request_id" in scope["state"]

    async def test_uses_x_request_id_header(self, middleware_class, _reset_context):
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [(b"x-request-id", b"my-custom-id")],
        }
        mw = middleware_class(app)
        await mw(scope, receive, send)
        assert scope["state"]["request_id"] == "my-custom-id"

    async def test_sets_response_header(self, middleware_class, _reset_context):
        app = AsyncMock()
        receive = AsyncMock()
        send = AsyncMock()
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [(b"host", b"localhost")],
        }

        async def fake_send_wrapper(scope, receive, send_wrapped):
            await send_wrapped({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
            await send_wrapped({"type": "http.response.body", "body": b""})

        app.side_effect = fake_send_wrapper
        mw = middleware_class(app)
        await mw(scope, receive, send)
        found_ex_request_id = False
        for call in send.call_args_list if hasattr(send, 'call_args_list') else []:
            msg = call[0][0]
            if msg["type"] == "http.response.start":
                hdrs = dict(msg.get("headers", []))
                if b"x-request-id" in hdrs:
                    found_ex_request_id = True
                    break
        assert found_ex_request_id, "x-request-id not found in response headers"

    async def test_logs_idempotency_key_on_post(self, middleware_class):
        with patch("app.middleware.request_id.logger") as mock_logger:
            app = AsyncMock()
            receive = AsyncMock()
            send = MagicMock()
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/upload",
                "headers": [(b"idempotency-key", b"key-123")],
            }
            mw = middleware_class(app)
            await mw(scope, receive, send)
            mock_logger.info.assert_called_once()
            assert "key-123" in str(mock_logger.info.call_args)

    async def test_does_not_log_idempotency_on_non_post(self, middleware_class):
        with patch("app.middleware.request_id.logger") as mock_logger:
            app = AsyncMock()
            receive = AsyncMock()
            send = MagicMock()
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/upload",
                "headers": [(b"idempotency-key", b"key-123")],
            }
            mw = middleware_class(app)
            await mw(scope, receive, send)
            mock_logger.info.assert_not_called()

    async def test_does_not_log_idempotency_on_non_matching_path(self, middleware_class):
        with patch("app.middleware.request_id.logger") as mock_logger:
            app = AsyncMock()
            receive = AsyncMock()
            send = MagicMock()
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/process",
                "headers": [(b"idempotency-key", b"key-123")],
            }
            mw = middleware_class(app)
            await mw(scope, receive, send)
            mock_logger.info.assert_not_called()

    async def test_resets_context_in_finally(self, middleware_class, _reset_context):
        _, reset_context = _reset_context
        app = AsyncMock()
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
        mw = middleware_class(app)
        await mw(scope, receive, send)
        reset_context.assert_called_once_with(("token",))

    async def test_resets_context_on_exception(self, middleware_class, _reset_context):
        _, reset_context = _reset_context
        app = AsyncMock(side_effect=ValueError("boom"))
        receive = AsyncMock()
        send = MagicMock()
        scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
        mw = middleware_class(app)
        with pytest.raises(ValueError):
            await mw(scope, receive, send)
        reset_context.assert_called_once_with(("token",))


class TestGetRequestId:
    def test_returns_from_state(self):
        from app.middleware.request_id import get_request_id
        request = MagicMock()
        request.state.request_id = "existing-id"
        assert get_request_id(request) == "existing-id"

    def test_creates_new_uuid_when_missing(self):
        from app.middleware.request_id import get_request_id
        request = MagicMock()
        del request.state.request_id
        result = get_request_id(request)
        assert len(result) == 36
        assert request.state.request_id == result


class TestShouldLogIdempotency:
    def test_matching_suffix_returns_true(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/upload")
        assert _should_log_idempotency("/generator/sessions")
        assert _should_log_idempotency("/synthesis/sessions")

    def test_non_matching_returns_false(self):
        from app.middleware.request_id import _should_log_idempotency
        assert not _should_log_idempotency("/api/v1/health")
        assert not _should_log_idempotency("/process")
        assert not _should_log_idempotency("/")
