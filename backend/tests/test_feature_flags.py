from unittest.mock import MagicMock, patch

import pytest


class TestGetFlag:
    @pytest.fixture
    def svc(self):
        from app.services.feature_flags import FeatureFlagService
        return FeatureFlagService()

    def test_returns_default_for_unknown(self, svc):
        result = svc.get_flag("nonexistent")
        assert result is None

    def test_returns_default_flag_value(self, svc):
        result = svc.get_flag("new_upload_flow")
        assert result is False

    def test_returns_in_memory_value(self, svc):
        svc._cache["test_flag"] = "custom"
        assert svc.get_flag("test_flag") == "custom"

    def test_redis_cache_hit(self, svc):
        mock_redis = MagicMock()
        mock_redis.get.return_value = '"redis_value"'
        svc._redis = mock_redis
        import redis as real_redis
        orig_isinstance = isinstance
        def isinstance_passthrough(obj, klass):
            if klass is real_redis.Redis:
                return True
            return orig_isinstance(obj, klass)
        with patch("builtins.isinstance", isinstance_passthrough):
            result = svc.get_flag("test_flag")
        assert result == "redis_value"

    def test_redis_unavailable_falls_through(self, svc):
        import redis as redis_mod

        class MockRedis(redis_mod.Redis):
            def get(self, key):
                raise Exception("redis down")

        svc._redis = MockRedis()
        svc._cache["test_flag"] = "cache_value"
        result = svc.get_flag("test_flag")
        assert result == "cache_value"

    def test_db_fallback(self, svc):
        mock_db = MagicMock()
        svc._db = mock_db
        svc._load_from_db = MagicMock(return_value="db_value")
        result = svc.get_flag("test_flag")
        assert result == "db_value"


class TestSetFlag:
    @pytest.fixture
    def svc(self):
        from app.services.feature_flags import FeatureFlagService
        return FeatureFlagService()

    def test_sets_in_cache(self, svc):
        svc.set_flag("my_flag", "my_value")
        assert svc._cache["my_flag"] == "my_value"

    def test_sets_redis_cache(self, svc):
        mock_redis = MagicMock()
        svc._redis = mock_redis
        import redis as real_redis
        orig = isinstance
        def isinstance_patch(obj, klass):
            if klass is real_redis.Redis:
                return True
            return orig(obj, klass)
        with patch("builtins.isinstance", isinstance_patch):
            svc.set_flag("my_flag", True)
        mock_redis.setex.assert_called_once_with("flag:my_flag", 300, "true")

    def test_saves_to_db(self, svc):
        mock_db = MagicMock()
        svc._db = mock_db
        svc._save_to_db = MagicMock()
        svc.set_flag("my_flag", 42)
        svc._save_to_db.assert_called_once()


class TestGetAllFlags:
    @pytest.fixture
    def svc(self):
        from app.services.feature_flags import FeatureFlagService
        return FeatureFlagService()

    def test_returns_all_defaults_plus_cache(self, svc):
        svc._cache["test_extra"] = True
        flags = svc.get_all_flags()
        assert flags["new_upload_flow"] is False
        assert flags["ai_suggestions"] is True
        assert flags["test_extra"] is True

    def test_includes_db_overrides(self, svc):
        mock_db = MagicMock()
        svc._db = mock_db
        svc._load_all_from_db = MagicMock(return_value={"new_upload_flow": True})
        flags = svc.get_all_flags()
        assert flags["new_upload_flow"] is True


class TestGetFeatureFlag:
    def test_convenience_function(self):
        from app.services.feature_flags import get_feature_flag
        svc = MagicMock()
        svc.get_flag.return_value = True
        with patch("app.services.feature_flags.get_feature_flag_service", return_value=svc):
            result = get_feature_flag("test_flag", default=False)
        assert result is True
        svc.get_flag.assert_called_once_with("test_flag", False, None)


class TestGetFeatureFlagService:
    def test_returns_singleton(self):
        from app.services.feature_flags import get_feature_flag_service
        s1 = get_feature_flag_service()
        s2 = get_feature_flag_service()
        assert s1 is s2
