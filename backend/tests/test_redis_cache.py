from unittest.mock import MagicMock, patch

import pytest

MODULE = "app.cache.redis_cache"


class TestRedisCache:
    @pytest.fixture
    def cache(self):
        from app.cache.redis_cache import RedisCache
        return RedisCache()

    def test_init_sets_client_none(self):
        from app.cache.redis_cache import RedisCache
        c = RedisCache()
        assert c._client is None
        assert c._initialized is False

    def test_init_with_redis_url(self):
        from app.cache.redis_cache import RedisCache
        c = RedisCache(redis_url="redis://myhost:6379")
        assert c._init_kwargs["redis_url"] == "redis://myhost:6379"

    def test_client_property_calls_ensure(self, cache):
        with patch.object(cache, "_ensure_client", return_value="mock") as m:
            result = cache.client
            assert result == "mock"
            m.assert_called_once()

    def test_generate_key_uses_sha256(self, cache):
        key = cache._generate_key("hello", prefix="test")
        assert key.startswith("test:")
        assert len(key) > 10

    def test_ensure_client_already_initialized(self, cache):
        cache._initialized = True
        cache._client = "mock-client"
        result = cache._ensure_client()
        assert result == "mock-client"

    def test_ensure_client_disabled(self, cache):
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.REDIS_ENABLED = False
            result = cache._ensure_client()
            assert result is None
            assert cache._initialized is True
            assert cache._client is None

    def test_ensure_client_connection_success(self, cache):
        with patch("app.config.settings.settings") as mock_settings, \
             patch("redis.Redis.from_url") as mock_from_url:
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            result = cache._ensure_client()
            mock_from_url.assert_called_once()
            mock_redis.ping.assert_called_once()
            assert result is not None

    def test_ensure_client_connection_failure(self, cache):
        with patch("app.config.settings.settings") as mock_settings, \
             patch("redis.Redis.from_url") as mock_from_url:
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_from_url.side_effect = ConnectionError("no redis")
            result = cache._ensure_client()
            assert result is None
            assert cache._client is None

    def test_get_grobid_result_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            assert cache.get_grobid_result("content") is None

    def test_get_grobid_result_cache_hit(self, cache):
        mock_client = MagicMock()
        mock_client.get.return_value = '{"key": "value"}'
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            result = cache.get_grobid_result("content")
            assert result == {"key": "value"}
            mock_client.get.assert_called_once()

    def test_get_grobid_result_cache_miss(self, cache):
        mock_client = MagicMock()
        mock_client.get.return_value = None
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.get_grobid_result("content") is None

    def test_get_grobid_result_error(self, cache):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.get_grobid_result("content") is None

    def test_set_grobid_result_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            cache.set_grobid_result("content", {"key": "val"})

    def test_set_grobid_result_success(self, cache):
        mock_client = MagicMock()
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.set_grobid_result("content", {"key": "val"}, ttl=3600)
            mock_client.setex.assert_called_once()

    def test_set_grobid_result_error(self, cache):
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.set_grobid_result("content", {"key": "val"})

    def test_get_llm_result_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            assert cache.get_llm_result("key") is None

    def test_get_llm_result_hit(self, cache):
        mock_client = MagicMock()
        mock_client.get.return_value = "cached text"
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.get_llm_result("key") == "cached text"

    def test_get_llm_result_miss(self, cache):
        mock_client = MagicMock()
        mock_client.get.return_value = None
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.get_llm_result("key") is None

    def test_get_llm_result_error(self, cache):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.get_llm_result("key") is None

    def test_set_llm_result_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            cache.set_llm_result("key", "text")

    def test_set_llm_result_success(self, cache):
        mock_client = MagicMock()
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.set_llm_result("key", "text", ttl=86400)
            mock_client.setex.assert_called_once_with("key", 86400, "text")

    def test_set_llm_result_error(self, cache):
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.set_llm_result("key", "text")

    def test_delete_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            cache.delete("key")

    def test_delete_success(self, cache):
        mock_client = MagicMock()
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.delete("key")
            mock_client.delete.assert_called_once_with("key")

    def test_delete_error(self, cache):
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.delete("key")

    def test_clear_no_client(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            cache.clear()

    def test_clear_success(self, cache):
        mock_client = MagicMock()
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.clear()
            mock_client.flushdb.assert_called_once()

    def test_clear_error(self, cache):
        mock_client = MagicMock()
        mock_client.flushdb.side_effect = Exception("redis down")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            cache.clear()

    def test_health_unavailable(self, cache):
        with patch.object(cache, "_ensure_client", return_value=None):
            assert cache.health() == {"status": "unavailable"}

    def test_health_available(self, cache):
        mock_client = MagicMock()
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            assert cache.health() == {"status": "available"}
            mock_client.ping.assert_called_once()

    def test_health_unavailable_detail(self, cache):
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("timeout")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            result = cache.health()
            assert result["status"] == "unavailable"

    def test_get_redis_cache_returns_singleton(self):
        from app.cache.redis_cache import get_redis_cache, redis_cache
        assert get_redis_cache() is redis_cache

    def test_ensure_client_settings_exception(self, cache):
        with patch("app.config.settings.settings") as mock_settings:
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = None
            mock_settings.REDIS_HOST = "myhost"
            mock_settings.REDIS_PORT = 6380
            mock_settings.REDIS_PASSWORD = "pass"
            with patch("redis.Redis.from_url", side_effect=Exception("conn failed")):
                result = cache._ensure_client()
            assert result is None

    def test_ensure_client_redis_url_from_settings(self, cache):
        with patch("app.config.settings.settings") as mock_settings, \
             patch("redis.Redis.from_url") as mock_from_url:
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = None
            mock_settings.REDIS_HOST = "myhost"
            mock_settings.REDIS_PORT = 6380
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            cache._ensure_client()
            url_arg = mock_from_url.call_args[0][0]
            assert "myhost" in url_arg
            assert "6380" in url_arg
