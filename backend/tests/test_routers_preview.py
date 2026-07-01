import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


class TestPreviewHelpers:
    def test_valid_session_id(self):
        from app.routers.preview import _valid_session_id
        assert _valid_session_id("abc-123_def")
        assert not _valid_session_id("")
        assert not _valid_session_id("ab")
        assert not _valid_session_id("x" * 65)

    def test_hash_html(self):
        from app.routers.preview import _hash_html
        h1 = _hash_html("hello")
        h2 = _hash_html("hello")
        h3 = _hash_html("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 12

    def test_chunk_text_empty(self):
        from app.routers.preview import _chunk_text
        assert list(_chunk_text("")) == []

    def test_chunk_text(self):
        from app.routers.preview import _chunk_text
        chunks = list(_chunk_text("a" * 1000, chunk_size=320))
        assert len(chunks) == 4
        assert all(len(c) <= 320 for c in chunks)

    def test_build_ai_messages(self):
        from app.routers.preview import _build_ai_messages
        messages = _build_ai_messages("some content", "IEEE")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "some content" in messages[1]["content"]


class TestHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat(self):
        from app.routers.preview import _heartbeat
        ws_mock = AsyncMock()
        ws_mock.send_json.side_effect = [None, Exception("stop")]
        with pytest.raises(Exception):
            await _heartbeat(ws_mock)


class TestPreviewLive:
    @pytest.mark.asyncio
    async def test_preview_live(self):
        from app.routers.preview import preview_live
        mock_result = {"html": "<p>hi</p>", "latency_ms": 5, "warnings": []}
        with patch("app.routers.preview.preview_renderer") as mock_pr:
            mock_pr.render_preview.return_value = mock_result
            payload = MagicMock()
            payload.content = "hello"
            payload.templateId = "IEEE"
            result = await preview_live(payload)
        assert result["html"] == "<p>hi</p>"

    @pytest.mark.asyncio
    async def test_default_template(self):
        from app.routers.preview import preview_live
        with patch("app.routers.preview.preview_renderer") as mock_pr:
            mock_pr.render_preview.return_value = {"html": "", "latency_ms": 0, "warnings": []}
            payload = MagicMock()
            payload.content = "hi"
            payload.templateId = "APA"
            result = await preview_live(payload)
        assert "latencyMs" in result


class TestAISuggest:
    @pytest.mark.asyncio
    async def test_invalid_session(self):
        from app.routers.preview import ai_suggest
        mock_request = MagicMock()
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await ai_suggest(mock_request, sessionId="ab", content="test")

    @pytest.mark.asyncio
    async def test_valid(self):
        from app.routers.preview import ai_suggest

        async def _run_directly(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        async def _run_directly(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with (
            patch("app.routers.preview.generate_with_fallback", return_value={"text": " suggestion text ", "model": "gpt-4", "tier": "nvidia"}),
            patch("app.routers.preview.asyncio.to_thread", _run_directly),
        ):
            response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")
            events = []
            async for raw in response.body_iterator:
                events.append(raw)
                if raw.get("event") == "done":
                    break
        assert len(events) >= 2
        assert any(e.get("event") == "status" for e in events)
        assert any(e.get("event") == "done" for e in events)

    @pytest.mark.asyncio
    async def test_llm_unavailable(self):
        from app.routers.preview import ai_suggest, LLMUnavailableError

        async def _run_directly(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with (
            patch("app.routers.preview.generate_with_fallback", side_effect=LLMUnavailableError("LLM down")),
            patch("app.routers.preview.asyncio.to_thread", _run_directly),
        ):
            response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")
            events = []
            async for raw in response.body_iterator:
                events.append(raw)
                if raw.get("event") == "error":
                    break
        assert any(e.get("event") == "error" for e in events)

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        from app.routers.preview import ai_suggest

        async def _run_directly(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with (
            patch("app.routers.preview.generate_with_fallback", side_effect=Exception("generic")),
            patch("app.routers.preview.asyncio.to_thread", _run_directly),
        ):
            response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")
            events = []
            async for raw in response.body_iterator:
                events.append(raw)
                if raw.get("event") == "error":
                    break
        assert any(e.get("event") == "error" for e in events)
