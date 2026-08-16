from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user, get_optional_user


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
    app.dependency_overrides[get_optional_user] = lambda: mock_user

    with (
        patch("app.routers.v1.documents_impl._require_db"),
        patch("app.routers.v1.documents_impl.DocumentService") as mock_ds,
        patch("app.routers.v1.documents_impl.virus_scanner.scan", new=AsyncMock(return_value={"clean": True})),
        patch("app.routers.v1.documents_impl.PipelineOrchestrator"),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline",
            return_value={"mode": "immediate"},
        ),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_edit_flow", return_value={"mode": "immediate"}
        ),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=AsyncMock()),
    ):
        with TestClient(app) as test_client:
            test_client.mock_ds = mock_ds
            yield test_client

    app.dependency_overrides = {}


class TestUploadDocument:
    def test_success(self, client, tmp_path):
        upload_dir = tmp_path / "uploads"
        import app.routers.v1.documents_impl as di

        original_dir = di.UPLOAD_DIR
        di.UPLOAD_DIR = str(upload_dir)

        client.mock_ds.create_document = AsyncMock(return_value=MagicMock())
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.docx", io.BytesIO(b"PK\x03\x04content"), "application/octet-stream")},
            data={"template": "ieee"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "PROCESSING"
        di.UPLOAD_DIR = original_dir

    def test_invalid_extension(self, client):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("virus.exe", io.BytesIO(b"data"), "application/octet-stream")},
            data={"template": "ieee"},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.text

    def test_empty_file(self, client):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("empty.docx", io.BytesIO(b""), "application/octet-stream")},
            data={"template": "ieee"},
        )
        assert response.status_code in (400, 422)

    def test_oversize_file(self, client):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            mock_s.MAX_FILE_SIZE = 10
            mock_s.DEFAULT_TEMPLATE = "ieee"
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("big.docx", io.BytesIO(b"x" * 100), "application/octet-stream")},
                data={"template": "ieee"},
            )
        assert response.status_code == 413
        assert b"too large" in response.content.lower() or b"exceeds" in response.content.lower()


class TestUploadChunked:
    def test_invalid_file_id(self, client):
        response = client.post(
            "/api/v1/documents/upload/chunked",
            data={
                "file_id": "../../etc/passwd",
                "chunk_index": 0,
                "total_chunks": 1,
                "template": "ieee",
            },
            files={"file": ("chunk.bin", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_chunk_exceeds_limit(self, client):
        response = client.post(
            "/api/v1/documents/upload/chunked",
            data={
                "file_id": "safe-id-123",
                "chunk_index": 0,
                "total_chunks": 1,
                "template": "ieee",
            },
            files={"file": ("chunk.bin", io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)), "application/octet-stream")},
        )
        assert response.status_code == 413

    def test_single_chunk_received(self, client, tmp_path):
        import app.routers.v1.documents_impl as di

        di.UPLOAD_DIR = str(tmp_path / "uploads")
        client.mock_ds.create_document = AsyncMock(return_value=MagicMock())

        response = client.post(
            "/api/v1/documents/upload/chunked",
            data={
                "file_id": "test-chunk-id",
                "chunk_index": 0,
                "total_chunks": 1,
                "template": "ieee",
            },
            files={"file": ("test.docx", io.BytesIO(b"PK\x03\x04fakecontent"), "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "complete"


class TestListDocuments:
    def test_success(self, client):
        client.mock_ds.list_documents = AsyncMock(
            return_value=[
                {
                    "id": "d1",
                    "filename": "test.docx",
                    "template": "ieee",
                    "status": "COMPLETED",
                    "progress": 100,
                    "current_stage": "EXPORT",
                    "error_message": None,
                    "created_at": "now",
                    "updated_at": "now",
                }
            ]
        )
        client.mock_ds.count_documents = AsyncMock(return_value=1)

        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        assert len(data["documents"]) == 1

    def test_with_filters(self, client):
        client.mock_ds.list_documents = AsyncMock(return_value=[])
        client.mock_ds.count_documents = AsyncMock(return_value=0)

        response = client.get("/api/v1/documents?status=COMPLETED&template=ieee&limit=10&offset=0")
        assert response.status_code == 200
        client.mock_ds.list_documents.assert_called_once()

    def test_db_unavailable(self, client):
        from app.exceptions import DatabaseUnavailableError

        client.mock_ds.list_documents = AsyncMock(side_effect=DatabaseUnavailableError("DB down"))
        client.mock_ds.count_documents = AsyncMock()

        response = client.get("/api/v1/documents")
        assert response.status_code == 503


class TestGetStatus:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "job-1",
                "status": "PROCESSING",
                "current_stage": "PARSING",
                "progress": 45,
                "error_message": None,
                "user_id": "user-123",
                "created_at": "now",
                "updated_at": "now",
            }
        )
        client.mock_ds.get_processing_statuses = AsyncMock(
            return_value=[
                {
                    "phase": "UPLOAD",
                    "status": "success",
                    "message": "done",
                    "progress_percentage": 100,
                    "updated_at": "now",
                },
            ]
        )
        client.mock_ds.get_document_result = AsyncMock(return_value=None)

        response = client.get("/api/v1/documents/job-1/status")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "PROCESSING"

    def test_not_found(self, client):
        client.mock_ds.get_document = AsyncMock(return_value=None)
        client.mock_ds.get_processing_statuses = AsyncMock(return_value=[])

        response = client.get("/api/v1/documents/missing/status")
        assert response.status_code == 404

    def test_not_authorized(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "job-1",
                "status": "PROCESSING",
                "user_id": "other-user",
            }
        )
        client.mock_ds.get_processing_statuses = AsyncMock(return_value=[])

        response = client.get("/api/v1/documents/job-1/status")
        assert response.status_code == 403


class TestGetSummary:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "status": "COMPLETED",
                "filename": "paper.docx",
                "template": "ieee",
                "created_at": "now",
                "output_path": "/tmp/doc.docx",
            }
        )
        client.mock_ds.get_document_result = AsyncMock(
            return_value={
                "validation_results": {"quality_summary": {"overall_score": 95}},
            }
        )

        response = client.get("/api/v1/documents/d1/summary")
        assert response.status_code == 200


class TestEditDocument:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "template": "ieee",
                "filename": "test.docx",
            }
        )

        response = client.post(
            "/api/v1/documents/d1/edit",
            json={"edited_structured_data": {"title": "New Title"}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "PROCESSING"

    def test_not_found(self, client):
        client.mock_ds.get_document = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/documents/missing/edit",
            json={"edited_structured_data": {"title": "x"}},
        )
        assert response.status_code == 404


class TestGetPreview:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "filename": "p.pdf",
                "template": "apa",
                "status": "COMPLETED",
                "created_at": "now",
            }
        )
        client.mock_ds.get_document_result = AsyncMock(
            return_value={
                "structured_data": {"blocks": [{"text": "Hello"}]},
                "validation_results": {"quality_summary": {"overall_score": 88}},
            }
        )

        response = client.get("/api/v1/documents/d1/preview")
        assert response.status_code == 200
        assert response.json()["data"]["structured_data"]["blocks"][0]["text"] == "Hello"


class TestGetComparisonData:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "status": "COMPLETED",
                "raw_text": "Original text.\nMore text.",
            }
        )
        client.mock_ds.get_document_result = AsyncMock(
            return_value={
                "structured_data": {
                    "blocks": [{"text": "Formatted text."}],
                },
            }
        )

        response = client.get("/api/v1/documents/d1/compare")
        assert response.status_code == 200
        assert "html_diff" in response.json()["data"]

    def test_not_ready(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "status": "PROCESSING",
            }
        )

        response = client.get("/api/v1/documents/d1/compare")
        assert response.status_code == 400


class TestDownload:
    def test_unsupported_format(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "status": "COMPLETED",
            }
        )

        response = client.get("/api/v1/documents/d1/download?format=svg")
        assert response.status_code == 400

    def test_not_ready(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "status": "PROCESSING",
            }
        )

        response = client.get("/api/v1/documents/d1/download?format=docx")
        assert response.status_code == 400


class TestDelete:
    def test_success(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "user-123",
                "filename": "test.docx",
                "output_path": None,
                "original_file_path": None,
            }
        )
        client.mock_ds.delete_document = AsyncMock()

        response = client.delete("/api/v1/documents/d1")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "deleted"

    def test_not_found(self, client):
        client.mock_ds.get_document = AsyncMock(return_value=None)

        response = client.delete("/api/v1/documents/missing")
        assert response.status_code == 404

    def test_not_authorized(self, client):
        client.mock_ds.get_document = AsyncMock(
            return_value={
                "id": "d1",
                "user_id": "other-user",
            }
        )

        response = client.delete("/api/v1/documents/d1")
        assert response.status_code == 403


class TestBatchUpload:
    def test_too_many_files(self, client):
        with patch("app.routers.v1.documents_impl.settings") as mock_s:
            mock_s.MAX_BATCH_FILES = 2
            response = client.post(
                "/api/v1/documents/batch-upload",
                data={"template": "ieee"},
                files=[
                    ("files", ("a.docx", io.BytesIO(b"data"), "application/octet-stream")),
                    ("files", ("b.docx", io.BytesIO(b"data"), "application/octet-stream")),
                    ("files", ("c.docx", io.BytesIO(b"data"), "application/octet-stream")),
                ],
            )
        assert response.status_code == 400

    def test_success(self, client):
        client.mock_ds.create_document = AsyncMock(return_value=MagicMock())
        response = client.post(
            "/api/v1/documents/batch-upload",
            data={"template": "ieee"},
            files=[
                ("files", ("a.docx", io.BytesIO(b"PK\x03\x04content1"), "application/octet-stream")),
                ("files", ("b.docx", io.BytesIO(b"PK\x03\x04content2"), "application/octet-stream")),
            ],
        )
        assert response.status_code == 200
        assert len(response.json()["data"]["jobs"]) == 2


class TestHelpers:
    def test_apply_rate_limit_headers(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult

        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=1000.0, retry_after=5.0)
        apply_rate_limit_headers(response, result)
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["Retry-After"] == "6"

    def test_apply_rate_limit_with_zero_retry(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult

        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=100, remaining=99, reset_at=2000.0, retry_after=0.0)
        apply_rate_limit_headers(response, result)
        assert response.headers["Retry-After"] == "1"
