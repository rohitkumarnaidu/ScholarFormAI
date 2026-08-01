from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def pubsub():
    with patch("app.realtime.pubsub.aioredis", None), patch("app.realtime.pubsub.settings.REDIS_ENABLED", False):
        from app.realtime.pubsub import RedisPubSub
        yield RedisPubSub(redis_url="redis://localhost:6379")


class TestRedisPubSub:
    @pytest.mark.asyncio
    async def test_publish_no_channel_returns(self, pubsub):
        await pubsub.publish("", {"key": "val"})

    @pytest.mark.asyncio
    async def test_publish_to_fallback_queue(self, pubsub):
        q = __import__("asyncio").Queue()
        pubsub._fallback_channels["test_ch"] = {q}
        await pubsub.publish("test_ch", {"msg": "hello"})
        result = await q.get()
        assert result == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_subscribe_fallback(self, pubsub):
        import asyncio
        async def reader():
            async for event in pubsub.subscribe("test_ch"):
                return event
        async def writer():
            await asyncio.sleep(0.05)
            await pubsub.publish("test_ch", {"msg": "hello"})
        result = await asyncio.gather(reader(), writer())
        assert result[0] == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_publish_redis_path(self):
        with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_aioredis.from_url.return_value = mock_redis
            with patch("app.realtime.pubsub.settings.REDIS_ENABLED", True):
                from app.realtime.pubsub import RedisPubSub
                ps = RedisPubSub(redis_url="redis://localhost:6379")
                await ps.publish("ch", {"x": 1})
                mock_redis.publish.assert_awaited_once_with("ch", '{"x": 1}')

    @pytest.mark.asyncio
    async def test_publish_redis_fallback_on_error(self, pubsub):
        with patch("app.realtime.pubsub.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.publish.side_effect = ConnectionError("no redis")
            mock_aioredis.from_url.return_value = mock_redis
            with patch("app.realtime.pubsub.settings.REDIS_ENABLED", True):
                from app.realtime.pubsub import RedisPubSub
                ps = RedisPubSub(redis_url="redis://localhost:6379")
                q = __import__("asyncio").Queue()
                ps._fallback_channels["ch"] = {q}
                await ps.publish("ch", {"fall": "back"})
                result = await q.get()
                assert result == {"fall": "back"}

    @pytest.mark.asyncio
    async def test_get_redis_returns_none_when_disabled(self, pubsub):
        result = await pubsub._get_redis()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_returns_none_when_no_aioredis(self):
        with patch("app.realtime.pubsub.aioredis", None):
            from app.realtime.pubsub import RedisPubSub
            ps = RedisPubSub(redis_url="redis://localhost:6379")
            result = await ps._get_redis()
            assert result is None
