# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    """Mock AI model pre-loading to speed up tests."""
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_parser,
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine") as mock_rag,
    ):
        # Setup parser mock
        parser_instance = MagicMock()
        mock_parser.return_value = parser_instance

        # Setup RAG mock
        rag_instance = MagicMock()
        mock_rag.return_value = rag_instance

        yield


@pytest.fixture
def client():
    """Setup TestClient with dependency overrides and mocked service."""
    # Delay imports to avoid collection-time issues
    from app.main import app
    from app.services.document_service import DocumentService
    from app.utils.dependencies import get_current_user, get_optional_user

    # We patch the class itself because router uses static methods
    mock_service = MagicMock(spec=DocumentService)

    # Mock Redis to avoid RateLimiter errors
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)

    # Setup a mock user
    mock_user = MagicMock()
    mock_user.id = "mock-user-123"

    # Dependencies inside app.main or routers
    app.dependency_overrides[get_optional_user] = lambda: mock_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Use patch(..., mock_service) so DocumentService IS the mock object
    with (
        patch("app.routers.v1.documents_impl.DocumentService", mock_service),
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.middleware.rate_limit.redis", mock_redis),
        TestClient(app) as c,
    ):
        c.mock_service = mock_service
        c.mock_user = mock_user
        yield c

    app.dependency_overrides = {}


def test_root_contract(client):
    """Simple test to verify collection and basic app connectivity."""
    response = client.get("/")
    assert response.status_code == 200
    assert "ScholarForm AI" in response.json()["message"]


@pytest.mark.contract
class TestEndpointContracts:
    """
    Contract tests for /api/v1 response envelopes.
    """

    def test_list_documents_contract(self, client):
        """Verify GET /api/v1/documents returns envelope + expected list payload."""
        # Router calls DocumentService.list_documents(...) [static method]
        client.mock_service.list_documents.return_value = [
            {
                "id": "doc-123",
                "filename": "test_document.docx",
                "template": "IEEE",
                "status": "COMPLETED",
                "progress": 100,
                "current_stage": "EXPORT",
                "created_at": "2024-02-23T00:00:00Z",
                "updated_at": "2024-02-23T00:05:00Z",
                "export_formats": ["docx", "pdf"],
            }
        ]
        client.mock_service.count_documents.return_value = 1

        response = client.get("/api/v1/documents")
        assert response.status_code == 200

        payload = response.json()
        assert payload["error"] is None
        assert payload["request_id"]
        assert payload["timestamp"]
        assert payload["data"]["total"] == 1
        assert payload["data"]["documents"][0]["filename"] == "test_document.docx"

    def test_get_status_contract(self, client):
        """Verify GET /api/v1/documents/{jobId}/status returns envelope + status payload."""
        job_id = "job-abc-123"
        client.mock_service.get_document.return_value = {
            "id": job_id,
            "status": "PROCESSING",
            "current_stage": "PARSING",
            "progress": 45,
            "error_message": None,
            "user_id": client.mock_user.id,
            "created_at": "2024-02-23T10:00:00+00:00",
            "updated_at": "2024-02-23T10:00:00+00:00",
        }
        client.mock_service.get_processing_statuses.return_value = [
            {
                "phase": "UPLOAD",
                "status": "success",
                "message": "File received",
                "progress": 100,
                "updated_at": "2024-02-23T09:55:00+00:00",
            }
        ]

        response = client.get(f"/api/v1/documents/{job_id}/status")
        assert response.status_code == 200

        payload = response.json()
        assert payload["error"] is None
        assert payload["data"]["job_id"] == job_id
        assert payload["data"]["status"] == "PROCESSING"

    def test_get_preview_contract(self, client):
        """Verify GET /api/v1/documents/{jobId}/preview returns envelope + preview payload."""
        job_id = "job-preview"
        client.mock_service.get_document.return_value = {
            "id": job_id,
            "filename": "test.pdf",
            "template": "APA",
            "status": "COMPLETED",
            "created_at": "2024-02-23T12:00:00+00:00",
            "user_id": client.mock_user.id,
        }
        client.mock_service.get_document_result.return_value = {
            "structured_data": {"blocks": [{"text": "Hello"}]},
            "validation_results": {"errors": [], "warnings": ["Missing DOI"]},
        }

        response = client.get(f"/api/v1/documents/{job_id}/preview")
        assert response.status_code == 200

        payload = response.json()
        assert payload["error"] is None
        assert payload["data"]["metadata"]["filename"] == "test.pdf"

    def test_upload_invalid_extension_contract(self, client):
        """Verify 400 error envelope for unsupported file extensions."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("malicious.js", b"console.log('hi')", "text/javascript")},
            data={"template": "IEEE"},
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["data"] is None
        assert payload["error"]["code"] == "INVALID_UPLOAD_REQUEST"
        assert "Invalid file type" in payload["error"]["message"]

    def test_get_preview_not_found_contract(self, client):
        """Verify 404 error envelope for missing documents."""
        client.mock_service.get_document.return_value = None
        response = client.get("/api/v1/documents/non-existent-id/preview")
        assert response.status_code == 404
        payload = response.json()
        assert payload["data"] is None
        assert payload["error"]["code"] == "DOCUMENT_NOT_FOUND"
        assert payload["error"]["message"] == "Document job not found"
