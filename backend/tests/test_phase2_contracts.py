# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Phase 2: Contract & Smoke Validation — Comprehensive contract tests.

Exit criterion: Every major API endpoint returns expected envelope + schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.user import User
from app.utils.dependencies import get_current_user, get_optional_user

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_heavy_services():
    """Mock all external/AI services to avoid real network calls during smoke tests."""
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
        patch("app.services.generator_session_service.get_supabase_client", return_value=MagicMock()),
        patch("app.db.supabase_client.get_supabase_client", return_value=AsyncMock()),
        patch("app.services.llm_service.generate_with_fallback", new=AsyncMock(return_value="Mocked LLM response")),
        patch("app.middleware.rate_limit.redis", MagicMock()),
        patch(
            "app.services.preview_renderer.preview_renderer.render_preview",
            return_value={"html": "<p>Mocked</p>", "latency_ms": 5, "warnings": []},
        ),
    ):
        yield


@pytest.fixture
def client():
    user = User(id="user-123", email="user@example.com", role="authenticated")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    with patch("app.main._probe_grobid_startup", new=AsyncMock(return_value=False)), TestClient(app) as test_client:
        test_client.mock_user = user
        yield test_client

    app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def assert_envelope(payload: dict, expect_success: bool = True):
    assert "data" in payload
    assert "error" in payload
    assert "request_id" in payload
    assert "timestamp" in payload
    if expect_success:
        assert payload["error"] is None
    else:
        assert payload["data"] is None
        assert payload["error"]["code"]
        assert payload["error"]["message"]


def assert_template_schema(tpl: dict):
    assert "id" in tpl
    assert "name" in tpl
    assert "description" in tpl
    assert "source" in tpl
    assert tpl["source"] == "built_in"
    assert isinstance(tpl["id"], str)
    assert tpl["id"]
    assert isinstance(tpl["name"], str)
    assert tpl["name"]
    assert isinstance(tpl["description"], str)


# ===================================================================
# 2.3 — Health endpoints
# ===================================================================


class TestHealthSmoke:
    def test_root_returns_running(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["message"] == "ScholarForm AI Backend is running"

    def test_root_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_ready_returns_200_or_503(self, client):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)

    def test_v1_health_success(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert_envelope(payload)
        assert payload["data"] == {"status": "alive"}

    def test_v1_health_live(self, client):
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["data"] == {"status": "alive"}

    def test_v1_health_ready(self, client):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)

    def test_v1_health_echoes_request_id(self, client):
        resp = client.get("/api/v1/health", headers={"X-Request-Id": "smoke-001"})
        assert resp.status_code == 200
        assert resp.headers["X-Request-Id"] == "smoke-001"
        assert resp.json()["request_id"] == "smoke-001"

    def test_v1_health_admin_requires_auth(self, client):
        app.dependency_overrides.clear()
        with TestClient(app) as anon:
            resp = anon.get("/api/v1/health/admin")
            assert resp.status_code in (401, 403)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )
        app.dependency_overrides[get_optional_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )


# ===================================================================
# 2.1 — Templates endpoint
# ===================================================================


class TestTemplatesSmoke:
    def test_get_template_list_returns_envelope(self, client):
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 200
        payload = resp.json()
        assert_envelope(payload)
        templates = payload["data"]["templates"]
        assert isinstance(templates, list)
        assert len(templates) >= 1

    def test_every_template_has_valid_schema(self, client):
        resp = client.get("/api/v1/templates")
        for tpl in resp.json()["data"]["templates"]:
            assert_template_schema(tpl)

    def test_ieee_template_is_present(self, client):
        ids = {t["id"] for t in client.get("/api/v1/templates").json()["data"]["templates"]}
        assert "ieee" in ids

    def test_ieee_template_has_correct_display_name(self, client):
        resp = client.get("/api/v1/templates")
        templates = resp.json()["data"]["templates"]
        ieee = next(t for t in templates if t["id"] == "ieee")
        assert ieee["name"] == "IEEE"

    def test_csl_search_requires_query(self, client):
        resp = client.get("/api/v1/templates/csl/search")
        assert resp.status_code == 422

    def test_csl_search_with_query_returns_envelope(self, client):
        with patch(
            "app.routers.v1.templates.search_styles", new=AsyncMock(return_value=[{"id": "ieee", "title": "IEEE"}])
        ):
            resp = client.get("/api/v1/templates/csl/search", params={"q": "ieee"})
            assert resp.status_code == 200
            assert_envelope(resp.json())
            assert resp.json()["data"]["query"] == "ieee"

    def test_csl_fetch_requires_slug(self, client):
        resp = client.get("/api/v1/templates/csl/fetch")
        assert resp.status_code == 422

    def test_custom_templates_require_auth(self, client):
        app.dependency_overrides.clear()
        with TestClient(app) as anon:
            resp = anon.get("/api/v1/templates/custom")
            assert resp.status_code in (401, 403)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )
        app.dependency_overrides[get_optional_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )

    def test_custom_templates_list_returns_envelope(self, client):
        with patch("app.routers.v1.templates._require_db", return_value=MagicMock()) as mock_db:
            mock_db.return_value.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
                data=[]
            )
            resp = client.get("/api/v1/templates/custom")
            assert resp.status_code == 200
            assert_envelope(resp.json())

    def test_create_custom_template_requires_name(self, client):
        with patch("app.routers.v1.templates._require_db", return_value=MagicMock()):
            resp = client.post("/api/v1/templates/custom", json={})
            assert resp.status_code == 422


# ===================================================================
# 2.2 — Document upload endpoint
# ===================================================================


class TestDocumentUploadSmoke:
    def test_upload_requires_file(self, client):
        resp = client.post("/api/v1/documents/upload")
        assert resp.status_code in (422, 400)

    def test_upload_rejects_invalid_extension(self, client):
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("malicious.js", b"console.log('hi')", "text/javascript")},
            data={"template": "IEEE"},
        )
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["data"] is None
        assert payload["error"]["code"] == "INVALID_UPLOAD_REQUEST"

    def test_upload_with_docx_returns_202(self, client):
        fake_docx = BytesIO(b"fake docx content")
        fake_docx.name = "test.docx"
        with (
            patch(
                "app.routers.v1.documents_impl.DocumentService.create_document",
                new=AsyncMock(return_value={"id": "job-001", "status": "PROCESSING"}),
            ),
            patch("app.routers.v1.documents_impl._require_db", return_value=MagicMock()),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota", return_value=None),
            patch(
                "app.routers.v1.documents_impl._validate_magic_bytes", new=AsyncMock(return_value=b"fake docx content")
            ),
            patch(
                "app.routers.v1.documents_impl._scan_uploaded_file",
                new=AsyncMock(return_value={"clean": True, "result": "clean"}),
            ),
            patch("app.pipeline.orchestrator.PipelineOrchestrator"),
            patch(
                "app.services.enhancement_manager.enhancement_manager.dispatch_document_pipeline",
                return_value={"mode": "inline"},
            ),
        ):
            resp = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "test.docx",
                        fake_docx,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"template": "ieee"},
            )
            assert resp.status_code in (200, 202)
            payload = resp.json()
            assert_envelope(payload)

    def test_upload_chunked_endpoint_rejects_missing_fields(self, client):
        resp = client.post("/api/v1/documents/upload/chunked")
        assert resp.status_code in (422, 400)


# ===================================================================
# 2.4 — Generator session CRUD
# ===================================================================


class TestGeneratorSessionSmoke:
    def test_create_agent_session_requires_prompt(self, client):
        with patch(
            "app.services.generator_session_service.GeneratorSessionService.create_session",
            new=AsyncMock(return_value="session-001"),
        ):
            with patch(
                "app.services.generator_session_service.GeneratorSessionService.add_message",
                new=AsyncMock(return_value=None),
            ):
                resp = client.post("/api/v1/generator/sessions", json={"session_type": "agent"})
                assert resp.status_code == 422

    def test_create_agent_session_returns_session_id(self, client):
        with (
            patch(
                "app.services.generator_session_service.GeneratorSessionService.create_session",
                new=AsyncMock(return_value="session-001"),
            ),
            patch(
                "app.services.generator_session_service.GeneratorSessionService.add_message",
                new=AsyncMock(return_value=None),
            ),
            patch("app.services.audit_log_service.audit_log_service.log", new=AsyncMock(return_value=None)),
            patch("app.routers.v1.generator._dispatch_agent_task", return_value=None),
        ):
            resp = client.post(
                "/api/v1/generator/sessions",
                json={"session_type": "agent", "prompt": "Write a paper about AI"},
            )
            assert resp.status_code == 202
            payload = resp.json()
            assert_envelope(payload)
            assert payload["data"]["session_id"] == "session-001"
            assert payload["data"]["status"] == "started"

    def test_get_nonexistent_session_returns_404(self, client):
        with patch(
            "app.services.generator_session_service.GeneratorSessionService.get_session",
            new=AsyncMock(return_value=None),
        ):
            resp = client.get("/api/v1/generator/sessions/nonexistent-id")
            assert resp.status_code == 404
            payload = resp.json()
            assert payload["data"] is None

    def test_get_session_returns_correct_schema(self, client):
        mock_session = {
            "id": "session-001",
            "status": "completed",
            "session_type": "agent",
            "config_json": {"template": "ieee"},
            "outline_json": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "user_id": "user-123",
        }
        with patch(
            "app.services.generator_session_service.GeneratorSessionService.get_session",
            new=AsyncMock(return_value=mock_session),
        ):
            with patch(
                "app.services.generator_session_service.GeneratorSessionService.get_latest_document",
                new=AsyncMock(return_value=None),
            ):
                resp = client.get("/api/v1/generator/sessions/session-001")
                assert resp.status_code == 200
                payload = resp.json()
                assert_envelope(payload)
                data = payload["data"]
                assert data["id"] == "session-001"
                assert data["status"] == "completed"
                assert data["session_type"] == "agent"

    def test_list_sessions_returns_list(self, client):
        with patch(
            "app.services.generator_session_service.GeneratorSessionService.list_sessions",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/v1/generator/sessions")
            assert resp.status_code == 200
            payload = resp.json()
            assert_envelope(payload)
            assert isinstance(payload["data"]["sessions"], list)

    def test_stop_session_returns_404_for_missing(self, client):
        with patch(
            "app.services.generator_session_service.GeneratorSessionService.get_session",
            new=AsyncMock(return_value=None),
        ):
            resp = client.post("/api/v1/generator/sessions/no-such-session/stop")
            assert resp.status_code == 404


# ===================================================================
# 2.5 — Preview endpoint
# ===================================================================


class TestPreviewSmoke:
    def test_live_preview_returns_html(self, client):
        resp = client.post("/api/v1/preview/live", json={"content": "<p>Hello</p>", "templateId": "ieee"})
        assert resp.status_code == 200
        data = resp.json()
        assert "html" in data
        assert "latencyMs" in data
        assert data["html"] == "<p>Mocked</p>"

    def test_live_preview_with_empty_content(self, client):
        with patch(
            "app.services.preview_renderer.preview_renderer.render_preview",
            return_value={"html": "", "latency_ms": 0, "warnings": ["Empty content"]},
        ):
            resp = client.post("/api/v1/preview/live", json={"content": "", "templateId": "ieee"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["html"] == ""

    def test_live_preview_missing_fields(self, client):
        resp = client.post("/api/v1/preview/live", json={})
        assert resp.status_code == 422


# ===================================================================
# 2.6 — Deprecation header contract test
# ===================================================================


class TestDeprecationSmoke:
    def test_active_endpoints_have_no_deprecation(self, client):
        """Current v1 endpoints must NOT have Deprecation header."""
        for path in ("/api/v1/templates", "/api/v1/health", "/api/v1/health/live"):
            resp = client.get(path)
            header_keys = {k.lower() for k in resp.headers}
            assert "deprecation" not in header_keys, f"{path} should not be deprecated"

    def test_deprecated_route_headers(self, client):
        """Verify that a deprecated route emits Deprecation, Sunset, and Link headers."""
        from fastapi import APIRouter

        from app.routers.deprecation import DeprecatedRoute

        test_router = APIRouter(route_class=DeprecatedRoute)
        DeprecatedRoute.successor_map = {"/api/v1/old/test": "/api/v1/new/test"}

        @test_router.get("/api/v1/old/test")
        async def old_endpoint():
            return {"message": "This is deprecated"}

        app.include_router(test_router)
        resp = client.get("/api/v1/old/test")
        assert resp.status_code == 200
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        assert headers_lower.get("deprecation") == "true"
        assert "sunset" in headers_lower
        assert "link" in headers_lower
        assert "successor-version" in headers_lower["link"]


# ===================================================================
# 2.7 — Document download + signed URL contract test
# ===================================================================


class TestDocumentsSmoke:
    def test_list_documents_returns_envelope(self, client):
        with patch("app.routers.v1.documents_impl.DocumentService") as MockSvc:
            MockSvc.list_documents = AsyncMock(return_value=[])
            MockSvc.count_documents = AsyncMock(return_value=0)
            MockSvc.get_document = AsyncMock(return_value=None)
            resp = client.get("/api/v1/documents")
            assert resp.status_code == 200
            payload = resp.json()
            assert_envelope(payload)
            assert "documents" in payload["data"]

    def test_download_requires_valid_job(self, client):
        with patch("app.routers.v1.documents_impl.DocumentService.get_document", new=AsyncMock(return_value=None)):
            resp = client.get("/api/v1/documents/bad-id/download")
            assert resp.status_code == 404

    def test_signed_download_requires_token_and_expires(self, client):
        with patch(
            "app.routers.v1.documents_impl.DocumentService.get_document",
            new=AsyncMock(
                return_value={"id": "doc-001", "user_id": "user-123", "filename": "test.docx", "status": "COMPLETED"}
            ),
        ):
            resp = client.get("/api/v1/documents/doc-001/download", params={"token": "abc", "format": "docx"})
            assert resp.status_code == 400
            assert "token and expires" in resp.json()["error"]["message"].lower()

    def test_signed_download_returns_url(self, client, tmp_path):
        output_path = tmp_path / "output.docx"
        output_path.write_text("fake docx content")
        doc_mock = {
            "id": "doc-001",
            "user_id": None,
            "filename": "test.docx",
            "status": "COMPLETED",
            "output_path": str(output_path),
        }
        with (
            patch("app.routers.v1.documents_impl.DocumentService.get_document", new=AsyncMock(return_value=doc_mock)),
            patch(
                "app.routers.v1.documents_impl.DocumentService.generate_signed_download_url",
                return_value={"url": "https://storage.example.com/doc-001.docx", "expires": 3600},
            ),
            patch("app.config.settings.settings.SIGNED_URL_SECRET", "test-secret"),
        ):
            resp = client.get("/api/v1/documents/doc-001/download", params={"format": "docx"})
            assert resp.status_code == 200
            payload = resp.json()
            assert_envelope(payload)
            assert "url" in payload["data"]
            assert payload["data"]["url"].startswith("https://")

    def test_delete_document_requires_auth(self, client):
        app.dependency_overrides.clear()
        with TestClient(app) as anon:
            resp = anon.delete("/api/v1/documents/doc-001")
            assert resp.status_code in (401, 403)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )
        app.dependency_overrides[get_optional_user] = lambda: User(
            id="user-123", email="user@example.com", role="authenticated"
        )
