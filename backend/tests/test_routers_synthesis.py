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
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_session_svc = MagicMock()
    mock_session_svc.create_session = AsyncMock(return_value="sess-1")
    mock_session_svc.get_session = AsyncMock()
    mock_session_svc.update_session = AsyncMock()
    mock_session_svc.add_message = AsyncMock()
    mock_session_svc.get_latest_document = AsyncMock(return_value=None)

    mock_vector_store = MagicMock()
    mock_vector_store.query = MagicMock(return_value=[])

    with (
        patch("app.routers.v1.synthesis._session_service", mock_session_svc),
        patch("app.routers.v1.synthesis._vector_store", mock_vector_store),
        patch("app.routers.v1.synthesis._get_synthesizer"),
        patch("app.routers.v1.synthesis.enhancement_manager.dispatch_synthesis_pipeline", return_value={"mode": "immediate"}),
        patch("app.routers.v1.synthesis._pubsub.publish", new=AsyncMock()),
    ):
        with TestClient(app) as test_client:
            test_client.mock_session_svc = mock_session_svc
            test_client.mock_vector_store = mock_vector_store
            yield test_client

    app.dependency_overrides = {}


class TestCreateSession:
    def test_invalid_session_type(self, client):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "single_doc"},
            files=[("files", ("a.docx", b"content", "application/octet-stream"))],
        )
        assert response.status_code == 422

    def test_too_few_files(self, client):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "multi_doc"},
            files=[("files", ("a.docx", b"content", "application/octet-stream"))],
        )
        assert response.status_code == 422

    def test_unsupported_extension(self, client):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "multi_doc"},
            files=[
                ("files", ("a.docx", b"PK\x03\x04content", "application/octet-stream")),
                ("files", ("b.exe", b"binary", "application/octet-stream")),
            ],
        )
        assert response.status_code == 400

    def test_file_too_large(self, client):
        with patch("app.routers.v1.synthesis.settings") as mock_s:
            mock_s.MAX_FILE_SIZE = 10
            mock_s.DEFAULT_TEMPLATE = "ieee"
            response = client.post(
                "/api/v1/synthesis/sessions",
                data={"session_type": "multi_doc", "template": "ieee"},
                files=[
                    ("files", ("a.docx", b"x" * 100, "application/octet-stream")),
                    ("files", ("b.docx", b"y" * 50, "application/octet-stream")),
                ],
            )
        assert response.status_code == 413

    def test_success(self, client):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "multi_doc", "template": "ieee"},
            files=[
                ("files", ("a.docx", b"PK\x03\x04content_a", "application/octet-stream")),
                ("files", ("b.docx", b"PK\x03\x04content_b", "application/octet-stream")),
            ],
        )
        assert response.status_code == 202
        data = response.json()["data"]
        assert data["session_id"] == "sess-1"
        assert data["status"] == "started"


class TestGetSession:
    def test_not_found(self, client):
        client.mock_session_svc.get_session.return_value = None
        response = client.get("/api/v1/synthesis/sessions/nonexistent")
        assert response.status_code == 404

    def test_access_denied(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "other-user",
        }
        response = client.get("/api/v1/synthesis/sessions/sess-1")
        assert response.status_code == 403

    def test_success(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "user-123",
            "status": "processing", "session_type": "multi_doc",
            "config_json": {"template": "ieee"},
            "outline_json": None,
            "created_at": "now", "updated_at": "now",
        }
        response = client.get("/api/v1/synthesis/sessions/sess-1")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == "sess-1"


class TestSessionEvents:
    def test_not_found(self, client):
        client.mock_session_svc.get_session.return_value = None
        response = client.get("/api/v1/synthesis/sessions/nonexistent/events")
        assert response.status_code == 404

    def test_access_denied(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "other-user",
        }
        response = client.get("/api/v1/synthesis/sessions/sess-1/events")
        assert response.status_code == 403

    def test_connected_event(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "user-123",
        }
        with patch("app.routers.v1.synthesis._pubsub.subscribe") as mock_sub:
            mock_sub.return_value = _async_iter([])
            response = client.get(
                "/api/v1/synthesis/sessions/sess-1/events",
                headers={"Accept": "text/event-stream"},
            )
        assert response.status_code == 200


class TestSessionMessages:
    def test_not_found(self, client):
        client.mock_session_svc.get_session.return_value = None
        response = client.post(
            "/api/v1/synthesis/sessions/nonexistent/messages",
            json={"content": "Hello", "session_type": "chat"},
        )
        assert response.status_code == 404

    def test_access_denied(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "other-user",
        }
        response = client.post(
            "/api/v1/synthesis/sessions/sess-1/messages",
            json={"content": "Hello", "session_type": "chat"},
        )
        assert response.status_code == 403

    def test_empty_message(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "user-123",
        }
        response = client.post(
            "/api/v1/synthesis/sessions/sess-1/messages",
            json={"content": "", "session_type": "chat"},
        )
        assert response.status_code == 422

    def test_success(self, client):
        client.mock_session_svc.get_session.return_value = {
            "id": "sess-1", "user_id": "user-123",
        }
        client.mock_vector_store.query.return_value = [
            {"source_doc": "a.pdf", "section": "intro", "text": "Some context"},
        ]
        with patch(
            "app.routers.v1.synthesis.generate_with_fallback",
            return_value={"text": "Here is the answer."},
        ):
            response = client.post(
                "/api/v1/synthesis/sessions/sess-1/messages",
                json={"content": "Summarize this", "session_type": "chat"},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["role"] == "assistant"
        assert data["content"] == "Here is the answer."


class TestHelpers:
    def test_parse_config_valid(self):
        from app.routers.v1.synthesis import _parse_config
        assert _parse_config('{"key": "val"}') == {"key": "val"}

    def test_parse_config_empty(self):
        from app.routers.v1.synthesis import _parse_config
        assert _parse_config("") == {}

    def test_parse_config_invalid(self):
        from app.routers.v1.synthesis import _parse_config
        with pytest.raises(Exception):
            _parse_config("{bad json}")

    def test_assert_session_owner_match(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": "u1"}
        user = MagicMock()
        user.id = "u1"
        _assert_session_owner(session, user)

    def test_assert_session_owner_mismatch(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": "other"}
        user = MagicMock()
        user.id = "u1"
        with pytest.raises(Exception):
            _assert_session_owner(session, user)

    def test_get_orchestrator_lazy_init(self):
        import app.routers.v1.synthesis as syn
        from app.routers.v1.synthesis import _get_orchestrator
        syn._orchestrator = None
        orch = _get_orchestrator()
        assert orch is not None

    def test_get_synthesizer_lazy_init(self):
        import app.routers.v1.synthesis as syn
        from app.routers.v1.synthesis import _get_synthesizer
        syn._orchestrator = None
        syn._synthesizer = None
        with patch("app.routers.v1.synthesis.MultiDocSynthesizer") as mock_synth_cls:
            mock_synth_cls.return_value = MagicMock()
            synth = _get_synthesizer()
            assert synth is not None


def _async_iter(items):
    async def gen():
        for item in items:
            yield item
    return gen()
