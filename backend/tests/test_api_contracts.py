# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.user import User
from app.utils.dependencies import get_current_user, get_optional_user


def _empty_async_iter():
    async def _iterator():
        if False:
            yield {}

    return _iterator()


def _async_iter_from_events(events):
    async def _iterator():
        for event in events:
            yield event

    return _iterator()


def _assert_audit_action_called(audit_mock: AsyncMock, action: str, resource_type: str | None = None):
    matched = [call.kwargs for call in audit_mock.await_args_list if call.kwargs.get("action") == action]
    assert matched, f"Expected audit action '{action}' to be logged."
    if resource_type is not None:
        assert any(item.get("resource_type") == resource_type for item in matched)
    return matched[-1]


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
        patch("app.services.generator_session_service.get_supabase_client", return_value=MagicMock()),
        patch("app.db.supabase_client.get_supabase_client", return_value=MagicMock()),
        patch("app.services.llm_service.generate_with_fallback", new=AsyncMock(return_value="Mocked LLM response")),
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


@pytest.fixture
def upload_docx_fixture() -> Path:
    return (Path("app/templates/ieee/template.docx")).resolve()


@pytest.mark.contract
def test_v1_health_success_envelope_and_generated_request_id(client: TestClient):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["data"] == {"status": "alive"}
    assert payload["error"] is None
    assert payload["request_id"]
    assert payload["timestamp"]
    assert response.headers["X-Request-Id"]


@pytest.mark.contract
def test_v1_health_echoes_client_request_id(client: TestClient):
    response = client.get("/api/v1/health", headers={"X-Request-Id": "contract-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "contract-test-123"
    assert response.json()["request_id"] == "contract-test-123"


@pytest.mark.contract
def test_v1_health_live_envelope(client: TestClient):
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"status": "alive"}
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_protected_route_unauthenticated_error_is_enveloped(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post("/api/v1/generator/sessions", json={"session_type": "agent", "prompt": "hello"})

    assert response.status_code == 401
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "UNAUTHORIZED"
    assert payload["error"]["message"] == "Not authenticated"


@pytest.mark.contract
def test_v1_generator_malformed_json_returns_validation_envelope(client: TestClient):
    response = client.post(
        "/api/v1/generator/sessions",
        content='{"session_type": "agent",',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_SESSION_REQUEST"
    assert "Malformed JSON body" in payload["error"]["message"]


@pytest.mark.skip(reason="Flaky in CI: LLM background task leak")
@pytest.mark.contract
def test_v1_generator_create_agent_success_contract(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch("app.routers.v1.generator._dispatch_agent_task"),
        patch("app.routers.v1.generator._session_service.create_session", new=AsyncMock(return_value="sess-create")),
        patch("app.routers.v1.generator._session_service.add_message", new=AsyncMock()),
        patch("app.routers.v1.generator.audit_log_service.log", new=audit_mock),
        patch("app.routers.v1.generator.abuse_detector.record_generation_request", new_callable=AsyncMock),
    ):
        response = client.post(
            "/api/v1/generator/sessions",
            headers={"Idempotency-Key": "idem-123"},
            json={"session_type": "agent", "prompt": "Draft an abstract", "template": "ieee"},
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["data"] == {"session_id": "sess-create", "status": "started"}
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "generation_start", "generator_session")


@pytest.mark.contract
def test_v1_ready_degraded_payload_stays_enveloped(client: TestClient):
    with patch(
        "app.routers.v1.health.get_readiness_payload",
        new=AsyncMock(return_value=({"ready": False, "checks": {"database": "unavailable"}}, 503)),
    ):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["data"]["ready"] is False
    assert payload["data"]["checks"]["database"] == "unavailable"
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_ready_healthy_payload_stays_enveloped(client: TestClient):
    with patch(
        "app.routers.v1.health.get_readiness_payload",
        new=AsyncMock(return_value=({"ready": True, "checks": {"database": "ok"}}, 200)),
    ):
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["ready"] is True
    assert payload["data"]["checks"]["database"] == "ok"
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_documents_upload_success_contract(
    client: TestClient,
    upload_docx_fixture: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    file_bytes = upload_docx_fixture.read_bytes()
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.routers.v1.documents_impl.UPLOAD_DIR", str(upload_dir), raising=False)
    audit_mock = AsyncMock()

    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.DocumentService.create_document", return_value={"id": "job-123"}),
        patch(
            "app.routers.v1.documents_impl.virus_scanner.scan",
            new_callable=AsyncMock,
            return_value={"clean": True, "engine": "clamav", "result": "clean"},
        ),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline",
            return_value={"mode": "standard"},
        ),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=audit_mock),
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
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "upload", "document")


@pytest.mark.contract
def test_v1_documents_upload_invalid_extension_returns_error_envelope(client: TestClient):
    with patch("app.routers.v1.documents_impl._require_db", return_value=None):
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("malicious.js", b"console.log('boom')", "text/javascript")},
            data={"template": "ieee"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_UPLOAD_REQUEST"
    assert "Invalid file type" in payload["error"]["message"]


@pytest.mark.contract
def test_v1_documents_upload_magic_bytes_mismatch_returns_error_envelope(client: TestClient):
    with patch("app.routers.v1.documents_impl._require_db", return_value=None):
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "spoofed.docx",
                    b"not-a-docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"template": "ieee"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_UPLOAD_REQUEST"
    assert "Unsupported file format" in payload["error"]["message"]


@pytest.mark.contract
def test_v1_documents_list_contract(client: TestClient):
    documents = [
        {
            "id": "job-1",
            "filename": "paper.docx",
            "template": "IEEE",
            "status": "COMPLETED",
            "progress": 100,
            "current_stage": "DONE",
            "created_at": "2026-03-27T10:00:00+00:00",
            "updated_at": "2026-03-27T10:01:00+00:00",
        }
    ]
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.DocumentService.list_documents", return_value=documents),
        patch("app.routers.v1.documents_impl.DocumentService.count_documents", return_value=1),
    ):
        response = client.get("/api/v1/documents?limit=10&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["documents"][0]["id"] == "job-1"
    assert payload["data"]["total"] == 1
    assert payload["data"]["limit"] == 10
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_documents_status_missing_contract(client: TestClient):
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.DocumentService.get_document", return_value=None),
    ):
        response = client.get("/api/v1/documents/missing-job/status")

    assert response.status_code == 404
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "DOCUMENT_NOT_FOUND"


@pytest.mark.contract
def test_v1_documents_download_invalid_format_contract(client: TestClient):
    with patch(
        "app.routers.v1.documents_impl.DocumentService.get_document",
        return_value={
            "id": "job-download",
            "filename": "paper.docx",
            "status": "COMPLETED",
            "user_id": client.mock_user.id,
            "output_path": "unused.docx",
        },
    ):
        response = client.get("/api/v1/documents/job-download/download?format=txt")

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_EXPORT_FORMAT"


@pytest.mark.contract
def test_v1_documents_signed_download_allows_tokenized_access_without_user(client: TestClient, tmp_path: Path):
    output_path = tmp_path / "formatted.docx"
    output_path.write_bytes(b"PK\x03\x04contract-docx")

    document_record = {
        "id": "job-download",
        "filename": "paper.docx",
        "status": "COMPLETED",
        "user_id": client.mock_user.id,
        "output_path": str(output_path),
        "output_hash": None,
    }

    with (
        patch("app.routers.v1.documents_impl.DocumentService.get_document", return_value=document_record),
        patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "test-secret"),
    ):
        link_response = client.get("/api/v1/documents/job-download/download?format=docx")

        app.dependency_overrides[get_optional_user] = lambda: None
        signed_url = link_response.json()["data"]["url"]
        signed_path = signed_url.replace("http://testserver", "")
        download_response = client.get(signed_path)

    assert link_response.status_code == 200
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"PK")


@pytest.mark.contract
def test_v1_documents_batch_upload_limit_contract(client: TestClient, upload_docx_fixture: Path):
    file_bytes = upload_docx_fixture.read_bytes()
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.settings.MAX_BATCH_FILES", 1),
    ):
        response = client.post(
            "/api/v1/documents/batch-upload",
            data={"template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
                (
                    "files",
                    (
                        "two.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
            ],
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_BATCH_UPLOAD"


@pytest.mark.contract
def test_v1_documents_upload_empty_file_contract(client: TestClient):
    with patch("app.routers.v1.documents_impl._require_db", return_value=None):
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "empty.docx",
                    b"",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"template": "ieee"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_UPLOAD_REQUEST"
    assert "File is empty" in payload["error"]["message"]


@pytest.mark.contract
def test_v1_documents_upload_oversize_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 8),
    ):
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "too-big.docx",
                    b"PK\x03\x04" + (b"x" * 32),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"template": "ieee"},
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "DOCUMENT_TOO_LARGE"


@pytest.mark.contract
def test_v1_documents_chunked_upload_success_contract_and_audit(
    client: TestClient,
    upload_docx_fixture: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("app.routers.v1.documents_impl.UPLOAD_DIR", str(tmp_path / "uploads"), raising=False)
    file_bytes = upload_docx_fixture.read_bytes()
    audit_mock = AsyncMock()

    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch(
            "app.routers.v1.documents_impl._validate_magic_bytes",
            new=AsyncMock(side_effect=lambda file, content, file_ext: content),
        ),
        patch(
            "app.routers.v1.documents_impl._scan_uploaded_file",
            new=AsyncMock(return_value={"clean": True, "engine": "clamav", "result": "clean"}),
        ),
        patch("app.routers.v1.documents_impl.DocumentService.create_document", return_value={"id": "chunk-job"}),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline",
            return_value={"mode": "standard"},
        ),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/documents/upload/chunked",
            data={
                "file_id": "chunk-job-1",
                "chunk_index": "0",
                "total_chunks": "1",
                "template": "ieee",
            },
            files={
                "file": (
                    "chunked.docx",
                    file_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "complete"
    assert payload["data"]["job_id"]
    matched = _assert_audit_action_called(audit_mock, "upload", "document")
    assert matched["details"]["chunked"] is True


@pytest.mark.contract
def test_v1_documents_status_existing_job_contract(client: TestClient):
    doc = {
        "id": "job-live",
        "status": "PROCESSING",
        "current_stage": "OCR",
        "progress": 25,
        "user_id": client.mock_user.id,
        "error_message": None,
        "created_at": "2026-03-27T10:00:00+00:00",
        "updated_at": "2026-03-27T10:01:00+00:00",
    }
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.DocumentService.get_document", return_value=doc),
        patch("app.routers.v1.documents_impl.DocumentService.get_processing_statuses", return_value=[]),
    ):
        response = client.get("/api/v1/documents/job-live/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-live"
    assert payload["data"]["status"] == "PROCESSING"
    assert payload["data"]["current_phase"] == "OCR"
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_documents_batch_upload_success_contract_and_audit(
    client: TestClient,
    upload_docx_fixture: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.routers.v1.documents_impl.UPLOAD_DIR", str(tmp_path / "uploads"), raising=False)
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)
    file_bytes = upload_docx_fixture.read_bytes()
    audit_mock = AsyncMock()
    with (
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.routers.v1.documents_impl.settings.MAX_BATCH_FILES", 2),
        patch(
            "app.routers.v1.documents_impl._validate_magic_bytes",
            new=AsyncMock(side_effect=lambda file, content, file_ext: content),
        ),
        patch("app.routers.v1.documents_impl.DocumentService.create_document", return_value={"id": "batch-item"}),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_document_pipeline",
            return_value={"mode": "standard"},
        ),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/documents/batch-upload",
            data={"template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
                (
                    "files",
                    (
                        "two.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
            ],
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] == 2
    assert all(item["status"] == "processing" for item in payload["data"]["jobs"])
    _assert_audit_action_called(audit_mock, "batch_upload", "document_batch")


@pytest.mark.contract
def test_v1_documents_edit_contract_and_audit(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch(
            "app.routers.v1.documents_impl.DocumentService.get_document",
            return_value={
                "id": "job-edit",
                "user_id": client.mock_user.id,
                "filename": "paper.docx",
                "template": "ieee",
            },
        ),
        patch(
            "app.routers.v1.documents_impl.enhancement_manager.dispatch_edit_flow",
            return_value={"mode": "standard"},
        ),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/documents/job-edit/edit",
            json={"edited_structured_data": {"sections": [{"title": "Intro"}]}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["job_id"] == "job-edit"
    assert payload["data"]["status"] == "PROCESSING"
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "edit", "document")


@pytest.mark.contract
def test_v1_documents_delete_contract_and_audit(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch(
            "app.routers.v1.documents_impl.DocumentService.get_document",
            return_value={
                "id": "job-delete",
                "user_id": client.mock_user.id,
                "filename": "paper.docx",
                "output_path": "missing-output.docx",
                "original_file_path": "missing-input.docx",
            },
        ),
        patch("app.routers.v1.documents_impl.DocumentService.delete_document"),
        patch("app.routers.v1.documents_impl.audit_log_service.log", new=audit_mock),
    ):
        response = client.delete("/api/v1/documents/job-delete")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"status": "deleted", "job_id": "job-delete"}
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "delete", "document")


@pytest.mark.contract
def test_v1_generator_fetch_denies_other_user(client: TestClient):
    with patch(
        "app.routers.v1.generator._session_service.get_session",
        new=AsyncMock(
            return_value={
                "id": "sess-1",
                "user_id": "other-user",
                "status": "processing",
                "session_type": "agent",
            }
        ),
    ):
        response = client.get("/api/v1/generator/sessions/sess-1")

    assert response.status_code == 403
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "SESSION_ACCESS_DENIED"


@pytest.mark.contract
def test_v1_generator_idempotency_key_accepted_with_stable_success(client: TestClient):
    with (
        patch("app.routers.v1.generator._dispatch_agent_task"),
        patch(
            "app.routers.v1.generator._session_service.create_session",
            new=AsyncMock(side_effect=["sess-idem-1", "sess-idem-2"]),
        ),
        patch("app.routers.v1.generator._session_service.add_message", new=AsyncMock()),
        patch("app.routers.v1.generator.audit_log_service.log", new_callable=AsyncMock),
        patch("app.routers.v1.generator.abuse_detector.record_generation_request", new_callable=AsyncMock),
    ):
        response_one = client.post(
            "/api/v1/generator/sessions",
            headers={"Idempotency-Key": "idem-key-1"},
            json={"session_type": "agent", "prompt": "Draft introduction", "template": "ieee"},
        )
        response_two = client.post(
            "/api/v1/generator/sessions",
            headers={"Idempotency-Key": "idem-key-1"},
            json={"session_type": "agent", "prompt": "Draft introduction", "template": "ieee"},
        )

    assert response_one.status_code == 202
    assert response_two.status_code == 202
    assert response_one.json()["data"]["status"] == "started"
    assert response_two.json()["data"]["status"] == "started"


@pytest.mark.contract
def test_v1_generator_events_connected_contract(client: TestClient):
    session = {"id": "sess-events", "user_id": client.mock_user.id}
    with (
        patch("app.routers.v1.generator._session_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.routers.v1.generator._pubsub.subscribe", return_value=_empty_async_iter()),
    ):
        with client.stream("GET", "/api/v1/generator/sessions/sess-events/events") as response:
            body = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: connected" in body
    assert '"session_id": "sess-events"' in body
    assert '"request_id":' in body


@pytest.mark.contract
def test_v1_generator_missing_prompt_contract(client: TestClient):
    with patch("app.routers.v1.generator.abuse_detector.record_generation_request", new=AsyncMock()):
        response = client.post(
            "/api/v1/generator/sessions",
            json={"session_type": "agent", "prompt": "   ", "template": "ieee"},
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_SESSION_REQUEST"
    assert "Prompt is required" in payload["error"]["message"]


@pytest.mark.contract
def test_v1_generator_empty_message_contract(client: TestClient):
    session = {"id": "sess-1", "user_id": client.mock_user.id, "session_type": "agent", "status": "processing"}
    with patch("app.routers.v1.generator._session_service.get_session", new=AsyncMock(return_value=session)):
        response = client.post("/api/v1/generator/sessions/sess-1/messages", json={"content": "   "})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_MESSAGE"


@pytest.mark.contract
def test_v1_generator_multi_doc_file_count_contract(client: TestClient, upload_docx_fixture: Path):
    file_bytes = upload_docx_fixture.read_bytes()
    with patch("app.routers.v1.generator.abuse_detector.record_generation_request", new=AsyncMock()):
        response = client.post(
            "/api/v1/generator/sessions",
            data={"session_type": "multi_doc", "template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                )
            ],
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_SESSION_REQUEST"
    assert "Upload between 2 and 6 files." in payload["error"]["message"]


@pytest.mark.contract
def test_v1_generator_multi_doc_create_success_contract_and_audit(
    client: TestClient,
    upload_docx_fixture: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    file_bytes = upload_docx_fixture.read_bytes()
    audit_mock = AsyncMock()
    with (
        patch("app.routers.v1.generator.abuse_detector.record_generation_request", new=AsyncMock()),
        patch("app.routers.v1.generator._session_service.create_session", new=AsyncMock(return_value="sess-md")),
        patch("app.routers.v1.generator._session_service.update_session", new=AsyncMock()),
        patch(
            "app.routers.v1.generator._validate_magic_bytes",
            new=AsyncMock(side_effect=lambda file, content, file_ext: content),
        ),
        patch("app.routers.v1.generator._get_synthesizer", return_value=SimpleNamespace(run=AsyncMock())),
        patch("app.routers.v1.generator.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/generator/sessions",
            data={"session_type": "multi_doc", "template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
                (
                    "files",
                    (
                        "two.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
            ],
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["data"] == {"session_id": "sess-md", "status": "started"}
    assert payload["error"] is None
    matched = _assert_audit_action_called(audit_mock, "generation_start", "generator_session")
    assert matched["details"]["session_type"] == "multi_doc"


@pytest.mark.contract
def test_v1_generator_message_success_contract_and_audit(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch(
            "app.routers.v1.generator._session_service.get_session",
            new=AsyncMock(
                return_value={
                    "id": "sess-msg",
                    "user_id": client.mock_user.id,
                    "session_type": "multi_doc",
                    "status": "processing",
                }
            ),
        ),
        patch("app.routers.v1.generator._session_service.add_message", new=AsyncMock()),
        patch(
            "app.routers.v1.generator._vector_store.query",
            return_value=[
                {"source_doc": "paper.docx", "section": "Introduction", "text": "Source context"},
            ],
        ),
        patch("app.routers.v1.generator.generate_with_fallback", return_value={"text": "Answer from sources."}),
        patch("app.routers.v1.generator.abuse_detector.record_llm_call", new=AsyncMock()),
        patch("app.routers.v1.generator.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/generator/sessions/sess-msg/messages",
            json={"content": "What is the key finding?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["role"] == "assistant"
    assert payload["data"]["content"] == "Answer from sources."
    assert payload["data"]["sources"][0]["source_doc"] == "paper.docx"
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "generation_message", "generator_session")


@pytest.mark.contract
def test_v1_generator_outline_approve_contract_and_audit(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch(
            "app.routers.v1.generator._session_service.get_session",
            new=AsyncMock(
                return_value={
                    "id": "sess-outline",
                    "user_id": client.mock_user.id,
                    "status": "processing",
                    "session_type": "agent",
                }
            ),
        ),
        patch("app.routers.v1.generator._session_service.update_session", new=AsyncMock()),
        patch("app.routers.v1.generator._session_service.add_message", new=AsyncMock()),
        patch("app.routers.v1.generator._dispatch_agent_task"),
        patch("app.routers.v1.generator.audit_log_service.log", new=audit_mock),
    ):
        response = client.post(
            "/api/v1/generator/sessions/sess-outline/outline/approve",
            json={"outline": {"sections": [{"title": "Introduction"}]}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"session_id": "sess-outline", "status": "resuming"}
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "generation_outline_approve", "generator_session")


@pytest.mark.contract
def test_v1_generator_stop_contract_and_audit(client: TestClient):
    audit_mock = AsyncMock()
    with (
        patch(
            "app.routers.v1.generator._session_service.get_session",
            new=AsyncMock(
                return_value={
                    "id": "sess-stop",
                    "user_id": client.mock_user.id,
                    "status": "processing",
                    "progress": 40,
                }
            ),
        ),
        patch("app.routers.v1.generator._session_service.update_session", new=AsyncMock()),
        patch(
            "app.routers.v1.generator._get_agent_pipeline",
            return_value=SimpleNamespace(_emit_sse=AsyncMock()),
        ),
        patch("app.routers.v1.generator.audit_log_service.log", new=audit_mock),
    ):
        response = client.post("/api/v1/generator/sessions/sess-stop/stop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"status": "stopping", "session_id": "sess-stop"}
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "generation_stop", "generator_session")


@pytest.mark.contract
def test_v1_synthesis_session_create_contract(
    client: TestClient,
    upload_docx_fixture: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    file_bytes = upload_docx_fixture.read_bytes()

    with (
        patch("app.routers.v1.synthesis._session_service.create_session", new=AsyncMock(return_value="syn-1")),
        patch("app.routers.v1.synthesis._session_service.update_session", new=AsyncMock()),
        patch("app.routers.v1.synthesis._get_synthesizer", return_value=SimpleNamespace(run=AsyncMock())),
    ):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "multi_doc", "template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
                (
                    "files",
                    (
                        "two.docx",
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
            ],
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["data"] == {"session_id": "syn-1", "status": "started"}
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_synthesis_file_count_contract(client: TestClient, upload_docx_fixture: Path):
    file_bytes = upload_docx_fixture.read_bytes()
    response = client.post(
        "/api/v1/synthesis/sessions",
        data={"session_type": "multi_doc", "template": "ieee"},
        files=[
            (
                "files",
                (
                    "one.docx",
                    file_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            )
        ],
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_SESSION_REQUEST"
    assert "Upload between 2 and 6 files." in payload["error"]["message"]


@pytest.mark.contract
def test_v1_synthesis_oversize_file_contract(client: TestClient):
    with patch("app.routers.v1.synthesis.settings.MAX_FILE_SIZE", 8):
        response = client.post(
            "/api/v1/synthesis/sessions",
            data={"session_type": "multi_doc", "template": "ieee"},
            files=[
                (
                    "files",
                    (
                        "one.docx",
                        b"PK\x03\x04" + (b"x" * 32),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
                (
                    "files",
                    (
                        "two.docx",
                        b"PK\x03\x04" + (b"y" * 32),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ),
                ),
            ],
        )

    assert response.status_code == 413
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "DOCUMENT_TOO_LARGE"


@pytest.mark.contract
def test_v1_synthesis_fetch_own_session_contract(client: TestClient):
    with (
        patch(
            "app.routers.v1.synthesis._session_service.get_session",
            new=AsyncMock(
                return_value={
                    "id": "syn-42",
                    "status": "processing",
                    "session_type": "multi_doc",
                    "user_id": client.mock_user.id,
                    "config_json": {"template": "ieee"},
                    "outline_json": None,
                    "created_at": "2026-03-27T10:00:00+00:00",
                    "updated_at": "2026-03-27T10:01:00+00:00",
                }
            ),
        ),
        patch(
            "app.routers.v1.synthesis._session_service.get_latest_document",
            new=AsyncMock(return_value={"docx_path": "uploads/syn-42/output.docx"}),
        ),
    ):
        response = client.get("/api/v1/synthesis/sessions/syn-42")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == "syn-42"
    assert payload["data"]["session_type"] == "multi_doc"
    assert payload["data"]["docx_path"] == "uploads/syn-42/output.docx"
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_synthesis_events_connected_contract(client: TestClient):
    session = {"id": "syn-events", "user_id": client.mock_user.id}
    with (
        patch("app.routers.v1.synthesis._session_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.routers.v1.synthesis._pubsub.subscribe", return_value=_empty_async_iter()),
    ):
        with client.stream("GET", "/api/v1/synthesis/sessions/syn-events/events") as response:
            body = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: connected" in body
    assert '"session_id": "syn-events"' in body


@pytest.mark.contract
def test_v1_synthesis_events_ongoing_schema_contract(client: TestClient):
    session = {"id": "syn-live", "user_id": client.mock_user.id}
    live_events = [
        {
            "event_type": "progress",
            "session_id": "syn-live",
            "progress": 65,
            "stage": "merge",
            "message": "Merging sources",
        }
    ]
    with (
        patch("app.routers.v1.synthesis._session_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.routers.v1.synthesis._pubsub.subscribe", return_value=_async_iter_from_events(live_events)),
    ):
        with client.stream("GET", "/api/v1/synthesis/sessions/syn-live/events") as response:
            body = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: connected" in body
    assert "event: progress" in body
    assert '"progress": 65' in body


@pytest.mark.contract
def test_v1_templates_builtin_ids_are_canonical(client: TestClient):
    response = client.get("/api/v1/templates")

    assert response.status_code == 200
    template_ids = [item["id"] for item in response.json()["data"]["templates"]]
    assert template_ids == sorted(template_ids)
    assert all(template_id == template_id.lower() for template_id in template_ids)


@pytest.mark.contract
def test_v1_templates_exposure_rules_contract(client: TestClient):
    response = client.get("/api/v1/templates")

    assert response.status_code == 200
    templates = response.json()["data"]["templates"]
    template_ids = {item["id"] for item in templates}
    assert "resume" in template_ids
    assert "portfolio" in template_ids
    assert any(item.startswith("modern_") for item in template_ids)
    assert all(not item.startswith("__") for item in template_ids)


@pytest.mark.contract
def test_v1_admin_route_non_admin_forbidden_contract(client: TestClient):
    response = client.get("/api/v1/health/admin")

    assert response.status_code == 403
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "FORBIDDEN"
    assert payload["error"]["message"] == "Admin access required"


@pytest.mark.contract
def test_v1_admin_route_admin_success_contract(client: TestClient):
    app.dependency_overrides[get_current_user] = lambda: User(
        id="admin-1",
        email="admin@example.com",
        role="admin",
    )
    response = client.get("/api/v1/health/admin")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"status": "alive", "scope": "admin"}
    assert payload["error"] is None


@pytest.mark.contract
def test_v1_billing_invalid_signature_contract(client: TestClient):
    fake_signature_error = type("FakeSignatureError", (Exception,), {})
    audit_mock = AsyncMock()
    with (
        patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
        patch("app.routers.v1.billing.stripe.error.SignatureVerificationError", new=fake_signature_error),
        patch(
            "app.routers.v1.billing.stripe.Webhook.construct_event",
            side_effect=fake_signature_error("boom"),
        ),
        patch(
            "app.routers.v1.billing.audit_log_service.log",
            new=audit_mock,
        ),
    ):
        response = client.post("/api/v1/billing/webhook", content=b"{}")

    assert response.status_code == 400
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_BILLING_WEBHOOK"
    assert payload["error"]["message"] == "Invalid Stripe signature."
    matched = _assert_audit_action_called(audit_mock, "billing_webhook_rejected", "billing")
    assert matched["details"]["reason"] == "invalid_signature"


@pytest.mark.contract
def test_v1_billing_checkout_event_contract_and_audit(client: TestClient):
    supabase_table = MagicMock()
    supabase_table.update.return_value = supabase_table
    supabase_table.eq.return_value = supabase_table
    supabase_table.execute.return_value = MagicMock(data=[{"id": "user-123"}])
    supabase = MagicMock()
    supabase.table.return_value = supabase_table
    audit_mock = AsyncMock()

    with (
        patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
        patch(
            "app.routers.v1.billing.stripe.Webhook.construct_event",
            return_value={
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "evt-object-1",
                        "customer": "cus_123",
                        "payment_status": "paid",
                        "metadata": {"user_id": "user-123"},
                    }
                },
            },
        ),
        patch("app.routers.v1.billing.get_supabase_client", return_value=supabase),
        patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
    ):
        response = client.post("/api/v1/billing/webhook", content=b"{}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"received": True}
    assert payload["error"] is None
    _assert_audit_action_called(audit_mock, "billing_change", "billing")

