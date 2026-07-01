import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

pytestmark = pytest.mark.asyncio


class aiter:
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


class TestRedisPubSub:
    @pytest.fixture
    def pubsub(self):
        with patch("app.realtime.pubsub.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_settings.REDIS_ENABLED = False
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub()
            ps._redis_warning_logged = False
            ps._force_fallback = False
            ps._fallback_channels = {}
            return ps

    async def test_get_redis_disabled(self, pubsub):
        client = await pubsub._get_redis()
        assert client is None

    async def test_get_redis_enabled_but_no_module(self, pubsub):
        pubsub._redis_enabled = True
        with patch("app.realtime.pubsub.aioredis", None):
            client = await pubsub._get_redis()
        assert client is None

    async def test_publish_empty_channel(self, pubsub):
        await pubsub.publish("", {"key": "val"})

    async def test_publish_fallback(self, pubsub):
        q = asyncio.Queue()
        pubsub._fallback_channels["test"] = {q}
        await pubsub.publish("test", {"key": "val"})
        result = await asyncio.wait_for(q.get(), timeout=0.5)
        assert result["key"] == "val"

    async def test_subscribe_fallback(self, pubsub):
        async def reader():
            gen = pubsub.subscribe("test")
            event = await gen.__anext__()
            return event

        reader_task = asyncio.create_task(reader())
        await asyncio.sleep(0.05)
        await pubsub.publish("test", {"key": "val"})
        result = await asyncio.wait_for(reader_task, timeout=0.5)
        assert result["key"] == "val"

    async def test_subscribe_fallback_cleanup(self, pubsub):
        async def reader():
            gen = pubsub.subscribe("test")
            try:
                await gen.__anext__()
            except asyncio.CancelledError:
                pass

        reader_task = asyncio.create_task(reader())
        await asyncio.sleep(0.02)
        reader_task.cancel()
        await asyncio.sleep(0.02)
        try:
            await reader_task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass
        await asyncio.sleep(0.02)
        assert len(pubsub._fallback_channels.get("test", set())) == 0

    async def test_subscribe_empty_channel(self, pubsub):
        with pytest.raises(StopAsyncIteration):
            gen = pubsub.subscribe("")
            await gen.__anext__()

    async def test_publish_with_redis(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis = AsyncMock()
        mock_redis.publish.return_value = 1

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            await pubsub.publish("ch", {"data": "hello"})
        mock_redis.publish.assert_called_once()

    async def test_publish_redis_fallback_on_error(self, pubsub):
        pubsub._redis_enabled = True
        mock_redis = AsyncMock()
        mock_redis.publish.side_effect = Exception("redis down")
        q = asyncio.Queue()
        pubsub._fallback_channels["ch"] = {q}

        async def mock_get_redis():
            return mock_redis

        with patch.object(pubsub, "_get_redis", mock_get_redis):
            await pubsub.publish("ch", {"data": "hello"})
        result = await asyncio.wait_for(q.get(), timeout=0.5)
        assert result["data"] == "hello"

    async def test_get_redis_returns_cached(self):
        with patch("app.realtime.pubsub.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_settings.REDIS_ENABLED = True
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub()
            ps._redis_warning_logged = False
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = mock_client
                client1 = await ps._get_redis()
                client2 = await ps._get_redis()
        assert client1 is not None
        assert client2 is not None

    async def test_get_redis_connection_error(self):
        with patch("app.realtime.pubsub.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_settings.REDIS_ENABLED = True
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub()
            ps._redis_warning_logged = False
            with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
                mock_aioredis.from_url.return_value = AsyncMock()
                mock_aioredis.from_url.return_value.ping.side_effect = Exception("connection error")
                client = await ps._get_redis()
        assert client is None
        assert ps._force_fallback is True

    async def test_queue_full_skipped(self, pubsub):
        q = asyncio.Queue(maxsize=1)
        q.put_nowait("fill")
        pubsub._fallback_channels["ch"] = {q}
        await pubsub.publish("ch", {"data": "hello"})
        assert q.qsize() == 1

    async def test_subscribe_fallback_no_events(self, pubsub):
        import time
        gen = pubsub.subscribe("empty_ch")
        task = asyncio.create_task(gen.__anext__())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, StopAsyncIteration):
            pass
