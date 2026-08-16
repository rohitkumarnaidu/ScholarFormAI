from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestNormalizeStatus:
    def test_pending_to_pending(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("PENDING") == "pending"

    def test_processing_to_processing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("PROCESSING") == "processing"

    def test_completed_to_done(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("COMPLETED") == "done"

    def test_failed_to_failed(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("FAILED") == "failed"

    def test_cancelled_to_failed(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("CANCELLED") == "failed"

    def test_unknown_returns_processing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status("UNKNOWN") == "processing"

    def test_none_returns_processing(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert DocumentGenerator._normalize_status(None) == "processing"


class TestNowIso:
    def test_returns_string(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        assert isinstance(DocumentGenerator._now_iso(), str)

    def test_ends_with_z_or_has_plus(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        iso = DocumentGenerator._now_iso()
        assert "+" in iso or "Z" in iso or iso.endswith("00:00")


class TestRuleBasedSkeleton:
    def test_default_doc_type(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("paper", {"title": "Test"})
        assert "Test" in result
        assert "Introduction" in result

    def test_resume_doc_type(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("resume", {"title": "Resume"})
        assert "Professional Summary" in result
        assert "Experience" in result

    def test_fallback_title(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        result = DocumentGenerator._rule_based_skeleton("paper", {})
        assert "Document Title" in result


class TestExtractOutline:
    def test_extracts_headings_and_title(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            {"type": "TITLE", "content": "My Paper"},
            {"type": "ABSTRACT", "content": "Abstract text"},
            {"type": "HEADING_1", "content": "Introduction"},
            {"type": "BODY", "content": "Some body"},
            {"type": "HEADING_2", "content": "Subsection"},
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert "My Paper" in outline
        assert "Abstract text" in outline
        assert "Introduction" in outline
        assert "Subsection" in outline

    def test_deduplicates_sections(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [
            {"type": "HEADING_1", "content": "Intro"},
            {"type": "HEADING_1", "content": "Intro"},
        ]
        outline = DocumentGenerator._extract_outline(blocks)
        assert len(outline) == 1

    def test_caps_at_50(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [{"type": "HEADING_1", "content": f"S{i}"} for i in range(100)]
        outline = DocumentGenerator._extract_outline(blocks)
        assert len(outline) == 50

    def test_skips_empty_content(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        blocks = [{"type": "HEADING_1", "content": ""}]
        outline = DocumentGenerator._extract_outline(blocks)
        assert len(outline) == 0


class TestComputeSha256:
    def test_computes_hash(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        f = tmp_path / "test.txt"
        f.write_text("hello")
        digest = DocumentGenerator._compute_sha256(f)
        assert isinstance(digest, str)
        assert len(digest) == 64

    def test_different_files_different_hashes(self, tmp_path):
        from app.pipeline.generation.document_generator import DocumentGenerator

        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert DocumentGenerator._compute_sha256(f1) != DocumentGenerator._compute_sha256(f2)


class TestConstructor:
    def test_volatile_sessions_initialized(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        assert gen._volatile_sessions == {}


class TestDefaultSessionConfig:
    def test_returns_config_dict(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        config = gen._default_session_config(
            doc_type="paper", template="ieee", metadata={"title": "Test"}, options={}, user_id="u1"
        )
        assert config["doc_type"] == "paper"
        assert config["template"] == "ieee"
        assert config["stage"] == "queued"


class TestGetSession:
    def test_returns_none_when_not_found(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        result = gen.get_session("nonexistent")
        assert result is None

    def test_returns_volatile_session(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {"id": "job1", "config_json": {"status": "pending"}}
        result = gen.get_session("job1")
        assert result["id"] == "job1"


class TestUpdateStatus:
    def test_updates_volatile_sessions(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {"id": "job1", "config_json": {}}
        gen.update_status("job1", status="processing", progress=50, stage="writing")
        assert gen._volatile_sessions["job1"]["status"] == "processing"
        assert gen._volatile_sessions["job1"]["progress"] == 50

    def test_clamps_progress(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {"id": "job1", "config_json": {}}
        gen.update_status("job1", status="done", progress=150)
        assert gen._volatile_sessions["job1"]["progress"] == 100

    def test_negative_progress_clamped(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {"id": "job1", "config_json": {}}
        gen.update_status("job1", status="pending", progress=-10)
        assert gen._volatile_sessions["job1"]["progress"] == 0


class TestGetStatus:
    @patch("app.pipeline.generation.document_generator.DocumentService")
    def test_uses_session_record(self, mock_ds):
        mock_ds.get_document_result.return_value = None
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {
            "id": "job1",
            "config_json": {"status": "done", "progress": 100, "stage": "done", "message": "OK"},
            "status": "done",
            "progress": 100,
        }
        status = gen.get_status("job1")
        assert status["status"] == "done"

    @patch("app.pipeline.generation.document_generator.DocumentService")
    def test_raises_on_not_found(self, mock_ds):
        mock_ds.get_document.return_value = None
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        with pytest.raises(KeyError):
            gen.get_status("nonexistent")


class TestStartJob:
    @patch("app.pipeline.generation.document_generator.DocumentService")
    @patch("app.pipeline.generation.document_generator.get_supabase_client")
    def test_returns_job_id(self, mock_get_sb, mock_ds):
        mock_ds.create_document.return_value = MagicMock()
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_get_sb.return_value = mock_sb
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        import asyncio

        job_id = asyncio.run(gen.start_job("paper", "ieee", {}, {}, "u1"))
        assert job_id is not None
        assert isinstance(job_id, str)


class TestRunPipeline:
    @patch("app.pipeline.generation.document_generator.DocumentGenerator._update")
    @patch("app.pipeline.generation.document_generator.DocumentGenerator._format_and_export")
    @patch("app.pipeline.generation.document_generator.ContentParser")
    @patch("app.pipeline.generation.document_generator.PromptBuilder")
    @patch("app.pipeline.generation.document_generator.DocumentService")
    def test_happy_path(self, mock_ds, mock_pb, mock_cp, mock_fae, mock_upd):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {
            "id": "job1",
            "config_json": {"doc_type": "paper", "template": "ieee", "metadata": {}, "options": {}},
        }
        mock_pb.return_value.build.return_value = "prompt"
        mock_cp.return_value.parse.return_value = [{"type": "BODY", "content": "Hello"}]
        mock_fae.return_value = Path("out.docx")

        gen.run_pipeline("job1")
        assert True  # no exception

    @patch("app.pipeline.generation.document_generator.DocumentGenerator._update")
    @patch("app.pipeline.generation.document_generator.DocumentGenerator._format_and_export")
    @patch("app.pipeline.generation.document_generator.ContentParser")
    @patch("app.pipeline.generation.document_generator.PromptBuilder")
    def test_error_path(self, mock_pb, mock_cp, mock_fae, mock_upd):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {
            "id": "job1",
            "config_json": {"doc_type": "paper", "template": "ieee", "metadata": {}, "options": {}},
        }
        mock_pb.return_value.build.side_effect = Exception("Build failed")

        gen.run_pipeline("job1")
        assert True  # exception caught internally


class TestGetDownloadPath:
    @patch("app.pipeline.generation.document_generator.DocumentService")
    def test_returns_none_when_not_found(self, mock_ds):
        mock_ds.get_document.return_value = None
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        assert gen.get_download_path("nonexistent") is None

    def test_returns_path_when_done(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        gen._volatile_sessions["job1"] = {
            "id": "job1",
            "config_json": {"status": "done", "output_path": "C:\\out.docx", "stage": "done", "message": ""},
            "status": "done",
            "progress": 100,
        }
        result = gen.get_download_path("job1")
        assert result is not None
        assert "out.docx" in str(result)


class TestSessionRecordToStatus:
    def test_returns_correct_keys(self):
        from app.pipeline.generation.document_generator import DocumentGenerator

        gen = DocumentGenerator()
        session = {
            "id": "job1",
            "config_json": {"status": "done", "progress": 100, "stage": "done", "message": "OK"},
            "status": "done",
            "progress": 100,
        }
        status = gen._session_record_to_status(session)
        assert status["job_id"] == "job1"
        assert status["status"] == "done"
        assert status["progress"] == 100
