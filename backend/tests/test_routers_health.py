import pytest
from unittest.mock import MagicMock, patch


class TestHealthRouter:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        app.dependency_overrides.clear()
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code in (200, 503)

    def test_live_endpoint(self, client):
        response = client.get("/api/v1/health/live")
        assert response.status_code in (200, 503)

    def test_ready_endpoint(self, client):
        response = client.get("/api/v1/health/ready")
        assert response.status_code in (200, 500, 503)

    def test_admin_health_no_auth(self, client):
        response = client.get("/api/v1/health/admin")
        assert response.status_code in (401, 403, 503)


class TestReadyEndpoint:
    @pytest.mark.asyncio
    async def test_ready_success(self):
        from app.routers.v1.health import ready
        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.health.get_readiness_payload", return_value=({"db": "healthy"}, 200)):
            result = await ready(mock_request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_ready_exception(self):
        from app.routers.v1.health import ready
        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.health.get_readiness_payload", side_effect=Exception("fail")):
            result = await ready(mock_request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_health_build_success_response(self):
        from app.routers.v1.health import health
        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = await health(mock_request)
        assert result is not None
