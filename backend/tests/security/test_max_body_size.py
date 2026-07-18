# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enterprise tests for MaxBodySizeMiddleware — Content-Length header validation
and streaming body-size tracking.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytestmark = [pytest.mark.security]


async def _consume_receive(scope, recv, send):
    """Simple ASGI app that reads messages until disconnect or None."""
    while True:
        msg = await recv()
        if msg is None:
            break
        if isinstance(msg, dict) and msg.get("type") == "http.disconnect":
            break


def _has_413(send: AsyncMock) -> bool:
    return any(
        c[0][0].get("type") == "http.response.start" and c[0][0].get("status") == 413
        for c in send.call_args_list
    )


class TestMaxBodySizeMiddleware:
    """MaxBodySizeMiddleware: Content-Length and streaming body size checks."""

    @pytest.mark.asyncio
    async def test_content_length_under_limit_passes(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=1024 * 1024)

        scope = {"type": "http", "headers": [(b"content-length", b"100")]}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_content_length_over_limit_returns_413(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "http", "headers": [(b"content-length", b"500")]}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_not_called()
        assert _has_413(send)

    @pytest.mark.asyncio
    async def test_no_content_length_small_body_passes(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=1024 * 1024)

        scope = {"type": "http", "headers": []}
        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": b"small"},
            {"type": "http.disconnect"},
        ])
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_body_exceeds_limit_mid_stream(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock(side_effect=_consume_receive)
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "http", "headers": []}
        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": b"x" * 101},
            {"type": "http.disconnect"},
        ])
        send = AsyncMock()

        await mw(scope, receive, send)
        assert _has_413(send)

    @pytest.mark.asyncio
    async def test_invalid_content_length_passes_through(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "http", "headers": [(b"content-length", b"not-a-number")]}
        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": b"small"},
            {"type": "http.disconnect"},
        ])
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_error_response_detail_message(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=50)

        scope = {"type": "http", "headers": [(b"content-length", b"500")]}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        body_calls = [
            c[0][0] for c in send.call_args_list
            if c[0][0].get("type") == "http.response.body"
        ]
        assert len(body_calls) >= 1
        body = body_calls[0].get("body", b"")
        assert b"too large" in body
        assert b"Request body too large" in body

    @pytest.mark.asyncio
    async def test_custom_max_size_enforced(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=10)

        scope = {"type": "http", "headers": [(b"content-length", b"15")]}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_not_called()
        assert _has_413(send)

    @pytest.mark.asyncio
    async def test_body_exactly_at_limit_passes(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock()
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "http", "headers": [(b"content-length", b"100")]}
        receive = AsyncMock()
        send = AsyncMock()

        await mw(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_chunks_accumulate_and_trigger_413(self):
        from app.middleware.security_headers import MaxBodySizeMiddleware

        app = AsyncMock(side_effect=_consume_receive)
        mw = MaxBodySizeMiddleware(app, max_size=100)

        scope = {"type": "http", "headers": []}
        receive = AsyncMock(side_effect=[
            {"type": "http.request", "body": b"x" * 40},
            {"type": "http.request", "body": b"x" * 30},
            {"type": "http.request", "body": b"x" * 40},
            {"type": "http.disconnect"},
        ])
        send = AsyncMock()

        await mw(scope, receive, send)
        assert _has_413(send)
