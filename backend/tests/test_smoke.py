# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_parser,
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine") as mock_rag,
    ):
        mock_parser.return_value = MagicMock()
        mock_rag.return_value = MagicMock()
        yield


@pytest.fixture
def client():
    from app.main import app
    from app.services.document_service import DocumentService
    from app.utils.dependencies import get_current_user, get_optional_user

    mock_service = MagicMock(spec=DocumentService)
    mock_service.list_documents.return_value = []
    mock_service.count_documents.return_value = 0

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True

    mock_user = MagicMock()
    mock_user.id = "mock-user-123"

    app.dependency_overrides[get_optional_user] = lambda: mock_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with (
        patch("app.routers.v1.documents_impl.DocumentService", mock_service),
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.middleware.rate_limit.redis", mock_redis),
    ):
        with TestClient(app) as test_client:
            test_client.mock_service = mock_service
            test_client.mock_user = mock_user
            yield test_client

    app.dependency_overrides = {}


@pytest.fixture
def upload_docx_fixture() -> Path:
    return Path("app/templates/ieee/template.docx")


@pytest.mark.contract
class TestBackendSmokeContracts:
    def test_templates_v1_contract_smoke(self, client: TestClient):
        response = client.get("/api/v1/templates")
        assert response.status_code == 200

        payload = response.json()
        assert "data" in payload
        templates = payload["data"]["templates"]
        assert len(templates) == 17

        expected_ids = {
            "acm",
            "apa",
            "chicago",
            "elsevier",
            "harvard",
            "ieee",
            "mla",
            "modern_blue",
            "modern_gold",
            "modern_red",
            "nature",
            "none",
            "numeric",
            "portfolio",
            "resume",
            "springer",
            "vancouver",
        }
        assert {template["id"] for template in templates} == expected_ids
        for template in templates:
            assert set(template.keys()) == {"id", "name", "description", "source"}
            assert all(isinstance(template[field], str) for field in template)

    def test_upload_v1_contract_smoke(self, client: TestClient, upload_docx_fixture: Path):
        client.mock_service.create_document.return_value = {"id": "job-123"}
        file_bytes = upload_docx_fixture.read_bytes()

        with (
            patch(
                "app.routers.v1.documents_impl.virus_scanner.scan",
                new_callable=AsyncMock,
                return_value={"clean": True, "engine": "clamav", "result": "clean"},
            ) as mock_scan,
            patch(
                "app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline",
                return_value={"mode": "standard"},
            ),
            patch("app.routers.v1.documents_impl.audit_log_service.log", new_callable=AsyncMock),
        ):
            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "fixture-upload.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"template": "ieee"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["status"] == "PROCESSING"
        assert payload["data"]["job_id"]
        mock_scan.assert_awaited_once()

    def test_health_v1_contract_smoke(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        payload = response.json()
        assert "request_id" in payload
        assert "timestamp" in payload
        assert payload["data"]["status"] == "alive"

    def test_generator_session_create_get_update_smoke(self, client: TestClient):
        session_id = "sess-123"
        session_record = {
            "id": session_id,
            "status": "processing",
            "session_type": "multi_doc",
            "config_json": {"template": "ieee"},
            "outline_json": None,
            "created_at": "2026-03-18T10:00:00+00:00",
            "updated_at": "2026-03-18T10:00:01+00:00",
            "user_id": client.mock_user.id,
        }

        with (
            patch("app.routers.v1.generator._dispatch_agent_task"),
            patch(
                "app.routers.v1.generator._session_service.create_session",
                new_callable=AsyncMock,
                return_value=session_id,
            ),
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value=session_record,
            ),
            patch(
                "app.routers.v1.generator._session_service.get_latest_document",
                new_callable=AsyncMock,
                return_value={"docx_path": "uploads/sess-123.docx"},
            ),
            patch("app.routers.v1.generator._session_service.add_message", new_callable=AsyncMock),
            patch("app.routers.v1.generator.audit_log_service.log", new_callable=AsyncMock),
            patch("app.routers.v1.generator.abuse_detector.record_generation_request", new_callable=AsyncMock),
            patch("app.routers.v1.generator.abuse_detector.record_llm_call", new_callable=AsyncMock),
            patch(
                "app.routers.v1.generator._vector_store.query",
                return_value=[{"source_doc": "paper-1", "section": "Intro", "text": "Source context"}],
            ),
            patch(
                "app.routers.v1.generator.generate_with_fallback",
                return_value={"text": "Updated draft response"},
            ),
            patch("app.tasks.celery_tasks.process_agent_pipeline_task.delay"),
        ):
            create_response = client.post(
                "/api/v1/generator/sessions",
                json={
                    "session_type": "agent",
                    "prompt": "Draft an abstract about AI formatting",
                    "template": "ieee",
                },
            )
            assert create_response.status_code == 202
            create_payload = create_response.json()
            assert create_payload["data"] == {"session_id": session_id, "status": "started"}
            assert create_payload["error"] is None
            assert create_payload["request_id"]
            assert create_payload["timestamp"]

            get_response = client.get(f"/api/v1/generator/sessions/{session_id}")
            assert get_response.status_code == 200
            get_payload = get_response.json()
            assert get_payload["data"]["id"] == session_id
            assert get_payload["error"] is None

            update_response = client.post(
                f"/api/v1/generator/sessions/{session_id}/messages",
                json={"content": "Rewrite the introduction with stronger novelty framing."},
            )
            assert update_response.status_code == 200
            update_payload = update_response.json()
            assert update_payload["data"]["role"] == "assistant"
            assert update_payload["data"]["content"] == "Updated draft response"

    def test_preview_live_http_smoke(self, client: TestClient):
        with patch(
            "app.routers.preview.preview_renderer.render_preview",
            return_value={"html": "<p>Preview</p>", "latency_ms": 8.7, "warnings": []},
        ) as mock_preview:
            response = client.post(
                "/api/v1/preview/live",
                json={"content": "Sample content", "templateId": "ieee"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["html"] == "<p>Preview</p>"
        assert isinstance(payload["latencyMs"], float)
        assert payload["warnings"] == []
        mock_preview.assert_called_once()

    def test_legacy_routes_removed_smoke(self, client: TestClient):
        templates_response = client.get("/api/templates")
        assert templates_response.status_code == 404

        documents_response = client.get("/api/documents")
        assert documents_response.status_code == 404

    def test_signed_download_v1_smoke(self, client: TestClient, tmp_path):
        job_id = "job-smoke-download-1"
        output_path = tmp_path / "download.docx"
        output_path.write_bytes(b"PK\x03\x04docx-smoke")

        client.mock_service.get_document.return_value = {
            "id": job_id,
            "filename": "download.docx",
            "user_id": client.mock_user.id,
            "status": "COMPLETED",
            "output_path": str(output_path),
            "output_hash": None,
        }
        client.mock_service.generate_signed_download_url.return_value = {
            "url": f"http://testserver/api/v1/documents/{job_id}/download?format=docx&token=fake-token&expires=1234567890",
            "expires": 1234567890,
        }
        client.mock_service.verify_signed_download.return_value = True

        with patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "test-secret"):
            response = client.get(f"/api/v1/documents/{job_id}/download?format=docx")
            assert response.status_code == 200
            payload = response.json()
            assert payload["data"]["expires"] == 1234567890
            assert "token=fake-token" in payload["data"]["url"]

            signed_response = client.get(
                f"/api/v1/documents/{job_id}/download?format=docx&token=fake-token&expires=1234567890"
            )

        assert signed_response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in signed_response.headers.get(
            "content-type", ""
        )
        assert signed_response.content.startswith(b"PK")

