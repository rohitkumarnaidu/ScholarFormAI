from __future__ import annotations


class TestApiKeyUsageLog:
    def test_tablename(self):
        from app.models.api_key_usage_log import ApiKeyUsageLog

        assert ApiKeyUsageLog.__tablename__ == "api_key_usage_log"

    def test_columns_defined(self):
        from app.models.api_key_usage_log import ApiKeyUsageLog

        cols = ApiKeyUsageLog.__table__.columns
        assert "id" in cols
        assert "user_api_key_id" in cols
        assert "endpoint" in cols
        assert "model" in cols
        assert "tokens_used" in cols
        assert "status_code" in cols
        assert "response_time_ms" in cols

    def test_user_api_key_id_indexed(self):
        from app.models.api_key_usage_log import ApiKeyUsageLog

        col = ApiKeyUsageLog.__table__.columns["user_api_key_id"]
        assert col.index is True
