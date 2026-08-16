from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


@pytest.fixture
def client():
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.role = "authenticated"

    mock_db = MagicMock()
    mock_service = MagicMock()

    from app.db.session import get_db

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.routers.v1.api_keys.ApiKeyService", return_value=mock_service) as _patched:
        with TestClient(app) as test_client:
            test_client.mock_service = mock_service
            test_client.mock_user = mock_user
            yield test_client

    app.dependency_overrides = {}


class TestCreateApiKey:
    def test_success(self, client):
        key_dict = {
            "id": "key-1",
            "provider": "openai",
            "key_label": "My Key",
            "is_active": True,
            "rate_limit_per_minute": 60,
            "rate_limit_per_hour": 1000,
            "daily_quota": 10000,
            "total_requests": 0,
            "last_request_at": None,
            "created_at": "2024-01-01T00:00:00",
            "key_preview": "sk-...abc",
        }
        client.mock_service.create_key.return_value = MagicMock(to_dict=lambda mask_key=True: key_dict)

        response = client.post(
            "/api/v1/keys",
            json={
                "provider": "openai",
                "api_key": "sk-test-key-12345",
            },
        )
        assert response.status_code == 201
        assert response.json()["provider"] == "openai"

    def test_value_error(self, client):
        client.mock_service.create_key.side_effect = ValueError("Invalid provider")
        response = client.post(
            "/api/v1/keys",
            json={
                "provider": "unknown",
                "api_key": "sk-test-key-12345",
            },
        )
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["error"]["message"]

    def test_short_key(self, client):
        response = client.post(
            "/api/v1/keys",
            json={
                "provider": "openai",
                "api_key": "short",
            },
        )
        assert response.status_code == 422


class TestListApiKeys:
    def test_success(self, client):
        key_dict = {
            "id": "key-1",
            "provider": "openai",
            "key_label": None,
            "is_active": True,
            "rate_limit_per_minute": 60,
            "rate_limit_per_hour": 1000,
            "daily_quota": 10000,
            "total_requests": 0,
            "last_request_at": None,
            "created_at": None,
            "key_preview": "sk-...abc",
        }
        client.mock_service.list_keys.return_value = [MagicMock(to_dict=lambda mask_key=True: key_dict)]

        response = client.get("/api/v1/keys")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["provider"] == "openai"

    def test_filter_by_provider(self, client):
        client.mock_service.list_keys.return_value = []
        response = client.get("/api/v1/keys?provider=openai")
        assert response.status_code == 200
        client.mock_service.list_keys.assert_called_once_with(user_id="user-123", provider="openai")


class TestGetApiKey:
    def test_found(self, client):
        key_dict = {
            "id": "key-1",
            "provider": "anthropic",
            "key_label": None,
            "is_active": True,
            "rate_limit_per_minute": 60,
            "rate_limit_per_hour": 1000,
            "daily_quota": 10000,
            "total_requests": 0,
            "last_request_at": None,
            "created_at": None,
            "key_preview": "sk-...xyz",
        }
        client.mock_service.get_key.return_value = MagicMock(to_dict=lambda mask_key=True: key_dict)

        response = client.get("/api/v1/keys/key-1")
        assert response.status_code == 200
        assert response.json()["provider"] == "anthropic"

    def test_not_found(self, client):
        client.mock_service.get_key.return_value = None
        response = client.get("/api/v1/keys/nonexistent")
        assert response.status_code == 404


class TestUpdateApiKey:
    def test_success(self, client):
        key_dict = {
            "id": "key-1",
            "provider": "openai",
            "key_label": "Updated",
            "is_active": False,
            "rate_limit_per_minute": 30,
            "rate_limit_per_hour": 500,
            "daily_quota": 5000,
            "total_requests": 0,
            "last_request_at": None,
            "created_at": None,
            "key_preview": "sk-...abc",
        }
        client.mock_service.update_key.return_value = MagicMock(to_dict=lambda mask_key=True: key_dict)

        response = client.put("/api/v1/keys/key-1", json={"key_label": "Updated", "is_active": False})
        assert response.status_code == 200
        assert response.json()["key_label"] == "Updated"

    def test_not_found(self, client):
        client.mock_service.update_key.return_value = None
        response = client.put("/api/v1/keys/nonexistent", json={"key_label": "Nope"})
        assert response.status_code == 404


class TestDeleteApiKey:
    def test_success(self, client):
        client.mock_service.delete_key.return_value = True
        response = client.delete("/api/v1/keys/key-1")
        assert response.status_code == 204

    def test_not_found(self, client):
        client.mock_service.delete_key.return_value = False
        response = client.delete("/api/v1/keys/nonexistent")
        assert response.status_code == 404


class TestUsageStats:
    def test_get_stats_direct(self):
        from unittest.mock import MagicMock

        from app.routers.v1.api_keys import get_usage_stats

        service = MagicMock()
        service.get_usage_stats.return_value = {
            "openai": {"total_requests": 10, "total_tokens": 5000, "avg_response_time_ms": 320.0},
        }
        with patch("app.routers.v1.api_keys.ApiKeyService", return_value=service):
            import asyncio

            result = asyncio.run(get_usage_stats(hours=48, db=MagicMock(), user=MagicMock()))
        assert "openai" in result

    def test_get_key_usage_direct(self):
        import asyncio
        from unittest.mock import MagicMock

        from app.routers.v1.api_keys import get_key_usage

        key = MagicMock()
        key.total_requests = 5
        key.last_request_at = None
        key.rate_limit_per_minute = 60
        key.rate_limit_per_hour = 1000
        key.daily_quota = 10000

        service = MagicMock()
        service.get_key.return_value = key

        mock_limiter = MagicMock()
        mock_limiter.get_usage.return_value = {"minute": 1, "hour": 5}

        with (
            patch("app.routers.v1.api_keys.ApiKeyService", return_value=service),
            patch("app.routers.v1.api_keys.get_api_key_rate_limiter", return_value=mock_limiter),
        ):
            result = asyncio.run(get_key_usage(key_id="key-1", db=MagicMock(), user=MagicMock()))
        assert result["key_id"] == "key-1"

    def test_get_key_usage_not_found_direct(self):
        import asyncio
        from unittest.mock import MagicMock

        from app.routers.v1.api_keys import get_key_usage

        service = MagicMock()
        service.get_key.return_value = None

        with patch("app.routers.v1.api_keys.ApiKeyService", return_value=service), pytest.raises(Exception):
            asyncio.run(get_key_usage(key_id="nonexistent", db=MagicMock(), user=MagicMock()))


class TestProviders:
    def test_get_supported_providers(self, client):
        with patch(
            "app.routers.v1.api_keys.ApiKeyService.get_supported_providers",
            return_value={
                "openai": {"name": "OpenAI", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
            },
        ):
            import asyncio

            from app.routers.v1.api_keys import get_supported_providers

            result = asyncio.run(get_supported_providers())
        assert "openai" in result
        assert result["openai"].default_rpm == 60
        assert result["openai"].default_rph == 1000
        assert result["openai"].default_daily == 10000


class TestTestApiKey:
    def test_skipped_provider(self, client):
        response = client.post(
            "/api/v1/keys/test",
            json={
                "provider": "custom",
                "api_key": "sk-test-key-12345",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"

    def test_short_key(self, client):
        response = client.post(
            "/api/v1/keys/test",
            json={
                "provider": "openai",
                "api_key": "short",
            },
        )
        assert response.status_code == 422

    def test_openai_valid(self, client):
        mock_resp = MagicMock(status_code=200)
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cm = AsyncMock(__aenter__=AsyncMock(return_value=mock_http))

        with patch("httpx.AsyncClient", return_value=mock_cm):
            response = client.post(
                "/api/v1/keys/test",
                json={
                    "provider": "openai",
                    "api_key": "sk-test-key-12345",
                },
            )
        assert response.status_code == 200
        assert response.json()["status"] == "valid"

    def test_openai_invalid(self, client):
        mock_resp = MagicMock(status_code=401, text="Unauthorized")
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cm = AsyncMock(__aenter__=AsyncMock(return_value=mock_http))

        with patch("httpx.AsyncClient", return_value=mock_cm):
            response = client.post(
                "/api/v1/keys/test",
                json={
                    "provider": "openai",
                    "api_key": "sk-bad-key",
                },
            )
        assert response.status_code == 200
        assert response.json()["status"] == "invalid"
