# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# -*- coding: utf-8 -*-
"""
Deep tests for DocumentGenerator — orchestrator of generate-from-scratch jobs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_GENERATOR_MODULE = "app.pipeline.generation.document_generator"


# ── helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _auto_mocks():
    """Reset class-level state on DocumentService between tests."""
    from app.services.document_service import DocumentService

    DocumentService._supports_file_hash = None
    DocumentService._supports_output_hash = None
    return


def _make_supabase_result(data=None):
    """Build a minimal supabase-py execute() return value."""
    result = MagicMock()
    result.data = data
    return result


def _fake_block(block_type: str, content: str, level: int = 0) -> dict:
    return {"type": block_type, "content": content, "level": level}


# ── Test suite ───────────────────────────────────────────────────────────────


class TestNormalizeStatus:
    """_normalize_status static method."""

    def test_exact_matches(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        cases = [
            ("PENDING", "pending"),
            ("PROCESSING", "processing"),
            ("COMPLETED", "done"),
            ("COMPLETED_WITH_WARNINGS", "done"),
            ("FAILED", "failed"),
            ("CANCELLED", "failed"),
            ("pending", "pending"),
            ("processing", "processing"),
            ("done", "done"),
            ("failed", "failed"),
        ]
        for raw, expected in cases:
            assert DocumentGenerator._normalize_status(raw) == expected

    def test_none_and_empty_fall_back_to_processing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status(None) == "processing"
        assert DocumentGenerator._normalize_status("") == "processing"

    def test_unknown_status_fall_back_to_processing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("SUPERCALIFRAGILISTIC") == "processing"
        assert DocumentGenerator._normalize_status("random_string") == "processing"

    def test_whitespace_stripped_before_match(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("  FAILED  ") == "failed"
        assert DocumentGenerator._normalize_status("\tCOMPLETED\n") == "done"


class TestNowIso:
    """_now_iso static method."""

    def test_returns_utc_iso_format(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._now_iso()
        # ISO-8601 — must end in Z or have a +00:00 offset
        assert isinstance(result, str)
        assert "+00:00" in result or result.endswith("Z") or result.endswith("+00:00")
        # round-trip parsable
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None


class TestDefaultSessionConfig:
    """_default_session_config method."""

    def test_returns_expected_dict(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        config = dg._default_session_config(
            doc_type="thesis",
            template="ieee",
            metadata={"title": "T"},
            options={"fast": True},
            user_id="u1",
        )
        assert config["doc_type"] == "thesis"
        assert config["template"] == "ieee"
        assert config["metadata"] == {"title": "T"}
        assert config["options"] == {"fast": True}
        assert config["user_id"] == "u1"
        assert config["stage"] == "queued"
        assert config["message"] == "Generation job queued."
        assert config["error"] is None
        assert config["output_path"] is None

    def test_all_params_preserved(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        config = dg._default_session_config(
            doc_type="resume",
            template="modern",
            metadata={"name": "Alice", "skills": ["Py"]},
            options={"word_count_target": 500},
            user_id="user-42",
        )
        assert config["metadata"]["skills"] == ["Py"]
        assert config["options"]["word_count_target"] == 500


class TestSessionRecordToStatus:
    """_session_record_to_status method."""

    def test_with_outline(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {
            "id": "job-1",
            "status": "COMPLETED",
            "progress": 100,
            "config_json": {
                "stage": "done",
                "message": "All set.",
                "error": None,
                "output_path": "/tmp/out.docx",
            },
            "outline_json": ["Intro", "Methods"],
        }
        result = dg._session_record_to_status(session, include_outline=True)
        assert result["job_id"] == "job-1"
        assert result["status"] == "done"
        assert result["progress"] == 100
        assert result["outline"] == ["Intro", "Methods"]

    def test_without_outline(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {
            "id": "job-2",
            "status": "PENDING",
            "progress": 0,
            "config_json": {"stage": "queued", "message": "Waiting..."},
        }
        result = dg._session_record_to_status(session, include_outline=False)
        assert result["outline"] == []

    def test_outline_is_non_list_becomes_empty(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {
            "id": "j",
            "status": "done",
            "progress": 100,
            "config_json": {},
            "outline_json": "not-a-list",
        }
        result = dg._session_record_to_status(session, include_outline=True)
        assert result["outline"] == []

    def test_outline_items_stripped_and_filtered(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {
            "id": "j",
            "status": "done",
            "progress": 100,
            "config_json": {},
            "outline_json": ["  Hello ", "", "  ", "World"],
        }
        result = dg._session_record_to_status(session, include_outline=True)
        assert result["outline"] == ["Hello", "World"]

    def test_progress_clamped_to_0_100(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {"id": "j", "status": "done", "progress": 999, "config_json": {}}
        result = dg._session_record_to_status(session)
        assert 0 <= result["progress"] <= 100
        assert result["progress"] == 100

    def test_fallback_keys_when_config_missing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {"id": "j"}
        result = dg._session_record_to_status(session)
        assert result["stage"] == "queued"
        assert result["message"] == "Generation in progress..."
        assert result["error"] is None
        assert result["output_path"] is None


class TestGetSessionRecord:
    """_get_session_record — Supabase + volatile fallback."""

    def test_supabase_returns_data(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb:
            sb = MagicMock()
            sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
                _make_supabase_result({"id": "s1", "status": "done"})
            )
            mock_sb.return_value = sb
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            result = dg._get_session_record("s1")
            assert result == {"id": "s1", "status": "done"}

    def test_supabase_none_falls_to_volatile(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["v1"] = {"id": "v1", "status": "pending"}
            result = dg._get_session_record("v1")
            assert result == {"id": "v1", "status": "pending"}

    def test_supabase_exception_falls_to_volatile(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb:
            sb = MagicMock()
            sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = (
                RuntimeError("DB down")
            )
            mock_sb.return_value = sb
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["v2"] = {"id": "v2", "status": "volatile_only"}
            result = dg._get_session_record("v2")
            assert result == {"id": "v2", "status": "volatile_only"}

    def test_supabase_empty_data_returns_none(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb:
            sb = MagicMock()
            sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
                _make_supabase_result(None)
            )
            mock_sb.return_value = sb
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            result = dg._get_session_record("missing")
            assert result is None

    def test_not_in_any_store_returns_none(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            result = dg._get_session_record("ghost")
            assert result is None


class TestGetSession:
    """get_session — public wrapper."""

    def test_delegates_to_get_session_record(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["s"] = {"id": "s"}
            assert dg.get_session("s") == {"id": "s"}
            assert dg.get_session("nope") is None


class TestUpdateStatus:
    """update_status — DB + volatile merge."""

    def test_updates_volatile_when_supabase_none(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j1"] = {"id": "j1", "config_json": {}}
            dg.update_status("j1", status="done", progress=100, stage="done", message="OK")
            assert dg._volatile_sessions["j1"]["status"] == "done"
            assert dg._volatile_sessions["j1"]["progress"] == 100
            assert dg._volatile_sessions["j1"]["config_json"]["status"] == "done"
            assert dg._volatile_sessions["j1"]["config_json"]["stage"] == "done"

    def test_updates_db_when_supabase_available(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb:
            sb = MagicMock()
            mock_sb.return_value = sb
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j2"] = {"id": "j2", "config_json": {}}
            dg.update_status("j2", status="failed", progress=0, error="boom")
            sb.table.return_value.update.return_value.eq.return_value.execute.assert_called_once()

    def test_db_exception_logged_not_raised(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb:
            sb = MagicMock()
            sb.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError("fail")
            mock_sb.return_value = sb
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j3"] = {"id": "j3", "config_json": {}}
            dg.update_status("j3", status="processing", progress=50)
            assert dg._volatile_sessions["j3"]["status"] == "processing"

    def test_with_outline_payload(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j4"] = {"id": "j4", "config_json": {}}
            dg.update_status("j4", status="processing", progress=50, outline=["A", "B"])
            assert dg._volatile_sessions["j4"]["outline_json"] == ["A", "B"]

    def test_empty_outline_items_filtered(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["j4b"] = {"id": "j4b", "config_json": {}}
            dg.update_status("j4b", status="processing", progress=50, outline=["", "  ", "Real"])
            assert dg._volatile_sessions["j4b"]["outline_json"] == ["Real"]

    def test_creates_record_if_not_found(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg.update_status("new-job", status="pending", progress=0)
            assert dg._volatile_sessions["new-job"]["status"] == "pending"

    def test_progress_clamped(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["jc"] = {"id": "jc", "config_json": {}}
            dg.update_status("jc", status="done", progress=200)
            assert dg._volatile_sessions["jc"]["progress"] == 100


class TestGetStatus:
    """get_status — reads from session then falls back to DocumentService."""

    def test_from_session_record(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["gs1"] = {
                "id": "gs1",
                "status": "done",
                "progress": 100,
                "config_json": {"stage": "done", "message": "OK", "output_path": "/p/docx"},
                "outline_json": ["Intro"],
            }
            status = dg.get_status("gs1")
            assert status["status"] == "done"
            assert status["output_path"] == "/p/docx"
            assert status["outline"] == ["Intro"]

    def test_fetches_outline_from_document_result_when_missing_in_status(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document_result.return_value = {
                    "structured_data": {"outline": ["Intro", "Methods"]},
                }
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                dg._volatile_sessions["gs2"] = {
                    "id": "gs2",
                    "status": "done",
                    "progress": 100,
                    "config_json": {"stage": "done", "message": "OK"},
                }
                status = dg.get_status("gs2")
                assert "Intro" in status["outline"]

    def test_fallback_to_document_service(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = {
                    "status": "COMPLETED",
                    "current_stage": "DONE",
                    "progress": 100,
                    "output_path": "/tmp/doc.docx",
                }
                MockDS.get_document_result.return_value = {
                    "structured_data": {"outline": ["Intro"]},
                }
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                status = dg.get_status("gs3")
                assert status["status"] == "done"
                assert status["output_path"] == "/tmp/doc.docx"
                assert status["outline"] == ["Intro"]

    def test_raises_key_error_for_unknown(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = None
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                with pytest.raises(KeyError, match="not found"):
                    dg.get_status("unknown")

    def test_maps_document_statuses_correctly(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                for db_status, expected in [
                    ("PENDING", "pending"),
                    ("PROCESSING", "processing"),
                    ("COMPLETED", "done"),
                    ("COMPLETED_WITH_WARNINGS", "done"),
                    ("FAILED", "failed"),
                    ("CANCELLED", "failed"),
                ]:
                    MockDS.get_document.return_value = {
                        "status": db_status,
                        "current_stage": "SOME_STAGE",
                        "progress": 0,
                    }
                    MockDS.get_document_result.return_value = None
                    from app.pipeline.generation.document_generator import DocumentGenerator

                    dg = DocumentGenerator()
                    status = dg.get_status(f"job_{db_status}")
                    assert status["status"] == expected, f"failed for {db_status}"


class TestGetDownloadPath:
    """get_download_path — returns Path for completed, else None."""

    def test_returns_path_for_completed_volatile(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["gd1"] = {
                "id": "gd1",
                "status": "done",
                "progress": 100,
                "config_json": {"stage": "done", "message": "OK", "output_path": "C:\\out\\test.docx"},
            }
            result = dg.get_download_path("gd1")
            assert isinstance(result, Path)
            assert "test.docx" in str(result)

    def test_none_for_pending_volatile(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = None
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                dg._volatile_sessions["gd2"] = {
                    "id": "gd2",
                    "status": "pending",
                    "progress": 0,
                    "config_json": {"stage": "queued"},
                }
                assert dg.get_download_path("gd2") is None

    def test_fallback_to_document_service(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = {
                    "status": "COMPLETED",
                    "output_path": "/real/output.docx",
                }
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                result = dg.get_download_path("gd3")
                assert isinstance(result, Path)
                assert "output.docx" in str(result)

    def test_returns_none_when_document_missing(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = None
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                assert dg.get_download_path("ghost") is None

    def test_returns_none_for_failed_document(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                MockDS.get_document.return_value = {
                    "status": "FAILED",
                    "output_path": None,
                }
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                assert dg.get_download_path("failed-job") is None


class TestStartJob:
    """start_job — full lifecycle creation."""

    @pytest.mark.asyncio
    async def test_returns_uuid_and_creates_volatile_session(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                    with patch(f"{_GENERATOR_MODULE}.emit_event"):
                        MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        MockDS.create_document.return_value = {"id": "doc-id"}
                        from app.pipeline.generation.document_generator import DocumentGenerator

                        dg = DocumentGenerator()
                        job_id = await dg.start_job(
                            doc_type="academic_paper",
                            template="ieee",
                            metadata={"title": "Paper"},
                            options={"word_count_target": 2000},
                            user_id="user-1",
                        )
                        assert job_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        assert job_id in dg._volatile_sessions
                        assert dg._volatile_sessions[job_id]["status"] == "pending"
                        assert dg._volatile_sessions[job_id]["config_json"]["doc_type"] == "academic_paper"

    @pytest.mark.asyncio
    async def test_supabase_insert_failure_stores_in_volatile(self):
        with patch("app.db.repositories.base.get_supabase_client") as mock_sb_getter:
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                    with patch(f"{_GENERATOR_MODULE}.emit_event"):
                        sb = MagicMock()
                        sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError("insert failed")
                        mock_sb_getter.return_value = sb
                        MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        MockDS.create_document.return_value = None
                        from app.pipeline.generation.document_generator import DocumentGenerator

                        dg = DocumentGenerator()
                        job_id = await dg.start_job("report", "none", {}, {}, "u2")
                        assert job_id in dg._volatile_sessions

    @pytest.mark.asyncio
    async def test_calls_document_service_create(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                    with patch(f"{_GENERATOR_MODULE}.emit_event"):
                        MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        from app.pipeline.generation.document_generator import DocumentGenerator

                        dg = DocumentGenerator()
                        await dg.start_job("resume", "modern", {"name": "A"}, {}, "u3")
                        MockDS.create_document.assert_called_once()
                        args = MockDS.create_document.call_args[1]
                        assert args["doc_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        assert args["template"] == "modern"

    @pytest.mark.asyncio
    async def test_emits_queued_event(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                    with patch(f"{_GENERATOR_MODULE}.emit_event") as mock_emit:
                        MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        MockDS.create_document.return_value = None
                        from app.pipeline.generation.document_generator import DocumentGenerator

                        dg = DocumentGenerator()
                        await dg.start_job("thesis", "plain", {}, {}, "u4")
                        mock_emit.assert_called_once_with(
                            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                            "status_update",
                            {
                                "phase": "QUEUED",
                                "status": "PENDING",
                                "message": "Generation job queued.",
                                "progress": 0,
                                "stage": "queued",
                            },
                        )


class TestRunPipeline:
    """run_pipeline — the main orchestration method."""

    @pytest.fixture
    def mock_all(self):
        """Patch all external dependencies and return them."""
        with patch("app.db.repositories.base.get_supabase_client", return_value=None) as mock_sb:
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.PromptBuilder") as MockPB:
                    with patch(f"{_GENERATOR_MODULE}.ContentParser") as MockCP:
                        with patch(f"{_GENERATOR_MODULE}.Formatter") as MockFmt:
                            with patch(f"{_GENERATOR_MODULE}.Exporter") as MockExp:
                                with patch(f"{_GENERATOR_MODULE}.emit_event") as mock_emit:
                                    with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                                        with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                                            with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                                                MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                                                yield {
                                                    "get_supabase_client": mock_sb,
                                                    "DocumentService": MockDS,
                                                    "PromptBuilder": MockPB,
                                                    "ContentParser": MockCP,
                                                    "Formatter": MockFmt,
                                                    "Exporter": MockExp,
                                                    "emit_event": mock_emit,
                                                    "uuid": MockUuid,
                                                    "LLM_NVIDIA": mock_nvidia,
                                                    "LLM_DEEPSEEK": mock_deepseek,
                                                }

    @pytest.mark.asyncio
    async def test_full_happy_path(self, mock_all, tmp_path):
        output_path = tmp_path / "generated" / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.docx"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("docx content")

        mock_all["LLM_NVIDIA"].complete.return_value = '[{"type":"TITLE","content":"My Paper"}]'
        pb_instance = MagicMock()
        pb_instance.build.return_value = "Build the prompt"
        mock_all["PromptBuilder"].return_value = pb_instance

        parser_instance = MagicMock()
        parser_instance.parse.return_value = [
            {"type": "TITLE", "content": "My Paper", "level": 0},
            {"type": "HEADING_1", "content": "Introduction", "level": 1},
        ]
        mock_all["ContentParser"].return_value = parser_instance

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        mock_all["Formatter"].return_value = formatter_instance

        exporter_instance = MagicMock()
        exporter_instance.process.return_value = MagicMock()
        mock_all["Exporter"].return_value = exporter_instance

        with patch(f"{_GENERATOR_MODULE}.GENERATED_DIR", tmp_path / "generated"):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"] = {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "config_json": {
                    "doc_type": "academic_paper",
                    "template": "ieee",
                    "metadata": {"title": "My Paper"},
                    "options": {},
                },
            }
            await dg.run_pipeline("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

            updated = dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
            assert updated["status"] == "done"
            assert updated["progress"] == 100

    @pytest.mark.asyncio
    async def test_job_not_found_logs_and_returns(self, mock_all):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        await dg.run_pipeline("nonexistent")
        mock_all["PromptBuilder"].assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_during_pipeline_marks_failed(self, mock_all):
        mock_all["get_supabase_client"].return_value = None
        pb_instance = MagicMock()
        pb_instance.build.side_effect = ValueError("prompt build failure")
        mock_all["PromptBuilder"].return_value = pb_instance

        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"] = {
            "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "config_json": {
                "doc_type": "academic_paper",
                "template": "ieee",
                "metadata": {},
                "options": {},
            },
        }
        await dg.run_pipeline("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        updated = dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]
        assert updated["status"] == "failed"
        assert "prompt build failure" in str(updated["config_json"].get("error", ""))

    @pytest.mark.asyncio
    async def test_compute_hash_failure_does_not_break_pipeline(self, mock_all, tmp_path):
        gen_dir = tmp_path / "gen"
        gen_dir.mkdir(parents=True)
        output_path = gen_dir / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.docx"
        output_path.write_text("some bytes")

        mock_all["LLM_NVIDIA"].complete.return_value = '[{"type":"TITLE","content":"T"}]'
        pb_instance = MagicMock()
        pb_instance.build.return_value = "prompt"
        mock_all["PromptBuilder"].return_value = pb_instance
        parser_instance = MagicMock()
        parser_instance.parse.return_value = [{"type": "TITLE", "content": "T", "level": 0}]
        mock_all["ContentParser"].return_value = parser_instance
        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        mock_all["Formatter"].return_value = formatter_instance
        exporter_instance = MagicMock()
        exporter_instance.process.return_value = MagicMock()
        mock_all["Exporter"].return_value = exporter_instance

        with patch(f"{_GENERATOR_MODULE}.DocumentGenerator._compute_sha256", side_effect=OSError("no hash")):
            with patch(f"{_GENERATOR_MODULE}.GENERATED_DIR", tmp_path / "gen"):
                from app.pipeline.generation.document_generator import DocumentGenerator

                dg = DocumentGenerator()
                dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"] = {
                    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "config_json": {"doc_type": "paper", "template": "t", "metadata": {}, "options": {}},
                }
                await dg.run_pipeline("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
                assert dg._volatile_sessions["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]["status"] == "done"


class TestInternalUpdate:
    """_update — internal status update with emissions."""

    def test_done_status(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
            DocumentService=MagicMock(),
            emit_event=MagicMock(),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["u1"] = {"id": "u1", "config_json": {}}
            dg._update("u1", "done", 100, "Complete", output_path="/p/docx")
            assert dg._volatile_sessions["u1"]["config_json"]["status"] == "done"
            assert dg._volatile_sessions["u1"]["config_json"]["output_path"] == "/p/docx"

    def test_error_status(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
            DocumentService=MagicMock(),
            emit_event=MagicMock(),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["u2"] = {"id": "u2", "config_json": {}}
            dg._update("u2", "error", 0, "Something broke", error="critical failure")
            assert dg._volatile_sessions["u2"]["config_json"]["status"] == "failed"
            assert dg._volatile_sessions["u2"]["config_json"]["error"] == "critical failure"

    def test_queued_stage_maps_to_pending(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
            DocumentService=MagicMock(),
            emit_event=MagicMock(),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["u3"] = {"id": "u3", "config_json": {}}
            dg._update("u3", "queued", 0, "Waiting")
            assert dg._volatile_sessions["u3"]["config_json"]["status"] == "pending"

    def test_calls_document_service_update(self):
        ds_mock = MagicMock()
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
            DocumentService=ds_mock,
            emit_event=MagicMock(),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["u4"] = {"id": "u4", "config_json": {}}
            dg._update("u4", "formatting", 75, "Formatting...")
            ds_mock.update_document.assert_called_once()
            assert ds_mock.upsert_processing_status.called


class TestEmit:
    """_emit — SSE event emission (fire-and-forget)."""

    def test_emits_event(self):
        with patch(f"{_GENERATOR_MODULE}.emit_event") as mock_emit:
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._emit("j1", phase="TEST", status="OK")
            mock_emit.assert_called_once_with("j1", "status_update", {"phase": "TEST", "status": "OK"})

    def test_emission_exception_caught(self):
        with patch(f"{_GENERATOR_MODULE}.emit_event", side_effect=RuntimeError("SSE down")):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            # should not raise
            dg._emit("j2", phase="X")


class TestLlmGenerate:
    """_llm_generate — fallback tiers."""

    @pytest.mark.asyncio
    async def test_nvidia_success(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                mock_nvidia.complete.return_value = "NVIDIA response text"
                dg = DocumentGenerator()
                result = await dg._llm_generate("prompt", "j1")
                assert result == "NVIDIA response text"

    @pytest.mark.asyncio
    async def test_nvidia_empty_falls_to_deepseek(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_nvidia.complete.return_value = ""
                    mock_deepseek.complete.return_value = "DeepSeek response"
                    dg = DocumentGenerator()
                    result = await dg._llm_generate("prompt", "j1")
                    assert result == "DeepSeek response"

    @pytest.mark.asyncio
    async def test_nvidia_whitespace_falls_to_deepseek(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_nvidia.complete.return_value = "   "
                    mock_deepseek.complete.return_value = "DeepSeek actual"
                    dg = DocumentGenerator()
                    result = await dg._llm_generate("prompt", "j1")
                    assert result == "DeepSeek actual"

    @pytest.mark.asyncio
    async def test_both_llms_fail_falls_to_rule_skeleton(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_nvidia.complete.side_effect = RuntimeError("NVIDIA down")
                    mock_deepseek.complete.side_effect = RuntimeError("DeepSeek down")
                    dg = DocumentGenerator()
                    dg._volatile_sessions["j1"] = {
                        "id": "j1",
                        "config_json": {"doc_type": "academic_paper", "metadata": {"title": "Fallback Title"}},
                    }
                    result = await dg._llm_generate("prompt", "j1")
                    blocks = json.loads(result)
                    assert blocks[0]["type"] == "TITLE"
                    assert "Fallback Title" in blocks[0]["content"]

    @pytest.mark.asyncio
    async def test_full_fallback_resume_type(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_nvidia.complete.return_value = None
                    mock_deepseek.complete.side_effect = RuntimeError("fail")
                    dg = DocumentGenerator()
                    dg._volatile_sessions["j2"] = {
                        "id": "j2",
                        "config_json": {"doc_type": "resume", "metadata": {"name": "Jane"}},
                    }
                    result = await dg._llm_generate("prompt", "j2")
                    blocks = json.loads(result)
                    assert any(b["type"] == "HEADING_1" and "Professional Summary" in b["content"] for b in blocks)

    @pytest.mark.asyncio
    async def test_default_metadata_fallback_in_rule_based(self):
        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(return_value=None),
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            with patch("app.services.llm_service.LLM_NVIDIA") as mock_nvidia:
                with patch("app.services.llm_service.LLM_DEEPSEEK") as mock_deepseek:
                    mock_nvidia.complete.side_effect = RuntimeError("x")
                    mock_deepseek.complete.side_effect = RuntimeError("y")
                    dg = DocumentGenerator()
                    dg._volatile_sessions["j3"] = {
                        "id": "j3",
                        "config_json": {"doc_type": "academic_paper", "metadata": {}},
                    }
                    result = await dg._llm_generate("prompt", "j3")
                    blocks = json.loads(result)
                    assert blocks[0]["content"] == "Document Title"  # fallback title


class TestRuleBasedSkeleton:
    """_rule_based_skeleton static method."""

    def test_academic_paper_contains_expected_sections(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("academic_paper", {"title": "My Research"})
        blocks = json.loads(result)
        types = [b["type"] for b in blocks]
        assert "TITLE" in types
        assert "ABSTRACT" in types
        assert "HEADING_1" in types
        assert blocks[0]["content"] == "My Research"

    def test_resume_contains_expected_sections(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("resume", {"name": "Alice", "summary": "Expert Python dev."})
        blocks = json.loads(result)
        assert blocks[0]["type"] == "TITLE"
        assert blocks[0]["content"] == "Alice"
        assert any("Professional Summary" in b.get("content", "") for b in blocks)

    def test_unknown_type_falls_to_academic_paper(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("blog_post", {"title": "Blog"})
        blocks = json.loads(result)
        assert blocks[0]["type"] == "TITLE"
        assert "ABSTRACT" in [b["type"] for b in blocks]

    def test_title_uses_name_fallback(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("academic_paper", {"name": "Fallback Name"})
        blocks = json.loads(result)
        assert "Fallback Name" in blocks[0]["content"]

    def test_abstract_from_metadata(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton(
            "academic_paper", {"title": "X", "abstract": "Custom abstract."}
        )
        blocks = json.loads(result)
        abstract_blocks = [b for b in blocks if b["type"] == "ABSTRACT"]
        assert len(abstract_blocks) == 1
        assert "Custom abstract." in abstract_blocks[0]["content"]


class TestFormatAndExport:
    """_format_and_export — build PipelineDocument, format, export."""

    @pytest.mark.asyncio
    async def test_happy_path(self, tmp_path):
        output_dir = tmp_path / "generated"
        output_dir.mkdir()
        docx_path = output_dir / "job-output.docx"
        docx_path.write_text("fake docx")

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        exporter_instance = MagicMock()
        exporter_instance.process.return_value = MagicMock()

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            Exporter=MagicMock(return_value=exporter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            raw_blocks = [
                {"type": "TITLE", "content": "  My Title  ", "level": 0},
                {"type": "BODY", "content": "Body text.", "level": 0},
            ]
            result = await dg._format_and_export(
                raw_blocks=raw_blocks,
                template="ieee",
                job_id="job-output",
                metadata={"title": "My Title", "authors": ["Jane"], "abstract": "Abs.", "keywords": ["KW"]},
                doc_type="academic_paper",
            )
            assert result == docx_path.resolve()

    @pytest.mark.asyncio
    async def test_empty_content_blocks_skipped(self, tmp_path):
        output_dir = tmp_path / "gen2"
        output_dir.mkdir()
        docx_path = output_dir / "skipped.docx"
        docx_path.write_text("content")

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        exporter_instance = MagicMock()

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            Exporter=MagicMock(return_value=exporter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            raw_blocks = [
                {"type": "BODY", "content": "", "level": 0},
                {"type": "BODY", "content": "   ", "level": 0},
                {"type": "TITLE", "content": "Real", "level": 0},
            ]
            result = await dg._format_and_export(
                raw_blocks=raw_blocks,
                template="plain",
                job_id="skipped",
                metadata={},
                doc_type="paper",
            )
            assert result == docx_path.resolve()

    @pytest.mark.asyncio
    async def test_raises_when_no_generated_doc(self, tmp_path):
        output_dir = tmp_path / "gen3"
        output_dir.mkdir()

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=None)

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            with pytest.raises(RuntimeError, match="Formatting failed"):
                await dg._format_and_export(
                    raw_blocks=[{"type": "TITLE", "content": "X", "level": 0}],
                    template="t",
                    job_id="fail",
                    metadata={},
                    doc_type="paper",
                )

    @pytest.mark.asyncio
    async def test_raises_when_output_not_found(self, tmp_path):
        output_dir = tmp_path / "gen4"
        output_dir.mkdir()

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        exporter_instance = MagicMock()

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            Exporter=MagicMock(return_value=exporter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            with pytest.raises(RuntimeError, match="Export failed"):
                await dg._format_and_export(
                    raw_blocks=[{"type": "TITLE", "content": "X", "level": 0}],
                    template="t",
                    job_id="missing-file",
                    metadata={},
                    doc_type="paper",
                )

    @pytest.mark.asyncio
    async def test_preserves_block_level(self, tmp_path):
        output_dir = tmp_path / "gen5"
        output_dir.mkdir()
        docx_path = output_dir / "levels.docx"
        docx_path.write_text("data")

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        exporter_instance = MagicMock()
        exporter_instance.process.return_value = MagicMock()

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            Exporter=MagicMock(return_value=exporter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            await dg._format_and_export(
                raw_blocks=[
                    {"type": "HEADING_1", "content": "H1", "level": 1},
                    {"type": "HEADING_2", "content": "H2", "level": 2},
                    {"type": "BODY", "content": "Text", "level": None},
                ],
                template="t",
                job_id="levels",
                metadata={},
                doc_type="paper",
            )
            # formatter received a PipelineDocument with blocks
            call_doc = formatter_instance.process.call_args[0][0]
            levels = [b.level for b in call_doc.blocks]
            assert levels == [1, 2, None]


class TestExtractOutline:
    """_extract_outline static method."""

    def test_extracts_headings_and_title_abstract(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            _fake_block("TITLE", "My Paper"),
            _fake_block("ABSTRACT", "Abstract text"),
            _fake_block("HEADING_1", "Introduction"),
            _fake_block("BODY", "Some text"),
            _fake_block("HEADING_2", "Methodology"),
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == ["My Paper", "Abstract text", "Introduction", "Methodology"]

    def test_deduplicates_case_insensitively(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            _fake_block("HEADING_1", "Introduction"),
            _fake_block("HEADING_1", "INTRODUCTION"),
            _fake_block("HEADING_1", "introduction"),
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == ["Introduction"]

    def test_limited_to_50(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [_fake_block("HEADING_1", f"Section {i}") for i in range(100)]
        outline = DocumentGenerator._extract_outline(blocks)
        assert len(outline) == 50

    def test_empty_when_no_headings(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [_fake_block("BODY", "Just text"), _fake_block("BULLET", "Item")]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == []

    def test_strips_content_whitespace(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [_fake_block("HEADING_1", "  Spaced Out  ")]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == ["Spaced Out"]

    def test_heading_types_included(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            _fake_block("HEADING_1", "H1"),
            _fake_block("HEADING_2", "H2"),
            _fake_block("HEADING_3", "H3"),
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == ["H1", "H2", "H3"]

    def test_non_heading_types_excluded(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            _fake_block("BULLET", "Item"),
            _fake_block("FIGURE_CAPTION", "Fig"),
            _fake_block("TABLE_CAPTION", "Tab"),
            _fake_block("REFERENCE_ENTRY", "Ref"),
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert outline == []


class TestComputeSha256:
    """_compute_sha256 static method."""

    def test_computes_correct_hash(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        f = tmp_path / "sample.bin"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert DocumentGenerator._compute_sha256(f) == expected

    def test_larger_file(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        f = tmp_path / "large.bin"
        data = b"x" * (2 * 1024 * 1024 + 13)  # > 2 chunks
        f.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert DocumentGenerator._compute_sha256(f) == expected

    def test_raises_on_missing_file(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        with pytest.raises(FileNotFoundError):
            DocumentGenerator._compute_sha256(Path("/nonexistent/path/file.bin"))


class TestGetGenerator:
    """get_generator — singleton factory."""

    def test_returns_document_generator_instance(self):
        from app.pipeline.generation.document_generator import get_generator

        instance = get_generator()
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert isinstance(instance, DocumentGenerator)

    def test_returns_same_instance(self):
        from app.pipeline.generation.document_generator import get_generator

        a = get_generator()
        b = get_generator()
        assert a is b


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_emit_swallows_exception(self):
        with patch(f"{_GENERATOR_MODULE}.emit_event", side_effect=Exception("SSE fail")):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._emit("e1", phase="X")  # no raise

    def test_normalize_very_long_string(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._normalize_status("  VERY_LONG_STATUS_STRING_THAT_IS_NOT_MAPPED  ")
        assert result == "processing"

    def test_session_record_progress_clamped_below_zero(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        dg = DocumentGenerator()
        session = {"id": "j", "status": "done", "progress": -50, "config_json": {}}
        result = dg._session_record_to_status(session)
        assert result["progress"] == 0

    def test_update_status_does_not_overwrite_unset_fields(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            dg._volatile_sessions["ec1"] = {
                "id": "ec1",
                "config_json": {"stage": "gen", "message": "Old msg", "error": None},
            }
            dg.update_status("ec1", status="processing", progress=50)
            assert dg._volatile_sessions["ec1"]["config_json"]["stage"] == "gen"  # unchanged
            assert dg._volatile_sessions["ec1"]["config_json"]["message"] == "Old msg"  # unchanged

    async def test_format_and_export_invalid_level_type(self, tmp_path):
        output_dir = tmp_path / "gen_ec"
        output_dir.mkdir()
        docx_path = output_dir / "ec_out.docx"
        docx_path.write_text("data")

        formatter_instance = MagicMock()
        formatter_instance.process.return_value = MagicMock(generated_doc=MagicMock())
        exporter_instance = MagicMock()
        exporter_instance.process.return_value = MagicMock()

        with patch.multiple(
            f"{_GENERATOR_MODULE}",
            get_supabase_client=MagicMock(),
            Formatter=MagicMock(return_value=formatter_instance),
            Exporter=MagicMock(return_value=exporter_instance),
            GENERATED_DIR=output_dir,
        ):
            from app.pipeline.generation.document_generator import DocumentGenerator

            dg = DocumentGenerator()
            await dg._format_and_export(
                raw_blocks=[
                    {"type": "HEADING_1", "content": "H", "level": "not-a-number"},
                    {"type": "BODY", "content": "Text", "level": 0},
                ],
                template="t",
                job_id="ec_out",
                metadata={},
                doc_type="paper",
            )
            call_doc = formatter_instance.process.call_args[0][0]
            assert call_doc.blocks[0].level is None

    def test_rule_based_skeleton_resume_with_empty_metadata(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("resume", {})
        blocks = json.loads(result)
        assert blocks[0]["content"] == "Document Title"

    def test_rule_based_skeleton_abstract_fallback(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("academic_paper", {"title": "T"})
        blocks = json.loads(result)
        abstract_blocks = [b for b in blocks if b["type"] == "ABSTRACT"]
        assert "Abstract placeholder" in abstract_blocks[0]["content"]

    @pytest.mark.asyncio
    async def test_start_job_user_id_none(self):
        with patch("app.db.repositories.base.get_supabase_client", return_value=None):
            with patch(f"{_GENERATOR_MODULE}.DocumentService") as MockDS:
                with patch(f"{_GENERATOR_MODULE}.uuid") as MockUuid:
                    with patch(f"{_GENERATOR_MODULE}.emit_event"):
                        MockUuid.uuid4.return_value = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        MockDS.create_document.return_value = None
                        from app.pipeline.generation.document_generator import DocumentGenerator

                        dg = DocumentGenerator()
                        job_id = await dg.start_job("paper", "t", {}, {}, user_id="")
                        assert job_id in dg._volatile_sessions
                        assert dg._volatile_sessions[job_id]["user_id"] is None
