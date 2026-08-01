from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.utils.dependencies import get_current_user


@pytest.fixture
def client():
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.role = "authenticated"
    mock_db = MagicMock(autospec=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_encryption = MagicMock()
    mock_encryption.encrypt.return_value = "encrypted:key"
    mock_encryption.decrypt.return_value = "decrypted-key"

    with (
        patch("app.routers.v1.providers.get_db", return_value=mock_db),
        patch("app.routers.v1.providers.get_encryption_service", return_value=mock_encryption),
    ):
        with TestClient(app) as test_client:
            test_client.mock_db = mock_db
            test_client.mock_user = mock_user
            test_client.mock_encryption = mock_encryption
            yield test_client

    app.dependency_overrides = {}


class TestGetProviders:
    def test_success(self, client):
        with patch("app.routers.v1.providers.list_available_models") as mock_list:
            mock_list.return_value = [
                {"provider_id": "openai", "name": "OpenAI", "models": ["gpt-4o"], "key_configured": True, "is_custom": False},
                {"provider_id": "anthropic", "name": "Anthropic", "models": ["claude-3"], "key_configured": False, "is_custom": False},
            ]
            response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) == 2
        assert data["providers"][0]["provider_id"] == "openai"

    def test_passes_db_and_user(self, client):
        with patch("app.routers.v1.providers.list_available_models") as mock_list:
            mock_list.return_value = []
            client.get("/api/v1/providers")
        mock_list.assert_called_once_with(db=client.mock_db, user_id="user-123")


class TestGetBuiltin:
    def test_returns_builtin_providers(self, client):
        with patch("app.routers.v1.providers.get_builtin_providers") as mock_builtin:
            mock_builtin.return_value = {"openai": {"name": "OpenAI"}}
            response = client.get("/api/v1/providers/builtin")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert data["providers"]["openai"]["name"] == "OpenAI"


class TestCreateCustomProvider:
    def test_success(self, client):
        with patch("app.models.custom_provider.CustomProvider.to_dict") as mock_to_dict:
            mock_to_dict.return_value = {
                "id": "cp-new",
                "name": "My Local LLM",
                "base_url": "http://localhost:8080/v1",
                "models": ["model-x", "model-y"],
                "is_local": True,
                "description": "My test server",
                "is_active": True,
                "created_at": None,
                "updated_at": None,
            }
            response = client.post("/api/v1/providers/custom", json={
                "name": "My Local LLM",
                "base_url": "http://localhost:8080/v1",
                "models": ["model-x", "model-y"],
                "is_local": True,
                "description": "My test server",
            })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Local LLM"
        assert data["models"] == ["model-x", "model-y"]

    def test_strips_trailing_slash(self, client):
        with patch("app.models.custom_provider.CustomProvider.to_dict") as mock_to_dict:
            mock_to_dict.return_value = {
                "id": "cp-2", "name": "Test", "base_url": "http://localhost:8080/v1",
                "models": [], "is_local": False, "description": None,
                "is_active": True, "created_at": None, "updated_at": None,
            }
            response = client.post("/api/v1/providers/custom", json={
                "name": "Test",
                "base_url": "http://localhost:8080/v1/",
            })
        assert response.status_code == 201

    def test_encrypts_api_key(self, client):
        with patch("app.models.custom_provider.CustomProvider.to_dict") as mock_to_dict:
            mock_to_dict.return_value = {
                "id": "cp-3", "name": "Key Test", "base_url": "http://localhost:8080/v1",
                "models": [], "is_local": False, "description": None,
                "is_active": True, "created_at": None, "updated_at": None,
            }
            response = client.post("/api/v1/providers/custom", json={
                "name": "Key Test",
                "base_url": "http://localhost:8080/v1",
                "api_key": "sk-secret-key",
            })
        assert response.status_code == 201
        client.mock_encryption.encrypt.assert_called_once_with("sk-secret-key")

    def test_missing_name_returns_422(self, client):
        response = client.post("/api/v1/providers/custom", json={
            "base_url": "http://localhost:8080/v1",
        })
        assert response.status_code == 422


class TestListCustomProviders:
    def test_success(self, client):
        mock_cp = MagicMock()
        mock_cp.to_dict.return_value = {
            "id": "cp-1", "name": "My Provider", "base_url": "http://localhost:8080/v1",
            "models": ["m1"], "is_local": False, "description": None,
            "is_active": True, "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00",
        }
        client.mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_cp]

        response = client.get("/api/v1/providers/custom")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Provider"
        assert data[0]["id"] == "cp-1"

    def test_empty(self, client):
        client.mock_db.execute.return_value.scalars.return_value.all.return_value = []
        response = client.get("/api/v1/providers/custom")
        assert response.status_code == 200
        assert response.json() == []


class TestGetCustomProvider:
    def test_found(self, client):
        mock_cp = MagicMock()
        mock_cp.to_dict.return_value = {
            "id": "cp-1", "name": "My Provider", "base_url": "http://localhost:8080/v1",
            "models": [], "is_local": False, "description": None,
            "is_active": True, "created_at": None, "updated_at": None,
        }
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cp

        response = client.get("/api/v1/providers/custom/cp-1")
        assert response.status_code == 200
        assert response.json()["id"] == "cp-1"

    def test_not_found(self, client):
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = client.get("/api/v1/providers/custom/cp-nonexistent")
        assert response.status_code == 404


class TestUpdateCustomProvider:
    def test_success(self, client):
        mock_cp = MagicMock()
        mock_cp.to_dict.return_value = {
            "id": "cp-1", "name": "Updated Name", "base_url": "http://localhost:8080/v1",
            "models": ["m1", "m2"], "is_local": True, "description": "updated",
            "is_active": True, "created_at": None, "updated_at": None,
        }
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cp

        response = client.put("/api/v1/providers/custom/cp-1", json={
            "name": "Updated Name",
            "models": ["m1", "m2"],
            "is_local": True,
            "description": "updated",
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert mock_cp.name == "Updated Name"
        assert mock_cp.models == ["m1", "m2"]

    def test_not_found(self, client):
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = client.put("/api/v1/providers/custom/cp-nonexistent", json={"name": "New"})
        assert response.status_code == 404

    def test_updates_api_key(self, client):
        mock_cp = MagicMock()
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cp

        response = client.put("/api/v1/providers/custom/cp-1", json={"api_key": "new-secret-key"})
        assert response.status_code == 200
        client.mock_encryption.encrypt.assert_called_once_with("new-secret-key")


class TestDeleteCustomProvider:
    def test_success(self, client):
        mock_cp = MagicMock()
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = mock_cp

        response = client.delete("/api/v1/providers/custom/cp-1")
        assert response.status_code == 204
        client.mock_db.delete.assert_called_once_with(mock_cp)

    def test_not_found(self, client):
        client.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        response = client.delete("/api/v1/providers/custom/cp-nonexistent")
        assert response.status_code == 404


class TestTestProviderConnection:
    def test_ollama_success(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"name": "deepseek-r1"}, {"name": "llama3"}]}

            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=ollama&base_url=http://localhost:11434")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"
        assert "Ollama" in data["message"]
        assert "deepseek-r1" in data["models_found"]

    def test_ollama_failure(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 500

            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=ollama&base_url=http://localhost:11434")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "invalid"

    def test_openai_compatible_success(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}

            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=openai&base_url=https://api.openai.com/v1&api_key=sk-test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"
        assert "gpt-4o" in data["models_found"]

    def test_openai_compatible_no_data_key(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"id": "model-x"}]}

            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=openai&base_url=https://api.openai.com/v1&api_key=sk-test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"
        assert len(data["models_found"]) == 0

    def test_exception_handled(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(side_effect=ConnectionError("refused"))
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=openai&base_url=https://api.openai.com/v1&api_key=sk-test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_provider_info_resolved_when_no_base_url(self, client):
        with patch("app.routers.v1.providers.get_provider_info") as mock_info:
            mock_info.return_value = {"base_url": "https://api.openai.com/v1"}
            with patch("httpx.AsyncClient") as mock_async_client:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"data": [{"id": "gpt-4o"}]}
                mock_client_instance = MagicMock()
                mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
                mock_async_client.return_value = mock_client_instance

                response = client.post("/api/v1/providers/test?provider_id=openai&api_key=sk-test")
            assert response.status_code == 200
            assert response.json()["status"] == "valid"

    def test_provider_not_found_raises_404(self, client):
        with patch("app.routers.v1.providers.get_provider_info", return_value=None):
            client.mock_db.execute.return_value.scalar_one_or_none.return_value = None
            response = client.post("/api/v1/providers/test?provider_id=nonexistent")
        assert response.status_code == 404

    def test_uses_provider_id_11434_pattern_for_ollama(self, client):
        with patch("httpx.AsyncClient") as mock_async_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"name": "llama3"}]}
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_async_client.return_value = mock_client_instance

            response = client.post("/api/v1/providers/test?provider_id=custom&base_url=http://localhost:11434")
        assert response.status_code == 200
        data = response.json()
        assert "Ollama" in data["message"]
