from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestShouldLogIdempotency:
    def test_upload_path(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/upload") is True

    def test_generator_session(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/generator/sessions") is True

    def test_other_path(self):
        from app.middleware.request_id import _should_log_idempotency
        assert _should_log_idempotency("/api/v1/documents") is False


class TestGetRequestId:
    def test_existing_state_id(self):
        from app.middleware.request_id import get_request_id
        request = MagicMock()
        request.state.request_id = "existing-id"
        result = get_request_id(request)
        assert result == "existing-id"

    def test_generates_new_id(self):
        from app.middleware.request_id import get_request_id
        request = MagicMock()
        request.state.request_id = None
        result = get_request_id(request)
        assert request.state.request_id == result
        assert result is not None


class TestRequestIdMiddleware:
    @pytest.mark.asyncio
    async def test_non_http_scope_passes(self):
        from app.middleware.request_id import RequestIdMiddleware
        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {"type": "websocket"}
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_http_sets_request_id(self):
        from app.middleware.request_id import RequestIdMiddleware
        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        }
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        assert "request_id" in scope.get("state", {})

    @pytest.mark.asyncio
    async def test_idempotency_key_logged_for_post(self):
        from app.middleware.request_id import RequestIdMiddleware
        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        headers = [(b"x-request-id", b"req-123"), (b"idempotency-key", b"idem-456")]
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/documents/upload",
            "headers": headers,
        }
        receive = MagicMock()
        send = MagicMock()
        with patch("app.middleware.request_id.logger") as mock_logger:
            await mw(scope, receive, send)
            mock_logger.info.assert_called_once()
            assert "idem-456" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_response_gets_x_request_id(self):
        from app.middleware.request_id import RequestIdMiddleware
        sent_messages = []

        async def send_wrapper(msg):
            sent_messages.append(msg)

        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        }
        receive = MagicMock()
        await mw(scope, receive, send_wrapper)
        start_msg = {"type": "http.response.start", "headers": [(b"content-type", b"text/plain")]}
        await app.call_args[0][2](start_msg)
        assert b"x-request-id" in dict(sent_messages[0]["headers"])

    @pytest.mark.asyncio
    async def test_context_reset_after_request(self):
        from app.middleware.request_id import RequestIdMiddleware
        from app.utils.logging_context import get_request_id_context
        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"x-request-id", b"req-999")],
        }
        receive = MagicMock()
        send = MagicMock()
        await mw(scope, receive, send)
        assert get_request_id_context() is None
