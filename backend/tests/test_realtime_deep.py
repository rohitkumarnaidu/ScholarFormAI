from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════
# Realtime Events — fill remaining branches
# ═══════════════════════════════════════════════════════════════════

class TestMakeEventEdgeCases:
    def test_no_kwargs_returns_minimal(self):
        from app.realtime.events import make_event
        result = make_event("test")
        assert result["event_type"] == "test"
        assert result["payload"] == {}

    def test_kwargs_merged_into_event(self):
        from app.realtime.events import make_event
        result = make_event("progress", job_id="j1", stage="parse", progress=50)
        assert result["job_id"] == "j1"
        assert result["stage"] == "parse"
        assert result["progress"] == 50


# ═══════════════════════════════════════════════════════════════════
# RedisPubSub — additional coverage
# ═══════════════════════════════════════════════════════════════════

class TestRedisPubSubAdditional:
    @pytest.fixture
    def pubsub(self):
        with patch("app.realtime.pubsub.settings") as mock_s:
            mock_s.REDIS_URL = "redis://localhost:6379"
            mock_s.REDIS_ENABLED = False
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub()
            ps._redis_warning_logged = False
            ps._force_fallback = False
            ps._fallback_channels = {}
            return ps

    async def test_subscribe_with_redis(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        async def fake_listen():
            yield {"type": "message", "data": json.dumps({"key": "val"})}

        mock_pubsub.listen = fake_listen
        mock_redis.pubsub.return_value = mock_pubsub

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "val"
            mock_pubsub.subscribe.assert_called_once_with("ch")

    def _make_redis_mock(self):
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        return mock_redis, mock_pubsub

    async def test_subscribe_redis_non_message_type(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "subscribe", "data": "ok"}
            yield {"type": "message", "data": json.dumps({"key": "val"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "val"

    async def test_subscribe_redis_none_data_skipped(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": None}
            yield {"type": "message", "data": json.dumps({"key": "val"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "val"

    async def test_subscribe_redis_bytes_data(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": b'{"key": "bytes"}'}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "bytes"

    async def test_subscribe_redis_bytearray_data(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": bytearray(b'{"key": "ba"}')}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "ba"

    async def test_subscribe_redis_dict_data(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": {"key": "dict_val"}}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "dict_val"

    async def test_subscribe_redis_json_decode_error_skipped(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": "{invalid json}"}
            yield {"type": "message", "data": json.dumps({"key": "ok"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "ok"

    async def test_subscribe_redis_unknown_data_type_skipped(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()

        async def fake_listen():
            yield {"type": "message", "data": 42}
            yield {"type": "message", "data": json.dumps({"key": "ok"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            event = await gen.__anext__()
            assert event["key"] == "ok"

    async def test_subscribe_redis_cleanup_aclose(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()
        mock_pubsub.aclose = AsyncMock()

        async def fake_listen():
            yield {"type": "message", "data": json.dumps({"key": "val"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            await gen.__anext__()
            await gen.aclose()
            mock_pubsub.unsubscribe.assert_called_once_with("ch")
            mock_pubsub.aclose.assert_called_once()

    async def test_subscribe_redis_cleanup_close_fallback(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis, mock_pubsub = self._make_redis_mock()
        mock_pubsub.aclose = None
        mock_pubsub.close = AsyncMock()

        async def fake_listen():
            yield {"type": "message", "data": json.dumps({"key": "val"})}

        mock_pubsub.listen = fake_listen

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            gen = pubsub.subscribe("ch")
            await gen.__anext__()
            await gen.aclose()
            mock_pubsub.unsubscribe.assert_called_once_with("ch")
            mock_pubsub.close.assert_called_once()

    async def test_publish_to_fallback_without_queues(self, pubsub):
        await pubsub.publish("unsubscribed_ch", {"key": "val"})

    async def test_get_redis_lock_contention(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
            mock_aioredis.from_url.return_value = mock_redis

            async def first_call():
                return await pubsub._get_redis()

            async def second_call():
                return await pubsub._get_redis()

            c1 = await first_call()
            c2 = await second_call()
            assert c1 is not None
            assert c2 is not None


class TestRedisPubSubDisconnected:
    @pytest.fixture
    def pubsub(self):
        with patch("app.realtime.pubsub.settings") as mock_s:
            mock_s.REDIS_URL = "redis://localhost:6379"
            mock_s.REDIS_ENABLED = True
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub()
            ps._redis_warning_logged = False
            ps._force_fallback = False
            ps._fallback_channels = {}
            return ps

    async def test_get_redis_connection_failure_sets_force_fallback(self, pubsub):
        with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
            mock_aioredis.from_url.side_effect = ConnectionError("no redis")
            client = await pubsub._get_redis()
            assert client is None
            assert pubsub._force_fallback is True

    async def test_subscribe_fallback_no_client(self, pubsub):
        pubsub._force_fallback = True
        gen = pubsub.subscribe("ch")
        pubsub._fallback_channels["ch"] = set()
        task = asyncio.create_task(gen.__anext__())
        await asyncio.sleep(0.05)
        await pubsub.publish("ch", {"key": "val"})
        result = await asyncio.wait_for(task, timeout=0.5)
        assert result["key"] == "val"

    async def test_subscribe_fallback_cleanup_discard(self, pubsub):
        pubsub._force_fallback = True
        gen = pubsub.subscribe("ch")
        task = asyncio.create_task(gen.__anext__())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass
        await asyncio.sleep(0.05)
        assert len(pubsub._fallback_channels.get("ch", set())) == 0
