from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


@pytest.fixture
def client():
    from app.main import app
    from app.utils.dependencies import get_current_user, get_optional_user

    mock_user = MagicMock()
    mock_user.id = "user-123"

    app.dependency_overrides[get_optional_user] = lambda: mock_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides = {}


class TestParseConfig:
    def test_empty(self):
        from app.routers.v1.generator import _parse_config
        assert _parse_config("") == {}

    def test_valid_json(self):
        from app.routers.v1.generator import _parse_config
        assert _parse_config('{"key":"val"}') == {"key": "val"}

    def test_invalid_json_raises(self):
        from app.routers.v1.generator import _parse_config
        with pytest.raises(HTTPException) as exc:
            _parse_config("{bad}")
        assert exc.value.status_code == 422
        assert "Invalid config JSON" in exc.value.detail


class TestDetectSectionRewrite:
    def test_no_trigger(self):
        from app.routers.v1.generator import _detect_section_rewrite
        assert _detect_section_rewrite("hello world", []) is None

    def test_rewrite_trigger_found(self):
        from app.routers.v1.generator import _detect_section_rewrite
        result = _detect_section_rewrite("please rewrite the introduction", ["Introduction", "Methods"])
        assert result == "Introduction"

    def test_expand_trigger_found(self):
        from app.routers.v1.generator import _detect_section_rewrite
        result = _detect_section_rewrite("expand the results section", ["Results"])
        assert result == "Results"

    def test_matches_section_name_directly(self):
        from app.routers.v1.generator import _detect_section_rewrite
        result = _detect_section_rewrite("rewrite discussion", ["Discussion", "Conclusion"])
        assert result == "Discussion"

    def test_aliases_intro(self):
        from app.routers.v1.generator import _detect_section_rewrite
        assert _detect_section_rewrite("rewrite the background", []) == "Introduction"
        assert _detect_section_rewrite("rewrite the abstract", []) == "Abstract"
        assert _detect_section_rewrite("revise methodology", []) == "Methods"
        assert _detect_section_rewrite("reword conclusion", []) == "Conclusion"

    def test_no_match_with_sections(self):
        from app.routers.v1.generator import _detect_section_rewrite
        result = _detect_section_rewrite("rewrite something", ["Acknowledgments"])
        assert result is None

    def test_trigger_not_at_start(self):
        from app.routers.v1.generator import _detect_section_rewrite
        assert _detect_section_rewrite("can you update the literature review", []) == "Literature Review"


class TestAssertSessionOwner:
    def test_owner_matches(self):
        from app.routers.v1.generator import _assert_session_owner
        user = MagicMock()
        user.id = "u1"
        _assert_session_owner({"user_id": "u1"}, user)

    def test_owner_matches_string_user(self):
        from app.routers.v1.generator import _assert_session_owner
        _assert_session_owner({"user_id": "u1"}, "u1")

    def test_owner_different_raises(self):
        from app.routers.v1.generator import _assert_session_owner
        user = MagicMock()
        user.id = "u2"
        with pytest.raises(HTTPException) as exc:
            _assert_session_owner({"user_id": "u1"}, user)
        assert exc.value.status_code == 403
        assert "Access denied" in exc.value.detail

    def test_no_session_user_passes(self):
        from app.routers.v1.generator import _assert_session_owner
        user = MagicMock()
        user.id = "u1"
        _assert_session_owner({}, user)


class TestSerializeSession:
    def test_full_session(self):
        from app.routers.v1.generator import _serialize_session
        session = {
            "id": "s1",
            "status": "done",
            "session_type": "agent",
            "config_json": {"user_prompt": "test", "template": "ieee"},
            "outline_json": {"sections": [{"title": "Intro"}]},
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
        }
        result = _serialize_session(session)
        assert result["id"] == "s1"
        assert result["prompt"] == "test"
        assert result["template"] == "ieee"

    def test_minimal_session(self):
        from app.routers.v1.generator import _serialize_session
        result = _serialize_session({"id": "s2"})
        assert result["id"] == "s2"
        assert result["prompt"] is None

    def test_config_fallback_keys(self):
        from app.routers.v1.generator import _serialize_session
        s = _serialize_session({"config_json": {"prompt": "p", "template_id": "apa"}})
        assert s["prompt"] == "p"
        assert s["template"] == "apa"

    def test_config_content_fallback(self):
        from app.routers.v1.generator import _serialize_session
        s = _serialize_session({"config_json": {"content": "c", "template_id": "mla"}})
        assert s["prompt"] == "c"
        assert s["template"] == "mla"


class TestAssertGenerationOwner:
    @pytest.mark.asyncio
    async def test_through_generator_owner_matches(self):
        from app.routers.v1.generator import _assert_generation_owner
        mock_gen = MagicMock()
        mock_gen.get_session.return_value = {"user_id": "u1"}
        with patch("app.routers.v1.generator.get_generator", return_value=mock_gen):
            await _assert_generation_owner("job-1", "u1")

    @pytest.mark.asyncio
    async def test_through_generator_not_owner_raises(self):
        from app.routers.v1.generator import _assert_generation_owner
        mock_gen = MagicMock()
        mock_gen.get_session.return_value = {"user_id": "u1"}
        with patch("app.routers.v1.generator.get_generator", return_value=mock_gen):
            with pytest.raises(HTTPException) as exc:
                await _assert_generation_owner("job-1", "u2")
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_through_document_service(self):
        from app.routers.v1.generator import _assert_generation_owner
        mock_gen = MagicMock()
        mock_gen.get_session.return_value = None
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator.DocumentService.get_document", new_callable=AsyncMock, return_value={"user_id": "u1"}),
        ):
            await _assert_generation_owner("job-1", "u1")

    @pytest.mark.asyncio
    async def test_through_document_not_owner_raises(self):
        from app.routers.v1.generator import _assert_generation_owner
        mock_gen = MagicMock()
        mock_gen.get_session.return_value = None
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator.DocumentService.get_document", new_callable=AsyncMock, return_value={"user_id": "u1"}),
        ):
            with pytest.raises(HTTPException) as exc:
                await _assert_generation_owner("job-1", "u2")
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_record_passes(self):
        from app.routers.v1.generator import _assert_generation_owner
        mock_gen = MagicMock()
        mock_gen.get_session.return_value = None
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator.DocumentService.get_document", new_callable=AsyncMock, return_value=None),
        ):
            await _assert_generation_owner("job-1", "u1")


class TestDispatchAgentTask:
    def test_pipeline_queued(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = True
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
            patch("app.tasks.celery_tasks.process_agent_pipeline_task") as mock_task,
        ):
            _dispatch_agent_task(bt, "pipeline", "sid", "prompt")
        em.should_queue_job.assert_called_once_with(15.0)
        mock_task.delay.assert_called_once_with("sid", "prompt")

    def test_resume_queued(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = True
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
            patch("app.tasks.celery_tasks.process_agent_resume_task") as mock_task,
        ):
            _dispatch_agent_task(bt, "resume", "sid")
        mock_task.delay.assert_called_once_with("sid")

    def test_rewrite_queued(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = True
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
            patch("app.tasks.celery_tasks.process_agent_rewrite_task") as mock_task,
        ):
            _dispatch_agent_task(bt, "rewrite", "sid", "section", "prompt")
        mock_task.delay.assert_called_once_with("sid", "section", "prompt")

    def test_pipeline_background(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = False
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
        ):
            _dispatch_agent_task(bt, "pipeline", "sid", "prompt")
        bt.add_task.assert_called_once()

    def test_resume_background(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = False
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
        ):
            _dispatch_agent_task(bt, "resume", "sid")
        bt.add_task.assert_called_once()

    def test_rewrite_background(self):
        from app.routers.v1.generator import _dispatch_agent_task
        bt = MagicMock()
        em = MagicMock()
        em.should_queue_job.return_value = False
        with (
            patch("app.routers.v1.generator.enhancement_manager", em),
        ):
            _dispatch_agent_task(bt, "rewrite", "sid", "section", "prompt")
        bt.add_task.assert_called_once()


class TestDownloadGeneratedArtifact:
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        from app.routers.v1.generator import _download_generated_artifact
        with pytest.raises(HTTPException) as exc:
            await _download_generated_artifact("job-1", "txt", MagicMock())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_job_not_found(self):
        from app.routers.v1.generator import _download_generated_artifact
        mock_gen = MagicMock()
        mock_gen.get_status.side_effect = KeyError("not found")
        user = MagicMock()
        user.id = "u1"
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
        ):
            with pytest.raises(HTTPException) as exc:
                await _download_generated_artifact("job-1", "docx", user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_job_not_done(self):
        from app.routers.v1.generator import _download_generated_artifact
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "processing", "progress": 50}
        user = MagicMock()
        user.id = "u1"
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
        ):
            with pytest.raises(HTTPException) as exc:
                await _download_generated_artifact("job-1", "docx", user)
            assert exc.value.status_code == 409
            assert "not yet complete" in exc.value.detail

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        from app.routers.v1.generator import _download_generated_artifact
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = None
        user = MagicMock()
        user.id = "u1"
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
        ):
            with pytest.raises(HTTPException) as exc:
                await _download_generated_artifact("job-1", "docx", user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_docx_download_success(self, tmp_path):
        from app.routers.v1.generator import _download_generated_artifact
        file_path = tmp_path / "output.docx"
        file_path.write_bytes(b"PKdocx")
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = file_path
        user = MagicMock()
        user.id = "u1"
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
        ):
            result = await _download_generated_artifact("job-1", "docx", user)
        assert result is not None
        assert result.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @pytest.mark.asyncio
    async def test_pdf_download_success(self, tmp_path):
        from app.routers.v1.generator import _download_generated_artifact
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PKdocx")
        pdf_path = tmp_path / "output.pdf"
        pdf_path.write_bytes(b"PDFdata")
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = docx_path
        user = MagicMock()
        user.id = "u1"
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
        ):
            result = await _download_generated_artifact("job-1", "pdf", user)
        assert result is not None
        assert result.media_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_pdf_export_converts(self, tmp_path):
        from app.routers.v1.generator import _download_generated_artifact
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PKdocx")
        pdf_target = tmp_path / "output.pdf"

        def _fake_convert(*_a, **_kw):
            pdf_target.write_bytes(b"PDFdata")
            return str(pdf_target)

        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = docx_path
        user = MagicMock()
        user.id = "u1"
        mock_exporter = MagicMock()
        mock_exporter.convert_to_pdf.side_effect = _fake_convert
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
            patch("app.routers.v1.generator.PDFExporter", return_value=mock_exporter),
        ):
            result = await _download_generated_artifact("job-1", "pdf", user)
        assert result is not None
        assert result.media_type == "application/pdf"
        mock_exporter.convert_to_pdf.assert_called_once()

    @pytest.mark.asyncio
    async def test_pdf_export_failure_raises_500(self, tmp_path):
        from app.routers.v1.generator import _download_generated_artifact
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PKdocx")
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = docx_path
        user = MagicMock()
        user.id = "u1"
        mock_exporter = MagicMock()
        mock_exporter.convert_to_pdf.return_value = None
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
            patch("app.routers.v1.generator.PDFExporter", return_value=mock_exporter),
        ):
            with pytest.raises(HTTPException) as exc:
                await _download_generated_artifact("job-1", "pdf", user)
            assert exc.value.status_code == 500
            assert "PDF conversion failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_pdf_export_runtime_error(self, tmp_path):
        from app.routers.v1.generator import _download_generated_artifact
        docx_path = tmp_path / "output.docx"
        docx_path.write_bytes(b"PKdocx")
        mock_gen = MagicMock()
        mock_gen.get_status.return_value = {"status": "done", "progress": 100}
        mock_gen.get_download_path.return_value = docx_path
        user = MagicMock()
        user.id = "u1"
        mock_exporter = MagicMock()
        mock_exporter.convert_to_pdf.side_effect = RuntimeError("no binary")
        with (
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
            patch("app.routers.v1.generator.PDFExporter", return_value=mock_exporter),
        ):
            with pytest.raises(HTTPException) as exc:
                await _download_generated_artifact("job-1", "pdf", user)
            assert exc.value.status_code == 400
            assert "PDF export unavailable" in exc.value.detail


class TestGenerationEndpoints:
    def test_start_generation_malformed_json(self, client):
        response = client.post("/api/v1/generator/sessions", content=b"not json", headers={"content-type": "application/json"})
        assert response.status_code == 422

    def test_start_generation_missing_prompt(self, client):
        response = client.post(
            "/api/v1/generator/sessions",
            json={"session_type": "agent", "prompt": ""},
        )
        assert response.status_code == 422

    def test_start_generation_wrong_session_type(self, client):
        response = client.post(
            "/api/v1/generator/sessions",
            json={"session_type": "multi_doc", "prompt": "test"},
        )
        assert response.status_code == 422

    def test_start_generation_form_bad_file_count(self, client):
        response = client.post(
            "/api/v1/generator/sessions",
            data={"session_type": "multi_doc"},
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 422

    @patch("app.routers.v1.generator._session_service.create_session", new_callable=AsyncMock)
    def test_start_generation_form_bad_ext(self, mock_create, client):
        mock_create.return_value = "fake_session_id"
        response = client.post(
            "/api/v1/generator/sessions",
            data={"session_type": "multi_doc"},
            files=[
                ("files", ("test1.pdf", b"%PDF-1.4 dummy pdf", "application/pdf")),
                ("files", ("test2.bad", b"dummy bad file", "application/octet-stream")),
            ]
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["error"]["message"]

    def test_get_session_not_found(self, client):
        with patch(
            "app.routers.v1.generator._session_service.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.get("/api/v1/generator/sessions/nonexistent")
        assert response.status_code == 404

    def test_get_session_access_denied(self, client):
        with patch(
            "app.routers.v1.generator._session_service.get_session",
            new_callable=AsyncMock,
            return_value={"id": "s1", "user_id": "other-user"},
        ):
            response = client.get("/api/v1/generator/sessions/s1")
        assert response.status_code == 403

    def test_list_sessions(self, client):
        sessions = [
            {"id": "s1", "status": "done", "session_type": "agent",
             "config_json": {"user_prompt": "test"}, "created_at": "now", "updated_at": "now"}
        ]
        with patch(
            "app.routers.v1.generator._session_service.list_sessions",
            new_callable=AsyncMock,
            return_value=sessions,
        ):
            response = client.get("/api/v1/generator/sessions")
        assert response.status_code == 200
        assert len(response.json()["data"]["sessions"]) == 1

    def test_post_message_empty_content(self, client):
        with patch(
            "app.routers.v1.generator._session_service.get_session",
            new_callable=AsyncMock,
            return_value={"id": "s1", "user_id": "user-123"},
        ):
            response = client.post(
                "/api/v1/generator/sessions/s1/messages",
                json={"content": ""},
            )
        assert response.status_code == 422

    def test_post_message_session_not_found(self, client):
        with patch(
            "app.routers.v1.generator._session_service.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post(
                "/api/v1/generator/sessions/s1/messages",
                json={"content": "hello"},
            )
        assert response.status_code == 404

    def test_approve_outline(self, client):
        with (
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value={"id": "s1", "user_id": "user-123"},
            ),
            patch(
                "app.routers.v1.generator._session_service.update_session",
                new_callable=AsyncMock,
            ),
            patch(
                "app.routers.v1.generator._session_service.add_message",
                new_callable=AsyncMock,
            ),
            patch("app.routers.v1.generator._dispatch_agent_task"),
            patch("app.routers.v1.generator.audit_log_service.log", new_callable=AsyncMock),
        ):
            response = client.post(
                "/api/v1/generator/sessions/s1/outline/approve",
                json={"sections": [{"title": "Intro"}]},
            )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "resuming"

    def test_approve_outline_session_not_found(self, client):
        with patch(
            "app.routers.v1.generator._session_service.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = client.post("/api/v1/generator/sessions/s1/outline/approve")
        assert response.status_code == 404

    def test_stop_session(self, client):
        with (
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value={"id": "s1", "user_id": "user-123", "config_json": {"k": "v"}},
            ),
            patch(
                "app.routers.v1.generator._session_service.update_session",
                new_callable=AsyncMock,
            ),
            patch("app.routers.v1.generator.audit_log_service.log", new_callable=AsyncMock),
        ):
            response = client.post("/api/v1/generator/sessions/s1/stop")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "stopping"

    def test_download_generated_not_found(self, client):
        mock_gen = MagicMock()
        mock_gen.get_status.side_effect = KeyError("not found")
        with (
            patch("app.routers.v1.generator._assert_generation_owner", new_callable=AsyncMock),
            patch("app.routers.v1.generator.get_generator", return_value=mock_gen),
        ):
            response = client.get("/api/v1/generator/sessions/nonexistent/download")
        assert response.status_code == 404

    def test_get_messages(self, client):
        messages = [
            {"role": "user", "content": "hello", "created_at": "now"},
            {"role": "assistant", "content": None, "created_at": "now"},
            {"role": "assistant", "content": "response", "created_at": "now"},
        ]
        with (
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value={"id": "s1", "user_id": "user-123"},
            ),
            patch(
                "app.routers.v1.generator._session_service.get_messages",
                new_callable=AsyncMock,
                return_value=messages,
            ),
        ):
            response = client.get("/api/v1/generator/sessions/s1/messages")
        assert response.status_code == 200
        assert len(response.json()["data"]["messages"]) == 2

    def test_get_latest_document(self, client):
        with (
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value={"id": "s1", "user_id": "user-123"},
            ),
            patch(
                "app.routers.v1.generator._session_service.get_latest_document",
                new_callable=AsyncMock,
                return_value={"content_json": {"text": "hello"}, "docx_path": "/path/docx", "version_number": 2},
            ),
        ):
            response = client.get("/api/v1/generator/sessions/s1/document")
        assert response.status_code == 200
        assert response.json()["data"]["version_number"] == 2

    def test_get_latest_document_none(self, client):
        with (
            patch(
                "app.routers.v1.generator._session_service.get_session",
                new_callable=AsyncMock,
                return_value={"id": "s1", "user_id": "user-123"},
            ),
            patch(
                "app.routers.v1.generator._session_service.get_latest_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            response = client.get("/api/v1/generator/sessions/s1/document")
        assert response.status_code == 200
        assert response.json()["data"]["content"] is None
