from unittest.mock import MagicMock

import pytest


class TestApiKeyService:
    @pytest.fixture
    def svc(self):
        from app.services.api_key_service import ApiKeyService

        db = MagicMock()
        svc = ApiKeyService(db)
        svc.encryption = MagicMock()
        svc.encryption.encrypt.side_effect = lambda x: f"enc_{x}"
        svc.encryption.decrypt.side_effect = lambda x: x.replace("enc_", "")
        return svc

    def test_create_key_unsupported_provider_raises(self, svc):
        with pytest.raises(ValueError, match="Unsupported provider"):
            svc.create_key("user-1", "unknown_provider", "sk-test")

    def test_create_key_success(self, svc):
        key = svc.create_key("user-1", "openai", "sk-test", key_label="My Key")
        assert key.provider == "openai"
        assert key.api_key_encrypted == "enc_sk-test"
        svc.db.add.assert_called_once()
        svc.db.commit.assert_called_once()

    def test_get_key_found(self, svc):
        svc.db.execute.return_value.scalar_one_or_none.return_value = "key_obj"
        result = svc.get_key("key-1", "user-1")
        assert result == "key_obj"

    def test_get_key_not_found(self, svc):
        svc.db.execute.return_value.scalar_one_or_none.return_value = None
        result = svc.get_key("key-1", "user-1")
        assert result is None

    def test_list_keys(self, svc):
        svc.db.execute.return_value.scalars.return_value.all.return_value = ["k1", "k2"]
        result = svc.list_keys("user-1")
        assert result == ["k1", "k2"]

    def test_update_key_updates_fields(self, svc):
        existing = MagicMock()
        existing.key_label = "Old"
        existing.is_active = True
        svc.get_key = MagicMock(return_value=existing)
        svc.update_key("key-1", "user-1", key_label="New Label", is_active=False)
        assert existing.key_label == "New Label"
        assert existing.is_active is False
        svc.db.commit.assert_called_once()

    def test_update_key_not_found(self, svc):
        svc.get_key = MagicMock(return_value=None)
        result = svc.update_key("key-1", "user-1", key_label="New")
        assert result is None

    def test_delete_key(self, svc):
        existing = MagicMock()
        svc.get_key = MagicMock(return_value=existing)
        result = svc.delete_key("key-1", "user-1")
        assert result is True
        svc.db.delete.assert_called_once_with(existing)
        svc.db.commit.assert_called_once()

    def test_delete_key_not_found(self, svc):
        svc.get_key = MagicMock(return_value=None)
        result = svc.delete_key("key-1", "user-1")
        assert result is False

    def test_decrypt_key(self, svc):
        key = MagicMock()
        key.api_key_encrypted = "enc_sk-test"
        assert svc.decrypt_key(key) == "sk-test"

    def test_increment_usage(self, svc):
        existing = MagicMock()
        existing.total_requests = 5
        svc.db.execute.return_value.scalar_one_or_none.return_value = existing
        svc.increment_usage("key-1")
        assert existing.total_requests == 6
        svc.db.commit.assert_called_once()

    def test_get_supported_providers(self, svc):
        from app.services.api_key_service import ApiKeyService

        providers = ApiKeyService.get_supported_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "cohere" in providers

    def test_get_active_key_found(self, svc):
        svc.db.execute.return_value.scalar_one_or_none.return_value = "active_key"
        result = svc.get_active_key("user-1", "openai")
        assert result == "active_key"

    def test_get_active_key_not_found(self, svc):
        svc.db.execute.return_value.scalar_one_or_none.return_value = None
        result = svc.get_active_key("user-1", "openai")
        assert result is None

    def test_log_usage(self, svc):
        svc.log_usage("key-1", endpoint="/chat", model="gpt-4", tokens_used=100, status_code=200, response_time_ms=500)
        svc.db.add.assert_called_once()
        svc.db.commit.assert_called_once()

    def test_get_usage_stats_empty(self, svc):
        svc.db.execute.return_value.all.return_value = []
        stats = svc.get_usage_stats("user-1", hours=24)
        assert stats == {}

    def test_get_usage_stats_with_data(self, svc):
        row = MagicMock()
        row.provider = "openai"
        row.total_requests = 10
        row.total_tokens = 500
        row.avg_response_time = 250.0
        svc.db.execute.return_value.all.return_value = [row]
        stats = svc.get_usage_stats("user-1", hours=24)
        assert stats["openai"]["total_requests"] == 10
        assert stats["openai"]["total_tokens"] == 500
        assert stats["openai"]["avg_response_time_ms"] == 250.0

    def test_get_usage_stats_null_avg(self, svc):
        row = MagicMock()
        row.provider = "anthropic"
        row.total_requests = 5
        row.total_tokens = 0
        row.avg_response_time = None
        svc.db.execute.return_value.all.return_value = [row]
        stats = svc.get_usage_stats("user-1", hours=24)
        assert stats["anthropic"]["avg_response_time_ms"] == 0

    def test_increment_usage_key_not_found(self, svc):
        svc.db.execute.return_value.scalar_one_or_none.return_value = None
        svc.increment_usage("key-missing")
        svc.db.commit.assert_not_called()

    def test_list_keys_with_provider_filter(self, svc):
        svc.db.execute.return_value.scalars.return_value.all.return_value = ["k1"]
        result = svc.list_keys("user-1", provider="openai")
        assert result == ["k1"]

    def test_update_key_partial_fields(self, svc):
        existing = MagicMock()
        existing.key_label = "Old"
        existing.is_active = True
        existing.rate_limit_per_minute = 10
        svc.get_key = MagicMock(return_value=existing)
        svc.update_key("key-1", "user-1", rate_limit_per_minute=30)
        assert existing.rate_limit_per_minute == 30
        assert existing.key_label == "Old"
        svc.db.commit.assert_called_once()

    def test_create_key_uses_default_label(self, svc):
        key = svc.create_key("user-1", "openai", "sk-test")
        assert key.key_label == "OpenAI Key"

    def test_create_key_nvidia_uses_defaults(self, svc):
        key = svc.create_key("user-1", "nvidia", "nv-key")
        assert key.rate_limit_per_minute == 60
        assert key.rate_limit_per_hour == 1000
        assert key.daily_quota == 10000
