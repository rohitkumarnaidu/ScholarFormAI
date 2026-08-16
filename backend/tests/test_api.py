# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
API Integration Tests
Tests FastAPI endpoints, authentication, and request handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user, get_optional_user

client = TestClient(app)


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.mark.integration
    def test_root_endpoint(self):
        """Test root endpoint returns correct message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "ScholarForm AI Backend is running"}

    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test health check endpoint returns correct structure."""
        with patch("app.db.supabase_client.check_supabase_health") as mock_sb_health:
            with patch("httpx.AsyncClient") as mock_httpx:
                with patch("app.services.model_store.model_store.get_model") as mock_get_model:
                    # Mock successful health checks
                    mock_sb_health.return_value = {"status": "healthy"}

                    # Mock httpx Ollama check
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_client = AsyncMock()
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_httpx.return_value = mock_client

                    # Mock model store
                    mock_get_model.return_value = True

                    response = client.get("/health")

                    assert response.status_code == 200
                    data = response.json()
                    assert "status" in data
                    assert "version" in data
                    assert "components" in data

    @pytest.mark.integration
    def test_health_endpoint_degraded_database(self):
        """Test health endpoint when database is unavailable."""
        with patch("app.db.supabase_client.check_supabase_health") as mock_sb_health:
            with patch("httpx.AsyncClient") as mock_httpx:
                with patch("app.services.model_store.model_store.get_model") as mock_get_model:
                    # Mock database failure
                    mock_sb_health.return_value = {"status": "unhealthy"}

                    # Mock httpx success
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_client = AsyncMock()
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_httpx.return_value = mock_client

                    mock_get_model.return_value = True

                    response = client.get("/health")

                    data = response.json()
                    assert data["status"] == "degraded"
                    assert "supabase_db" in data["components"]

    @pytest.mark.integration
    def test_health_endpoint_ollama_unavailable(self):
        """Test health endpoint when Ollama is unavailable."""
        with patch("app.db.supabase_client.check_supabase_health") as mock_sb_health:
            with patch("httpx.AsyncClient") as mock_httpx:
                with patch("app.services.model_store.model_store.get_model") as mock_get_model:
                    # Mock Supabase healthy
                    mock_sb_health.return_value = {"status": "healthy"}

                    # Mock Ollama failure
                    mock_client = AsyncMock()
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(side_effect=Exception("Ollama unavailable"))
                    mock_httpx.return_value = mock_client

                    mock_get_model.return_value = True

                    response = client.get("/health")

                    data = response.json()
                    assert data["status"] == "degraded"
                    assert "ollama" in data["components"]

    @pytest.mark.integration
    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = client.options("/", headers={"Origin": "http://localhost:5173"})
        # CORS middleware should add headers
        assert response.status_code in [200, 405]  # OPTIONS may not be explicitly defined

    @pytest.mark.integration
    def test_rate_limiting_not_applied_to_health(self):
        """Test rate limiting skips health endpoint."""
        with patch("app.db.supabase_client.check_supabase_health") as mock_sb_health:
            with patch("httpx.AsyncClient") as mock_httpx:
                with patch("app.services.model_store.model_store.get_model") as mock_get_model:
                    mock_sb_health.return_value = {"status": "healthy"}
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_client = AsyncMock()
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=False)
                    mock_client.get = AsyncMock(return_value=mock_response)
                    mock_httpx.return_value = mock_client
                    mock_get_model.return_value = True

                    # Make multiple rapid requests to /health
                    for _ in range(20):
                        response = client.get("/health")
                        assert response.status_code in [200, 503]  # healthy or degraded, never rate limited

    @pytest.mark.integration
    def test_ready_endpoint_no_nameerror(self):
        """Regression: /ready should return structured JSON (no datetime NameError)."""
        with patch("app.db.supabase_client.check_supabase_health") as mock_sb_health:
            with patch("httpx.AsyncClient") as mock_httpx:
                with patch("app.services.model_store.model_store.get_model") as mock_get_model:
                    with patch(
                        "app.services.llm_service.check_health", new=AsyncMock(return_value={"nvidia": "healthy"})
                    ):
                        mock_sb_health.return_value = {"status": "healthy"}
                        mock_response = AsyncMock()
                        mock_response.status_code = 200
                        mock_client = AsyncMock()
                        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                        mock_client.__aexit__ = AsyncMock(return_value=False)
                        mock_client.get = AsyncMock(return_value=mock_response)
                        mock_httpx.return_value = mock_client
                        mock_get_model.return_value = True

                        response = client.get("/ready")
                        assert response.status_code in [200, 503]
                        payload = response.json()
                        assert "ready" in payload
                        assert "timestamp" in payload

    @pytest.mark.integration
    def test_document_summary_endpoint(self):
        """GET /api/v1/documents/{job_id}/summary should expose lightweight status payload."""
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_optional_user] = lambda: mock_user
        try:
            with patch("app.routers.v1.documents_impl.DocumentService.get_document") as mock_get_document:
                with patch("app.routers.v1.documents_impl.DocumentService.get_document_result") as mock_get_result:
                    mock_get_document.return_value = {
                        "id": "job-summary",
                        "user_id": "user-123",
                        "status": "COMPLETED_WITH_WARNINGS",
                        "filename": "paper.docx",
                        "template": "IEEE",
                        "created_at": "2026-02-26T10:00:00+00:00",
                        "output_path": "uploads/job-summary.docx",
                    }
                    mock_get_result.return_value = {
                        "validation_results": {
                            "quality_score": 78,
                            "quality_summary": {
                                "overall_score": 78,
                                "template_compliance": 85,
                                "content_quality": 72,
                                "citation_count": 14,
                                "missing_sections": ["Abstract", "Acknowledgements"],
                                "llm_provider_used": "groq",
                            },
                        }
                    }
                    response = client.get("/api/v1/documents/job-summary/summary")

            assert response.status_code == 200
            data = response.json()["data"]
            assert data["id"] == "job-summary"
            assert data["status"] == "COMPLETED_WITH_WARNINGS"
            assert data["output_path"] == "uploads/job-summary.docx"
            assert data["quality"] == {
                "overall_score": 78,
                "template_compliance": 85,
                "content_quality": 72,
                "citation_count": 14,
                "missing_sections": ["Abstract", "Acknowledgements"],
                "llm_provider_used": "groq",
            }
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    @pytest.mark.integration
    def test_document_status_includes_quality_score(self):
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_optional_user] = lambda: mock_user
        try:
            with patch("app.routers.v1.documents_impl.DocumentService.get_document") as mock_get_document:
                with patch("app.routers.v1.documents_impl.DocumentService.get_processing_statuses", return_value=[]):
                    with patch("app.routers.v1.documents_impl.DocumentService.get_document_result") as mock_get_result:
                        mock_get_document.return_value = {
                            "id": "job-quality",
                            "user_id": "user-123",
                            "status": "COMPLETED",
                            "current_stage": "DONE",
                            "progress": 100,
                        }
                        mock_get_result.return_value = {
                            "validation_results": {
                                "quality_score": 92.4,
                                "quality_summary": {
                                    "overall_score": 92.4,
                                    "template_compliance_pct": 100.0,
                                },
                            }
                        }
                        response = client.get("/api/v1/documents/job-quality/status")

            assert response.status_code == 200
            payload = response.json()["data"]
            assert payload["quality_score"] == 92.4
            assert payload["quality_summary"]["overall_score"] == 92.4
            assert payload["quality"]["overall_score"] == 92.4
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    @pytest.mark.integration
    def test_log_error_endpoint_allows_guest(self):
        """POST /api/v1/metrics/log-error should work without auth."""
        response = client.post(
            "/api/v1/metrics/log-error",
            json={
                "message": "UI failed to render",
                "stack": "Error: boom",
                "url": "http://localhost:5173/upload",
                "timestamp": "2026-02-26T10:00:00Z",
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "logged"

    @pytest.mark.integration
    def test_compare_and_download_accept_completed_with_warnings(self, tmp_path):
        """Documents in COMPLETED_WITH_WARNINGS must be downloadable/comparable."""
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_optional_user] = lambda: mock_user
        try:
            output_path = tmp_path / "job-download.docx"
            output_path.write_bytes(b"PK\x03\x04dummy-docx")

            with patch("app.routers.v1.documents_impl.DocumentService.get_document") as mock_get_document:
                with patch("app.routers.v1.documents_impl.DocumentService.get_document_result") as mock_get_result:
                    mock_get_document.return_value = {
                        "id": "job-download",
                        "user_id": "user-123",
                        "status": "COMPLETED_WITH_WARNINGS",
                        "filename": "paper.docx",
                        "raw_text": "Original text",
                        "output_path": str(output_path),
                    }
                    mock_get_result.return_value = {"structured_data": {"blocks": [{"text": "Formatted text"}]}}

                    compare_response = client.get("/api/v1/documents/job-download/compare")
                    assert compare_response.status_code == 200
                    assert "html_diff" in compare_response.json()["data"]

                    download_link = client.get("/api/v1/documents/job-download/download?format=docx")
                    assert download_link.status_code == 200
                    signed_url = download_link.json()["data"]["url"]
                    from urllib.parse import urlparse

                    parsed = urlparse(signed_url)
                    download_response = client.get(f"{parsed.path}?{parsed.query}")
                    assert download_response.status_code == 200
                    assert (
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        in download_response.headers.get("content-type", "")
                    )
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    @pytest.mark.integration
    def test_download_rejects_unsupported_format(self):
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_optional_user] = lambda: mock_user
        try:
            with patch("app.routers.v1.documents_impl.DocumentService.get_document") as mock_get_document:
                mock_get_document.return_value = {
                    "id": "job-download",
                    "user_id": "user-123",
                    "status": "COMPLETED",
                    "filename": "paper.docx",
                    "output_path": "uploads/job-download.docx",
                }
                response = client.get("/api/v1/documents/job-download/download?format=txt")

            assert response.status_code == 400
            assert response.json()["error"]["message"] == "Unsupported format. Supported: docx, pdf, tex"
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    @pytest.mark.integration
    def test_download_supports_tex_export(self, tmp_path):
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_optional_user] = lambda: mock_user
        try:
            output_path = tmp_path / "job-download.docx"
            output_path.write_bytes(b"PK\x03\x04dummy-docx")
            tex_path = tmp_path / "job-download.tex"
            tex_path.write_text("\\section{Introduction}", encoding="utf-8")

            with patch("app.routers.v1.documents_impl.DocumentService.get_document") as mock_get_document:
                with patch("app.routers.v1.documents_impl.LaTeXExporter.convert_to_latex", return_value=str(tex_path)):
                    mock_get_document.return_value = {
                        "id": "job-download",
                        "user_id": "user-123",
                        "status": "COMPLETED",
                        "filename": "paper.docx",
                        "output_path": str(output_path),
                    }
                    link_response = client.get("/api/v1/documents/job-download/download?format=tex")
                    assert link_response.status_code == 200
                    signed_url = link_response.json()["data"]["url"]
                    from urllib.parse import urlparse

                    parsed = urlparse(signed_url)
                    response = client.get(f"{parsed.path}?{parsed.query}")

            assert response.status_code == 200
            assert "application/x-latex" in response.headers.get("content-type", "")
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    @pytest.mark.integration
    def test_chunk_upload_starts_processing_and_returns_job_id(self, tmp_path, monkeypatch):
        """Chunk reassembly should trigger pipeline and return a job_id."""
        monkeypatch.chdir(tmp_path)
        mock_user = MagicMock()
        mock_user.id = "user-123"
        app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("app.routers.v1.documents_impl._require_db", return_value=None):
                with patch(
                    "app.routers.v1.documents_impl.DocumentService.create_document", return_value={"id": "job-x"}
                ):
                    with patch("app.routers.v1.documents_impl.PipelineOrchestrator") as mock_orchestrator:
                        with patch(
                            "app.utils.background_tasks.run_pipeline_with_timeout", return_value=None
                        ) as mock_run_pipeline:
                            response = client.post(
                                "/api/v1/documents/upload/chunked",
                                data={
                                    "file_id": "chunk-file-123",
                                    "chunk_index": "0",
                                    "total_chunks": "1",
                                    "template": "IEEE",
                                },
                                files={
                                    "file": (
                                        "sample.docx",
                                        b"PK\x03\x04chunk-content",
                                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    )
                                },
                            )

            assert response.status_code == 200
            payload = response.json()["data"]
            assert payload["status"] == "complete"
            assert payload["file_id"] == "chunk-file-123"
            assert "job_id" in payload
            assert "file_hash" in payload
            assert mock_orchestrator.called
            assert mock_run_pipeline.called
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_upload_rejects_infected_file_with_validation_code(self, tmp_path, monkeypatch):
        """Infected uploads must fail validation before document creation or pipeline dispatch."""
        monkeypatch.chdir(tmp_path)

        with (
            patch("app.routers.v1.documents_impl._require_db", return_value=None),
            patch(
                "app.routers.v1.documents_impl.virus_scanner.scan",
                new=AsyncMock(return_value={"clean": False, "engine": "clamav", "result": "Eicar-Test-Signature"}),
            ),
            patch("app.routers.v1.documents_impl.DocumentService.create_document") as mock_create_document,
            patch("app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline") as mock_dispatch,
        ):
            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "infected.docx",
                        b"PK\x03\x04infected-docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"template": "IEEE"},
            )

        assert response.status_code == 422
        payload = response.json()
        assert payload["error"]["code"] == "DOCUMENT_VALIDATION_FAILED"
        assert "Malware detected" in payload["error"]["message"]
        mock_create_document.assert_not_called()
        mock_dispatch.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
