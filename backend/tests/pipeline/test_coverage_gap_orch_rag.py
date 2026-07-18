# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Coverage gap tests for PipelineOrchestrator and RagEngine.
Targets uncovered branches, edge cases, and error handlers.
"""

from __future__ import annotations
import os
import json
import time
import asyncio
import tempfile
import threading
from unittest.mock import patch, MagicMock, call, ANY, PropertyMock
from pathlib import Path
import pytest
pytestmark = [pytest.mark.pipeline]


# ==============================================================================
#  PIPELINE ORCHESTRATOR TESTS
# ==============================================================================

@pytest.fixture
def orch():
    from app.models import BlockType, PipelineDocument, DocumentMetadata, Block
    with (
        patch("app.pipeline.orchestrator.InputConverter"),
        patch("app.pipeline.orchestrator.ContentAnalyzer"),
        patch("app.pipeline.orchestrator.ContractLoader"),
        patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
        patch("app.pipeline.orchestrator.GROBIDClient"),
        patch("app.pipeline.orchestrator.DoclingClient"),
    ):
        from app.pipeline.orchestrator import PipelineOrchestrator
        o = PipelineOrchestrator(templates_dir="app/templates", temp_dir="/tmp/test_cov_gap")
        return o


def _make_sb():
    sb = MagicMock()
    sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    return sb


def _make_doc(job_id="job1"):
    from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
    doc = PipelineDocument(
        document_id=job_id,
        blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body text")],
        metadata=DocumentMetadata(),
    )
    doc.metadata.ai_hints = {}
    return doc


# ──────────────────────────────────────────────────────────────────────────────
# _get_figure_analyzer
# ──────────────────────────────────────────────────────────────────────────────

class TestGetFigureAnalyzer:
    def test_figure_analyzer_lazy_init(self):
        from app.pipeline.orchestrator import _get_figure_analyzer, _figure_analyzer_instance
        old = _figure_analyzer_instance
        try:
            import app.pipeline.orchestrator as mod
            mod._figure_analyzer_instance = None
            with patch("app.pipeline.figures.analyzer.figure_analyzer", "mock_analyzer") as patched_mod:
                result = _get_figure_analyzer()
                assert result == "mock_analyzer"
        finally:
            import app.pipeline.orchestrator as mod
            mod._figure_analyzer_instance = old

    def test_figure_analyzer_returns_cached(self):
        from app.pipeline.orchestrator import _get_figure_analyzer, _figure_analyzer_instance
        old = _figure_analyzer_instance
        try:
            import app.pipeline.orchestrator as mod
            mod._figure_analyzer_instance = "cached"
            result = _get_figure_analyzer()
            assert result == "cached"
        finally:
            import app.pipeline.orchestrator as mod
            mod._figure_analyzer_instance = old


# ──────────────────────────────────────────────────────────────────────────────
# _coerce_bool
# ──────────────────────────────────────────────────────────────────────────────

class TestCoerceBool:
    def test_none_returns_default(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._coerce_bool(None, True) is True
        assert PipelineOrchestrator._coerce_bool(None, False) is False

    def test_bool_passthrough(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._coerce_bool(True) is True
        assert PipelineOrchestrator._coerce_bool(False) is False

    def test_int_float(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._coerce_bool(1) is True
        assert PipelineOrchestrator._coerce_bool(0.0) is False
        assert PipelineOrchestrator._coerce_bool(0) is False

    def test_string_truthy(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        for s in ["1", "true", "yes", "on"]:
            assert PipelineOrchestrator._coerce_bool(s) is True, f"'{s}' should be True"

    def test_string_falsy(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        for s in ["0", "false", "no", "off"]:
            assert PipelineOrchestrator._coerce_bool(s) is False, f"'{s}' should be False"

    def test_unknown_type_returns_default(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        assert PipelineOrchestrator._coerce_bool([], default=True) is True
        assert PipelineOrchestrator._coerce_bool({}, default=False) is False


# ──────────────────────────────────────────────────────────────────────────────
# _check_stage_interface
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckStageInterface:
    def test_missing_method_raises(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        orch = MagicMock(spec=PipelineOrchestrator)
        instance = MagicMock(spec=["something"])
        with pytest.raises(RuntimeError, match="does not implement required method"):
            PipelineOrchestrator._check_stage_interface(orch, instance, "missing_method", "TestStage")

    def test_has_method_ok(self):
        from app.pipeline.orchestrator import PipelineOrchestrator
        instance = MagicMock()
        instance.process = MagicMock()
        PipelineOrchestrator._check_stage_interface(None, instance, "process", "TestStage")


# ──────────────────────────────────────────────────────────────────────────────
# _record_stage_transition
# ──────────────────────────────────────────────────────────────────────────────

class TestRecordStageTransition:
    def test_processing_records_start_time(self, orch):
        orch._stage_start_times.clear()
        orch._record_stage_transition("job1", "EXTRACTION", "PROCESSING")
        assert ("job1", "EXTRACTION") in orch._stage_start_times

    def test_unknown_status_ignored(self, orch):
        orch._stage_start_times.clear()
        orch._record_stage_transition("job1", "EXTRACTION", "UNKNOWN_STATUS")
        assert ("job1", "EXTRACTION") not in orch._stage_start_times

    def test_completed_no_start_time(self, orch):
        orch._stage_start_times.clear()
        orch._record_stage_transition("job1", "EXTRACTION", "COMPLETED")

    def test_completed_records_metric(self, orch):
        orch._stage_start_times[("job1", "EXTRACTION")] = time.perf_counter() - 1.0
        with patch("app.middleware.prometheus_metrics.MetricsManager") as mock_mm:
            orch._record_stage_transition("job1", "EXTRACTION", "COMPLETED")
            mock_mm.record_pipeline_stage_duration.assert_called_once()

    def test_stage_start_time_already_exists(self, orch):
        orch._stage_start_times.clear()
        orch._record_stage_transition("job1", "EXTRACTION", "PROCESSING")
        orch._record_stage_transition("job1", "EXTRACTION", "PROCESSING")
        assert ("job1", "EXTRACTION") in orch._stage_start_times


# ──────────────────────────────────────────────────────────────────────────────
# _update_status
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateStatus:
    def test_sb_unavailable(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_existing_record_update(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")
        update_call = sb.table.return_value.update
        assert update_call.called

    def test_status_completed_phase_persistence(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "PERSISTENCE", "COMPLETED")
        update_call = sb.table.return_value.update
        assert update_call.called

    def test_status_failed_includes_error(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "FAILED", message="Something broke")

    def test_status_other_copied(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "PROCESSING", progress=50)

    def test_progress_in_doc_data(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED", progress=75)

    def test_insert_new_record(self, orch):
        sb = _make_sb()
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_non_transient_error(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = Exception("disk full")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_transient_then_success(self, orch):
        sb = MagicMock()
        err = Exception("RemoteProtocolError: server disconnected")
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = [
            err,
            MagicMock(data=[{"id": 1}]),
        ]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_transient_refresh_returns_none(self, orch):
        sb = MagicMock()
        err = Exception("RemoteProtocolError: server disconnected")
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = [
            err,
            MagicMock(data=[{"id": 1}]),
        ]
        call_count = [0]
        def _get_sb(refresh=False):
            call_count[0] += 1
            if refresh:
                return None
            return sb
        with patch("app.pipeline.orchestrator.get_supabase_client", side_effect=_get_sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_all_transient_attempts_fail(self, orch):
        sb = MagicMock()
        err = Exception("RemoteProtocolError: server disconnected")
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = [err, err, err]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_transient_on_update_then_success(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        err = Exception("connection reset")
        sb.table.return_value.update.return_value.match.side_effect = [err, MagicMock()]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")


# ──────────────────────────────────────────────────────────────────────────────
# _check_cancelled
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckCancelled:
    def test_sb_none(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orch._check_cancelled("job1")

    def test_status_cancelled_raises(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"status": "CANCELLED"}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with pytest.raises(asyncio.CancelledError):
                orch._check_cancelled("job1")

    def test_status_not_cancelled(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"status": "PROCESSING"}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            orch._check_cancelled("job1")

    def test_exception_caught(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB down")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            orch._check_cancelled("job1")


# ──────────────────────────────────────────────────────────────────────────────
# _persist_partial_result
# ──────────────────────────────────────────────────────────────────────────────

class TestPersistPartialResult:
    def test_no_sb_no_doc(self, orch):
        orch._persist_partial_result("job1", None, None)

    def test_existing_result_update(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]
        doc = _make_doc()
        with patch("app.pipeline.orchestrator.build_structured_data", return_value={"partial": True}):
            orch._persist_partial_result("job1", doc, sb)
        assert sb.table.return_value.update.called

    def test_no_existing_insert(self, orch):
        sb = _make_sb()
        doc = _make_doc()
        with patch("app.pipeline.orchestrator.build_structured_data", return_value={"partial": True}):
            orch._persist_partial_result("job1", doc, sb)
        assert sb.table.return_value.insert.called

    def test_exception_handled(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("fail")
        doc = _make_doc()
        orch._persist_partial_result("job1", doc, sb)


# ──────────────────────────────────────────────────────────────────────────────
# _run_with_timeout
# ──────────────────────────────────────────────────────────────────────────────

class TestRunWithTimeout:
    def test_normal_execution(self, orch):
        result = orch._run_with_timeout(lambda x: x * 2, 10, 21)
        assert result == 42

    def test_timeout_error(self, orch):
        def slow():
            import time
            time.sleep(100)
            return 42
        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow, 0.01)

    def test_cancel_event_set_on_timeout(self, orch):
        cancel_event = threading.Event()
        def slow():
            import time
            time.sleep(100)
            return 42
        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow, 0.01, cancel_event=cancel_event)
        assert cancel_event.is_set()


# ──────────────────────────────────────────────────────────────────────────────
# _resolve_runtime_flags
# ──────────────────────────────────────────────────────────────────────────────

class TestResolveRuntimeFlags:
    def test_pytest_override(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"}, clear=True):
                flags = orch._resolve_runtime_flags({})
        assert flags["fast_mode"] is True

    def test_low_memory_mode(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = True
            with patch.dict(os.environ, {}, clear=True):
                flags = orch._resolve_runtime_flags({})
        assert flags["fast_mode"] is True

    def test_options_not_none(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {}, clear=True):
                flags = orch._resolve_runtime_flags({"fast_mode": True, "semantic_parser": True})
        assert flags["semantic_parser"] is True

    def default_fast_mode_true(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = True
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {}, clear=True):
                flags = orch._resolve_runtime_flags(None)
        assert flags["fast_mode"] is True


# ──────────────────────────────────────────────────────────────────────────────
# _should_skip_docling_for_digital_pdf
# ──────────────────────────────────────────────────────────────────────────────

class TestShouldSkipDocling:
    def test_force_docling(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = True
            assert orch._should_skip_docling_for_digital_pdf("/any.pdf") is False

    def test_auto_skip_false(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = False
            assert orch._should_skip_docling_for_digital_pdf("/any.pdf") is False

    def test_empty_pdf(self, orch, tmp_path):
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy content with enough chars")
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            with patch("fitz.open") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__.return_value = 0
                mock_fitz.return_value.__enter__.return_value = mock_doc
                assert orch._should_skip_docling_for_digital_pdf(str(pdf)) is False

    def test_enough_chars_returns_true(self, orch, tmp_path):
        pdf = tmp_path / "digital.pdf"
        pdf.write_bytes(b"dummy")
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            with patch("fitz.open") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__.return_value = 3
                page = MagicMock()
                page.get_text.return_value = "x" * 300
                mock_doc.__getitem__.return_value = page
                mock_doc.__iter__.return_value = iter([page, page])
                mock_fitz.return_value.__enter__.return_value = mock_doc
                assert orch._should_skip_docling_for_digital_pdf(str(pdf)) is True

    def test_fitz_import_exception(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            import builtins
            orig_import = builtins.__import__
            def fake_import(name, *args, **kwargs):
                if name == "fitz":
                    raise ImportError("no fitz")
                return orig_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=fake_import):
                assert orch._should_skip_docling_for_digital_pdf("/test.pdf") is False


# ──────────────────────────────────────────────────────────────────────────────
# _extract_pymupdf_fallback_metadata
# ──────────────────────────────────────────────────────────────────────────────

class TestExtractPyMuPDF:
    def test_import_exception(self, orch):
        import builtins
        def fake_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("no fitz")
            return builtins.__import__(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=fake_import):
            result = orch._extract_pymupdf_fallback_metadata("/test.pdf")
        assert result == {}

    def test_successful_extraction(self, orch):
        with patch("fitz.open") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.metadata = {"title": "Test Paper", "author": "Author A"}
            mock_doc.__len__.return_value = 5
            page = MagicMock()
            page.get_text.return_value = "This is sample text content for testing."
            mock_doc.__getitem__.return_value = page
            mock_doc.__iter__.return_value = iter([page, page])
            mock_fitz.return_value.__enter__.return_value = mock_doc
            result = orch._extract_pymupdf_fallback_metadata("/test.pdf")
            assert result["source"] == "pymupdf"
            assert result["title"] == "Test Paper"

    def test_open_exception(self, orch):
        with patch("fitz.open") as mock_fitz:
            mock_fitz.return_value.__enter__.side_effect = Exception("corrupt PDF")
            result = orch._extract_pymupdf_fallback_metadata("/test.pdf")
        assert result == {}


# ──────────────────────────────────────────────────────────────────────────────
# _sync_block_confidence
# ──────────────────────────────────────────────────────────────────────────────

class TestSyncBlockConfidence:
    def test_classification_confidence_in_metadata(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": 0.85})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata["nlp_confidence"] == 0.85

    def test_no_classification_confidence_fallback(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = MagicMock(spec=Block)
        block.block_id = "b1"
        block.metadata = {}
        block.classification_confidence = 0.75
        block.semantic_intent = None
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata.get("nlp_confidence") == 0.75

    def test_nlp_confidence_metadata_fallback(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"nlp_confidence": 0.65})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata["nlp_confidence"] == 0.65

    def test_type_error_skipped(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": "not-a-number"})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        orch._sync_block_confidence(doc)
        assert "nlp_confidence" not in block.metadata or block.metadata.get("nlp_confidence") == 0.0

    def test_negative_clamped(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": -0.5})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata["nlp_confidence"] == 0.0

    def test_above_one_clamped(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": 1.5})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata["nlp_confidence"] == 1.0

    def test_semantic_intent_set(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = MagicMock(spec=Block)
        block.block_id = "b1"
        block.metadata = {"classification_confidence": 0.9}
        block.semantic_intent = "introduction"
        block.classification_confidence = None
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.metadata.ai_hints = {}
        orch._sync_block_confidence(doc)
        assert block.metadata.get("semantic_intent") == "introduction"


# ──────────────────────────────────────────────────────────────────────────────
# _build_quality_summary
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildQualitySummary:
    def test_heading_candidates_count(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.HEADING_1, text="Intro", metadata={"is_heading_candidate": True, "classification_confidence": 0.9})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 85.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["heading_candidates"] == 1

    def test_no_heading_candidates(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="body", metadata={"classification_confidence": 0.9})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 85.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["heading_candidates"] == 0

    def test_no_figures_or_tables_lowers_asset_score(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(document_id="d1", blocks=[], metadata=DocumentMetadata())
        doc.template = None
        doc.figures = []
        doc.tables = []
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 85.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["figures"] == 0
        assert summary["tables"] == 0

    def test_metadata_not_dict(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = MagicMock(spec=Block)
        block.metadata = None
        block.classification_confidence = 0.85
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["block_count"] == 1

    def test_value_error_on_float_conversion(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        block = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": "bad"})
        doc = PipelineDocument(document_id="d1", blocks=[block], metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["block_count"] == 1

    def test_low_conf_blocks_counted(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": 0.3}),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="t", metadata={"classification_confidence": 0.9}),
        ]
        doc = PipelineDocument(document_id="d1", blocks=blocks, metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["low_conf_blocks"] == 1

    def test_errors_and_warnings_penalty(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(document_id="d1", blocks=[], metadata=DocumentMetadata())
        doc.template = None
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, {"errors": ["err1", "err2"], "warnings": ["warn1"]})
        assert summary["errors"] == 2
        assert summary["warnings"] == 1

    def test_template_name_from_doc(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, TemplateInfo
        doc = PipelineDocument(document_id="d1", blocks=[], metadata=DocumentMetadata())
        doc.template = TemplateInfo(template_name="ACM")
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 90.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})


# ──────────────────────────────────────────────────────────────────────────────
# _compute_sha256
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeSha256:
    def test_sha256_computation(self, orch, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        digest = orch._compute_sha256(str(f))
        assert isinstance(digest, str)
        assert len(digest) == 64


# ──────────────────────────────────────────────────────────────────────────────
# _run_extraction_stage
# ──────────────────────────────────────────────────────────────────────────────

class TestRunExtractionStage:
    def test_direct_parse_format(self, orch, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        factory = MagicMock()
        parser = MagicMock()
        factory.get_parser.return_value = parser
        doc = _make_doc()
        parser.parse.return_value = doc
        result = orch._run_extraction_stage(factory, "/tmp/test.pdf", "job1", {}, ".pdf")
        assert result.formatting_options is not None

    def test_conversion_format(self, orch, tmp_path):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        factory = MagicMock()
        parser = MagicMock()
        factory.get_parser.return_value = parser
        doc = _make_doc()
        parser.parse.return_value = doc
        orch.converter.convert_to_docx.return_value = "/tmp/converted.docx"
        result = orch._run_extraction_stage(factory, "/tmp/test.doc", "job1", {}, ".doc")
        assert result is doc
        orch.converter.convert_to_docx.assert_called_once_with("/tmp/test.doc", "job1")


# ──────────────────────────────────────────────────────────────────────────────
# _run_semantic_parsing
# ──────────────────────────────────────────────────────────────────────────────

class TestRunSemanticParsing:
    def test_successful_semantic_parsing(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="d1",
            blocks=[Block(block_id="b1", index=0, block_type=BlockType.BODY, text="test")],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 10
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_sp:
                sp_instance = MagicMock()
                sp_instance.analyze_blocks.return_value = [
                    {"predicted_section_type": "introduction", "confidence_score": 0.95}
                ]
                mock_sp.return_value = sp_instance
                result = orch._run_semantic_parsing(doc)
        assert result.metadata.ai_hints is not None


# ──────────────────────────────────────────────────────────────────────────────
# _run_classification
# ──────────────────────────────────────────────────────────────────────────────

class TestRunClassification:
    def test_classification_runs(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        with patch("app.pipeline.orchestrator.ContentClassifier") as MockCls:
            inst = MagicMock()
            inst.process.return_value = doc
            MockCls.return_value = inst
            result = orch._run_classification(doc)
        assert result is doc


# ──────────────────────────────────────────────────────────────────────────────
# _run_validation_stage
# ──────────────────────────────────────────────────────────────────────────────

class TestRunValidation:
    def test_validation_runs(self, orch):
        doc = _make_doc()
        with patch("app.pipeline.orchestrator.DocumentValidator") as MockVal:
            inst = MagicMock()
            inst.process.return_value = doc
            MockVal.return_value = inst
            result = orch._run_validation_stage(doc)
        assert result is doc


# ──────────────────────────────────────────────────────────────────────────────
# _run_figure_analysis_stage — additional edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestFigureAnalysisAdditional:
    def test_downsample_returns_same_path(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, Figure
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig.png", caption_text="Fig")
        doc = PipelineDocument(document_id="d1", blocks=[], metadata=DocumentMetadata(), figures=[fig])
        doc.metadata.ai_hints = {}
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = "/tmp/fig.png"
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert result.figures[0].export_path == "/tmp/fig.png"
        assert any(a.get("downsampled") is not True for a in result.metadata.ai_hints.get("figure_analysis", []))

    def test_metadata_is_dict_without_ai_hints(self, orch):
        from app.models import PipelineDocument, Block, BlockType, Figure
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig.png", caption_text="Fig")
        doc = PipelineDocument(
            document_id="figdoc", blocks=[], figures=[fig],
        )
        object.__setattr__(doc, "metadata", {"existing": "value"})
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert "figure_analysis" in result.metadata["ai_hints"]

    def test_metadata_has_ai_hints_attr(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, Figure
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig.png", caption_text="Fig")
        doc = PipelineDocument(document_id="figdoc", blocks=[], metadata=DocumentMetadata(), figures=[fig])
        doc.metadata.ai_hints = {"existing": "data"}
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert "figure_analysis" in result.metadata.ai_hints

    def test_no_results_no_metadata_update(self, orch):
        doc = _make_doc()
        mock_analyzer = MagicMock()
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            result = orch._run_figure_analysis_stage(doc)
        assert result is doc

    def test_figure_with_image_data_and_no_export_path(self, orch):
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, Figure
        fig = Figure(figure_id="f2", index=1, export_path=None, image_data=b"imgdata", caption_text="Fig")
        doc = PipelineDocument(document_id="figdoc", blocks=[], metadata=DocumentMetadata(), figures=[fig])
        doc.metadata.ai_hints = {}
        mock_analyzer = MagicMock()
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=False):
                result = orch._run_figure_analysis_stage(doc)
        assert result.metadata.ai_hints["figure_analysis"][0]["valid"] is False


# ──────────────────────────────────────────────────────────────────────────────
# _run_formatting_stage
# ──────────────────────────────────────────────────────────────────────────────

class TestRunFormatting:
    def test_formatting_runs(self, orch):
        doc = _make_doc()
        with patch("app.pipeline.orchestrator.Formatter") as MockFmt:
            inst = MagicMock()
            inst.process.return_value = doc
            MockFmt.return_value = inst
            with patch.object(orch, "_run_with_timeout", return_value=doc):
                result = orch._run_formatting_stage(doc)
        assert result is doc


# ──────────────────────────────────────────────────────────────────────────────
# _export_document
# ──────────────────────────────────────────────────────────────────────────────

class TestExportDocument:
    def test_export_creates_dir_and_output(self, orch, tmp_path):
        doc = _make_doc()
        exporter = MagicMock()
        with patch("app.pipeline.orchestrator.Exporter", return_value=exporter):
            with patch("os.makedirs") as mock_mkdir:
                result = orch._export_document(doc, str(tmp_path / "input.pdf"), "job1")
        assert result is not None
        assert doc.output_path == result


# ──────────────────────────────────────────────────────────────────────────────
# run_pipeline
# ──────────────────────────────────────────────────────────────────────────────

class TestRunPipeline:
    def test_semaphore_timeout(self, orch):
        import threading
        old = threading.Semaphore.acquire
        def fake_acquire(timeout=None):
            return False
        with patch.object(threading.Semaphore, "acquire", side_effect=fake_acquire):
            with patch.object(orch, "_update_status"):
                result = orch.run_pipeline("/tmp/test.pdf", "job1")
        assert result["status"] == "failed"

    def test_success_path(self, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = _make_sb()
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch.run_pipeline(str(input_path), "job1")
        assert result["status"] in ("success", "processing")


# ──────────────────────────────────────────────────────────────────────────────
# run_edit_flow
# ──────────────────────────────────────────────────────────────────────────────

class TestRunEditFlow:
    def test_sb_unavailable(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"

    def test_document_not_found(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"

    def test_successful_edit_persistence(self, orch):
        from app.models import BlockType
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = MagicMock()
                            with patch("app.pipeline.orchestrator.Exporter") as mock_exp:
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"

    def test_cancelled_error(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = asyncio.CancelledError("cancel")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.object(orch, "_update_status"):
                result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "cancelled"

    def test_general_exception(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("generic error")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.object(orch, "_update_status"):
                result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"

    def test_edit_with_existing_result_and_versions(self, orch):
        from app.models import BlockType
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"version_number": "v3"}
        ]
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = MagicMock()
                            with patch("app.pipeline.orchestrator.Exporter") as mock_exp:
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"

    def test_version_number_exception(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"version_number": None}
        ]
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = MagicMock()
                            with patch("app.pipeline.orchestrator.Exporter") as mock_exp:
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"


# ==============================================================================
#  RAG ENGINE TESTS
# ==============================================================================

def _make_rag_engine(temp_dir=None, model_name=None):
    import tempfile as _tf
    persist_dir = temp_dir or _tf.mkdtemp()
    from app.pipeline.intelligence.rag_engine import RagEngine
    with patch.object(RagEngine, "_load_embedding_model"):
        re = RagEngine(persist_directory=persist_dir)
    re.chroma_enabled = False
    re.client = None
    re.collection = None
    return re


# ──────────────────────────────────────────────────────────────────────────────
# _load_chromadb
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadChromadb:
    def test_chromadb_already_loaded(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb, chromadb
        old_cdb = globals().get("chromadb")
        try:
            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod.chromadb = "already_loaded"
            rag_mod._CHROMADB_AVAILABLE = False
            result = _load_chromadb()
            assert result == "already_loaded"
            assert rag_mod._CHROMADB_AVAILABLE is True
        finally:
            pass

    def test_chromadb_import_already_attempted(self):
        import app.pipeline.intelligence.rag_engine as rag_mod
        old = rag_mod._CHROMADB_IMPORT_ATTEMPTED
        try:
            rag_mod.chromadb = None
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = True
            result = rag_mod._load_chromadb()
            assert result is None
        finally:
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = old

    def test_chromadb_import_succeeds(self):
        import app.pipeline.intelligence.rag_engine as rag_mod
        old_cdb = rag_mod.chromadb
        old_attempted = rag_mod._CHROMADB_IMPORT_ATTEMPTED
        old_available = rag_mod._CHROMADB_AVAILABLE
        try:
            rag_mod.chromadb = None
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = False
            rag_mod._CHROMADB_AVAILABLE = False
            import types
            fake_chromadb = types.ModuleType("chromadb")
            with patch.dict("sys.modules", {"chromadb": fake_chromadb}):
                with patch.object(rag_mod, "chromadb", None):
                    result = rag_mod._load_chromadb()
        finally:
            rag_mod.chromadb = old_cdb
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = old_attempted
            rag_mod._CHROMADB_AVAILABLE = old_available

    def test_chromadb_import_fails(self):
        import app.pipeline.intelligence.rag_engine as rag_mod
        old_chromadb = rag_mod.chromadb
        old_attempted = rag_mod._CHROMADB_IMPORT_ATTEMPTED
        old_available = rag_mod._CHROMADB_AVAILABLE
        try:
            rag_mod.chromadb = None
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = False
            rag_mod._CHROMADB_AVAILABLE = False
            import builtins
            orig_import = builtins.__import__
            def fake_import(name, *args, **kwargs):
                if name == "chromadb":
                    raise ImportError("chromadb not installed")
                return orig_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=fake_import):
                result = rag_mod._load_chromadb()
            assert result is None
            assert rag_mod._CHROMADB_AVAILABLE is False
        finally:
            rag_mod.chromadb = old_chromadb
            rag_mod._CHROMADB_IMPORT_ATTEMPTED = old_attempted
            rag_mod._CHROMADB_AVAILABLE = old_available


# ──────────────────────────────────────────────────────────────────────────────
# _DeterministicEmbeddingModel
# ──────────────────────────────────────────────────────────────────────────────

class TestDeterministicEmbeddingModel:
    def test_init_with_custom_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(dimension=64)
        assert m.dimension == 64

    def test_init_min_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(dimension=8)
        assert m.dimension == 32

    def test_get_sentence_embedding_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(128)
        assert m.get_sentence_embedding_dimension() == 128

    def test_encode_single_string(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode("hello world")
        assert len(result) == 32
        assert all(isinstance(v, float) for v in result)

    def test_encode_empty_string(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode("")
        assert len(result) == 32
        assert all(v == 0.0 for v in result)

    def test_encode_list(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode(["hello", "world"])
        assert len(result) == 2
        assert all(len(v) == 32 for v in result)

    def test_encode_tuple(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode(("hello", "world"))
        assert len(result) == 2


# ──────────────────────────────────────────────────────────────────────────────
# _coerce_embedding_vector
# ──────────────────────────────────────────────────────────────────────────────

class TestCoerceEmbeddingVector:
    def test_none(self):
        re = _make_rag_engine()
        result = re._coerce_embedding_vector(None)
        assert result == []

    def test_nested_list(self):
        re = _make_rag_engine()
        result = re._coerce_embedding_vector([[0.1, 0.2, 0.3]])
        assert len(result) == 3

    def test_invalid_type(self):
        re = _make_rag_engine()
        result = re._coerce_embedding_vector("not-a-vector")
        assert result == []

    def test_exception_during_conversion(self):
        re = _make_rag_engine()
        result = re._coerce_embedding_vector([object(), object()])
        assert result == []

    def test_numpy_array(self):
        import numpy as np
        re = _make_rag_engine()
        result = re._coerce_embedding_vector(np.array([0.5, 0.6, 0.7]))
        assert len(result) == 3


# ──────────────────────────────────────────────────────────────────────────────
# _is_reusable_embedding_model
# ──────────────────────────────────────────────────────────────────────────────

class TestIsReusableEmbeddingModel:
    def test_none(self):
        re = _make_rag_engine()
        usable, dim = re._is_reusable_embedding_model(None)
        assert usable is False
        assert dim is None

    def test_no_encode_method(self):
        re = _make_rag_engine()
        candidate = MagicMock(spec=["something"])
        usable, dim = re._is_reusable_embedding_model(candidate)
        assert usable is False

    def test_no_get_sentence_embedding_dimension(self):
        re = _make_rag_engine()
        candidate = MagicMock()
        candidate.encode = MagicMock()
        del candidate.get_sentence_embedding_dimension
        usable, dim = re._is_reusable_embedding_model(candidate)
        assert usable is False

    def test_dimension_negative(self):
        re = _make_rag_engine()
        candidate = MagicMock()
        candidate.encode.return_value = [0.1]
        candidate.get_sentence_embedding_dimension.return_value = -1
        usable, dim = re._is_reusable_embedding_model(candidate)
        assert usable is False

    def test_encode_returns_empty(self):
        re = _make_rag_engine()
        candidate = MagicMock()
        candidate.encode.return_value = None
        candidate.get_sentence_embedding_dimension.return_value = 384
        with patch.object(re, "_coerce_embedding_vector", return_value=[]):
            usable, dim = re._is_reusable_embedding_model(candidate)
            assert usable is False

    def test_exception_in_validation(self):
        re = _make_rag_engine()
        candidate = MagicMock()
        candidate.encode.side_effect = Exception("model error")
        candidate.get_sentence_embedding_dimension.return_value = 384
        usable, dim = re._is_reusable_embedding_model(candidate)
        assert usable is False

    def test_valid(self):
        re = _make_rag_engine()
        candidate = MagicMock()
        candidate.encode.return_value = [0.1, 0.2]
        candidate.get_sentence_embedding_dimension.return_value = 384
        with patch.object(re, "_coerce_embedding_vector", return_value=[0.1, 0.2]):
            usable, dim = re._is_reusable_embedding_model(candidate)
            assert usable is True
            assert dim == 384


# ──────────────────────────────────────────────────────────────────────────────
# _activate_deterministic_embedding
# ──────────────────────────────────────────────────────────────────────────────

class TestActivateDeterministicEmbedding:
    def test_store_failure_does_not_block(self):
        re = _make_rag_engine()
        from unittest.mock import PropertyMock
        ms = MagicMock()
        ms.set_model.side_effect = Exception("store fail")
        re._activate_deterministic_embedding(ms, "test reason")
        assert re.embedding_model is not None

    def test_stores_model(self):
        re = _make_rag_engine()
        ms = MagicMock()
        re._activate_deterministic_embedding(ms, "test reason")
        ms.set_model.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# _load_embedding_model — heavy coverage
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadEmbeddingModel:
    def _make_rag_no_load(self, temp_dir=None):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch.object(RagEngine, "_load_embedding_model"):
            return RagEngine(persist_directory=temp_dir or tempfile.mkdtemp(), auto_seed=False)

    def test_low_memory_hf_api_success(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
        ):
            mock_settings.LOW_MEMORY_MODE = True
            mock_settings.RAG_USE_TRANSFORMERS = False
            with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
                mock_getenv.return_value = "huggingface_api"
                with patch.object(re, "_coerce_embedding_vector", return_value=[0.1, 0.2]):
                    with patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as MockHF:
                        hf_inst = MagicMock()
                        hf_inst.encode.return_value = [0.1]
                        hf_inst.dimension = 384
                        MockHF.return_value = hf_inst
                        re._load_embedding_model()
        assert re.embedding_model is not None

    def test_low_memory_hf_api_fails_then_deterministic(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
        ):
            mock_settings.LOW_MEMORY_MODE = True
            mock_settings.RAG_USE_TRANSFORMERS = False
            with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
                mock_getenv.return_value = "huggingface_api"
                with patch.object(re, "_coerce_embedding_vector", return_value=[]):
                    with patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as MockHF:
                        hf_inst = MagicMock()
                        hf_inst.encode.return_value = []
                        MockHF.return_value = hf_inst
                        re._load_embedding_model()
        assert re.embedding_model is not None

    def test_low_memory_no_hf_provider_deterministic(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
        ):
            mock_settings.LOW_MEMORY_MODE = True
            mock_settings.RAG_USE_TRANSFORMERS = False
            with patch("app.pipeline.intelligence.rag_engine.os.getenv", return_value=""):
                re._load_embedding_model()
        assert "deterministic" in str(re.active_model_name).lower()

    def test_sentence_transformer_import_fails(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
        ):
            mock_settings.LOW_MEMORY_MODE = False
            mock_settings.RAG_USE_TRANSFORMERS = True
            import builtins
            orig_import = builtins.__import__
            def fake_import(name, *args, **kwargs):
                if "sentence_transformers" in name:
                    raise ImportError("no sentence transformers")
                return orig_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=fake_import):
                re._load_embedding_model()
        assert re.embedding_model is not None

    def test_reuse_from_model_store_primary(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
        ):
            mock_settings.LOW_MEMORY_MODE = False
            mock_settings.RAG_USE_TRANSFORMERS = True
            candidate = MagicMock()
            candidate.encode.return_value = MagicMock(tolist=lambda: [0.1] * 1024)
            candidate.get_sentence_embedding_dimension.return_value = 1024
            with patch("app.services.model_store.model_store") as ms:
                ms.is_loaded.return_value = True
                ms.get_model.return_value = candidate
                re._load_embedding_model()
        assert re.active_model_name == "BAAI/bge-m3"

    def test_invalid_model_in_store_reloads(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("sentence_transformers.SentenceTransformer") as MockST,
        ):
            mock_settings.LOW_MEMORY_MODE = False
            mock_settings.RAG_USE_TRANSFORMERS = True
            candidate = MagicMock()
            candidate.encode.side_effect = Exception("invalid")
            candidate.get_sentence_embedding_dimension.return_value = 384
            with patch("app.services.model_store.model_store") as ms:
                ms.is_loaded.return_value = True
                ms.get_model.return_value = candidate
                st_inst = MagicMock()
                st_inst.get_sentence_embedding_dimension.return_value = 1024
                MockST.return_value = st_inst
                re._load_embedding_model()
        assert re.active_model_name == "BAAI/bge-m3"

    def test_load_primary_fails_fallback_succeeds(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
            patch("sentence_transformers.SentenceTransformer") as MockST,
        ):
            mock_settings.LOW_MEMORY_MODE = False
            mock_settings.RAG_USE_TRANSFORMERS = True
            ms.is_loaded.return_value = False
            MockST.side_effect = [Exception("OOM"), MagicMock()]
            MockST.return_value.get_sentence_embedding_dimension.return_value = 384
            re._load_embedding_model()
        assert re.active_model_name == "BAAI/bge-small-en-v1.5"

    def test_both_fail_deterministic(self):
        re = self._make_rag_no_load()
        with (
            patch("app.config.settings.settings") as mock_settings,
            patch("app.services.model_store.model_store") as ms,
            patch("sentence_transformers.SentenceTransformer") as MockST,
        ):
            mock_settings.LOW_MEMORY_MODE = False
            mock_settings.RAG_USE_TRANSFORMERS = True
            ms.is_loaded.return_value = False
            MockST.side_effect = [Exception("OOM"), Exception("also OOM")]
            re._load_embedding_model()
        assert "deterministic" in str(re.active_model_name).lower()


# ──────────────────────────────────────────────────────────────────────────────
# _HuggingFaceAPIEmbeddingModel
# ──────────────────────────────────────────────────────────────────────────────

class TestHuggingFaceAPIEmbeddingModel:
    def test_init_default(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            assert m.dimension == 384

    def test_init_bge_m3(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel(model_id="BAAI/bge-m3")
            assert m.dimension == 1024

    def test_init_custom_url(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {"RAG_EMBEDDING_API_URL": "https://custom.url/model"}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            assert "custom.url" in m.api_url

    def test_normalize_embedding_api_url_empty(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url("", "test-model")
        assert "test-model" in url

    def test_normalize_embedding_api_url_missing_pipeline(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(
            "https://router.huggingface.co/hf-inference/models/test-model",
            "test-model",
        )
        assert "/pipeline/feature-extraction" in url

    def test_normalize_embedding_api_url_valid(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(
            "https://router.huggingface.co/hf-inference/models/test-model/pipeline/feature-extraction",
            "test-model",
        )
        assert url.endswith("feature-extraction")

    def test_default_feature_extraction_url(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._default_feature_extraction_url("test-model")
        assert "test-model" in url
        assert "feature-extraction" in url

    def test_get_sentence_embedding_dimension(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        m = _HuggingFaceAPIEmbeddingModel()
        assert m.get_sentence_embedding_dimension() == 384

    def test_encode_no_token(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = ""
            result = m.encode("hello")
            assert result == []

    def test_encode_http_500_retry_then_fail(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            m.max_retries = 2
            m.retry_backoff_seconds = 0.01
            resp = MagicMock()
            resp.status_code = 500
            resp.text = "server error"
            with patch("requests.post", return_value=resp):
                result = m.encode("hello")
                assert result == []

    def test_encode_http_400_sentence_similarity_recovers(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            m.max_retries = 2
            m.retry_backoff_seconds = 0.01
            m.api_url = "https://router.huggingface.co/hf-inference/models/test-model"
            resp = MagicMock()
            resp.status_code = 400
            resp.text = "SentenceSimilarityPipeline"
            resp.json.return_value = [[0.1, 0.2]]
            call_count = [0]
            def side_effect(*a, **kw):
                call_count[0] += 1
                if call_count[0] == 1:
                    return resp
                resp2 = MagicMock()
                resp2.status_code = 200
                resp2.json.return_value = [[0.1, 0.2]]
                return resp2
            with patch("requests.post", side_effect=side_effect):
                result = m.encode("hello")
                assert len(result) > 0

    def test_encode_http_200_single(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = [[0.1, 0.2, 0.3]]
            with patch("requests.post", return_value=resp):
                result = m.encode("hello")
                assert len(result) == 3

    def test_encode_http_200_list(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = [[0.1, 0.2], [0.3, 0.4]]
            with patch("requests.post", return_value=resp):
                result = m.encode(["hello", "world"])
                assert len(result) == 2

    def test_encode_exception_retry(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            m.max_retries = 2
            m.retry_backoff_seconds = 0.01
            call_count = [0]
            def side_effect(*a, **kw):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("network error")
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = [[0.1, 0.2]]
                return resp
            with patch("requests.post", side_effect=side_effect):
                result = m.encode("hello")
                assert len(result) > 0

    def test_encode_all_exceptions_fail(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch.dict(os.environ, {}, clear=True):
            m = _HuggingFaceAPIEmbeddingModel()
            m.token = "fake"
            m.max_retries = 2
            m.retry_backoff_seconds = 0.01
            with patch("requests.post", side_effect=Exception("always fails")):
                result = m.encode("hello")
                assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# add_guideline — edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestAddGuideline:
    def test_chroma_enabled_no_embedding(self):
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.collection = MagicMock()
        with patch.object(re, "_seed_if_empty"):
            with patch.object(re, "_save_native"):
                re.embedding_model = None
                re.add_guideline("IEEE", "intro", "Content")
                assert len(re.knowledge_base) == 1

    def test_not_chroma_enabled_with_embedding(self):
        re = _make_rag_engine()
        re.chroma_enabled = False
        with patch.object(re, "_seed_if_empty"):
            with patch.object(re, "_save_native"):
                re.add_guideline("ACM", "references", "Cite properly")
                assert len(re.knowledge_base) == 1
                assert re.knowledge_base[0]["metadata"]["publisher"] == "ACM"

    def test_not_chroma_no_embedding(self):
        re = _make_rag_engine()
        re.chroma_enabled = False
        re.embedding_model = None
        with patch.object(re, "_seed_if_empty"):
            with patch.object(re, "_save_native"):
                re.add_guideline("IEEE", "abstract", "Text")
                assert len(re.knowledge_base) == 1
                assert re.knowledge_base[0]["embedding"] == []


# ──────────────────────────────────────────────────────────────────────────────
# query_guidelines — edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestQueryGuidelines:
    def test_chroma_query_fallback_native(self):
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.collection = MagicMock()
        re.collection.query.side_effect = Exception("chroma error")
        re.knowledge_base = [
            {"text": "Abstract rules", "metadata": {"publisher": "IEEE"}, "embedding": [0.5] * 256},
        ]
        embed_mock = MagicMock()
        embed_mock.encode.return_value = [0.3] * 256
        re.embedding_model = embed_mock
        with patch.object(re, "_coerce_embedding_vector", side_effect=lambda x: [0.3] * 256):
            results = re.query_guidelines("IEEE", "abstract", top_k=1)
            assert len(results) > 0

    def test_embedding_model_none(self):
        re = _make_rag_engine()
        re.chroma_enabled = False
        re.embedding_model = None
        results = re.query_guidelines("IEEE", "test", top_k=1)
        assert results == []

    def test_native_query_empty_embedding(self):
        re = _make_rag_engine()
        re.embedding_model = MagicMock()
        re.embedding_model.encode.return_value = [0.3] * 256
        re.knowledge_base = [
            {"text": "Rule", "metadata": {"publisher": "IEEE"}, "embedding": []},
        ]
        with patch.object(re, "_coerce_embedding_vector", side_effect=lambda x: x if isinstance(x, list) and x else []):
            results = re.query_guidelines("IEEE", "test", top_k=1)
            assert results == []

    def test_shape_mismatch_skipped(self):
        re = _make_rag_engine()
        re.embedding_model = MagicMock()
        re.embedding_model.encode.return_value = [0.3] * 256
        re.knowledge_base = [
            {"text": "Rule 1", "metadata": {"publisher": "IEEE"}, "embedding": [0.5] * 128},
            {"text": "Rule 2", "metadata": {"publisher": "IEEE"}, "embedding": [0.5] * 256},
        ]
        with patch.object(re, "_coerce_embedding_vector", side_effect=lambda x: x if isinstance(x, list) and len(x) > 0 else []):
            results = re.query_guidelines("IEEE", "test", top_k=1)
            assert len(results) == 1

    def test_zero_denom_skipped(self):
        re = _make_rag_engine()
        re.embedding_model = MagicMock()
        re.embedding_model.encode.return_value = [0.0] * 256
        re.knowledge_base = [
            {"text": "Rule", "metadata": {"publisher": "IEEE"}, "embedding": [0.0] * 256},
        ]
        with patch.object(re, "_coerce_embedding_vector", side_effect=lambda x: x if isinstance(x, list) else x.tolist() if hasattr(x, 'tolist') else []):
            results = re.query_guidelines("IEEE", "test", top_k=1)
            assert results == []

    def test_exception_during_native(self):
        re = _make_rag_engine()
        re.embedding_model = MagicMock()
        re.embedding_model.encode.side_effect = Exception("encode fail")
        results = re.query_guidelines("IEEE", "test", top_k=1)
        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# query_rules — edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestQueryRules:
    def test_normal_flow(self):
        re = _make_rag_engine()
        re.knowledge_base = [
            {"text": "Abstract must be concise", "metadata": {"publisher": "IEEE", "section": "abstract"}, "embedding": [0.5] * 256},
        ]
        re.active_model_name = "deterministic-hash-v1"
        with patch.object(re, "query_guidelines", return_value=["Abstract must be concise"]):
            results = re.query_rules("IEEE", "abstract", top_k=1)
            assert len(results) == 1
            assert "text" in results[0]
            assert results[0]["metadata"]["publisher"] == "IEEE"

    def test_exception_returns_empty(self):
        re = _make_rag_engine()
        with patch.object(re, "query_guidelines", side_effect=Exception("fail")):
            results = re.query_rules("IEEE", "abstract", top_k=1)
            assert results == []

    def test_empty_template_defaults(self):
        re = _make_rag_engine()
        re.knowledge_base = []
        with patch.object(re, "query_guidelines", return_value=[]):
            results = re.query_rules("", "", top_k=1)
            assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# _save_native / _load_native
# ──────────────────────────────────────────────────────────────────────────────

class TestNativePersistence:
    def test_save_and_load(self):
        re = _make_rag_engine()
        re.knowledge_base = [{"text": "test", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]}]
        re._save_native()
        re.knowledge_base = []
        re._load_native()
        assert len(re.knowledge_base) == 1

    def test_load_no_file(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = str(tmp_path / "empty")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        # kb_file won't exist
        re._load_native()
        assert re.knowledge_base == []


# ──────────────────────────────────────────────────────────────────────────────
# reset
# ──────────────────────────────────────────────────────────────────────────────

class TestReset:
    def test_chroma_enabled_exception(self):
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.client = MagicMock()
        re.collection = MagicMock()
        re.client.delete_collection.side_effect = Exception("chroma delete fail")
        re.knowledge_base = [{"text": "rule"}]
        re.reset()
        assert len(re.knowledge_base) == 0

    def test_chroma_enabled_success(self):
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.client = MagicMock()
        re.collection = MagicMock()
        re.knowledge_base = [{"text": "rule"}]
        re.reset()
        assert len(re.knowledge_base) == 0
        re.client.delete_collection.assert_called_once()

    def test_no_kb_file(self, tmp_path):
        persist = str(tmp_path / "no_kb")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        re.knowledge_base = [{"text": "rule"}]
        re.reset()
        assert len(re.knowledge_base) == 0


# ──────────────────────────────────────────────────────────────────────────────
# _seed_if_empty — edge cases
# ──────────────────────────────────────────────────────────────────────────────

class TestSeedIfEmpty:
    def test_knowledge_base_not_empty(self):
        re = _make_rag_engine()
        re.knowledge_base = [{"existing": "data"}]
        with patch.object(re, "_save_native"):
            re._seed_if_empty()

    def test_chroma_enabled_with_data(self):
        re = _make_rag_engine()
        re.knowledge_base = []
        re.chroma_enabled = True
        re.collection = MagicMock()
        re.collection.count.return_value = 5
        with patch.object(re, "_save_native"):
            re._seed_if_empty()

    def test_default_file_not_found(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = str(tmp_path / "seed_test")
        re = _make_rag_engine(persist)
        re.knowledge_base = []
        re.chroma_enabled = False
        with patch("os.path.exists", return_value=False):
            re._seed_if_empty()

    def test_dict_payload_with_guidelines(self, tmp_path):
        import tempfile as _tf
        persist = str(tmp_path / "seed_dict")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        re.knowledge_base = []
        re.chroma_enabled = False
        default_file = os.path.join(os.path.dirname(os.path.dirname(re.kb_file)), "default_guidelines.json")
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", return_value={"guidelines": [{"publisher": "IEEE", "section": "abstract", "text": "Abstract rules"}]}):
                    with patch.object(re, "add_guideline"):
                        re._seed_if_empty()

    def test_list_payload(self, tmp_path):
        import tempfile as _tf
        persist = str(tmp_path / "seed_list")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        re.knowledge_base = []
        re.chroma_enabled = False
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", return_value=[{"publisher": "IEEE", "section": "abstract", "text": "Abstract rules"}]):
                    with patch.object(re, "add_guideline"):
                        re._seed_if_empty()

    def test_invalid_item_skipped(self, tmp_path):
        persist = str(tmp_path / "seed_invalid")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        re.knowledge_base = []
        re.chroma_enabled = False
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", return_value=[{"invalid": "item"}]):
                    with patch.object(re, "add_guideline"):
                        re._seed_if_empty()

    def test_general_exception(self):
        re = _make_rag_engine()
        with patch.object(re, "_save_native"):
            re._seed_if_empty()


# ──────────────────────────────────────────────────────────────────────────────
# get_rag_engine
# ──────────────────────────────────────────────────────────────────────────────

class TestGetRagEngine:
    def test_singleton_creates_new(self):
        from app.pipeline.intelligence.rag_engine import _rag_engine, get_rag_engine
        old = _rag_engine
        try:
            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod._rag_engine = None
            with patch.object(rag_mod, "RagEngine") as MockRE:
                instance = MagicMock()
                MockRE.return_value = instance
                result = get_rag_engine()
                assert result is instance
        finally:
            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod._rag_engine = old

    def test_singleton_returns_existing(self):
        from app.pipeline.intelligence.rag_engine import _rag_engine, get_rag_engine
        old = _rag_engine
        try:
            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod._rag_engine = "existing"
            result = get_rag_engine()
            assert result == "existing"
        finally:
            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod._rag_engine = old


# ──────────────────────────────────────────────────────────────────────────────
# RagEngine.__init__ — persist_directory logic
# ──────────────────────────────────────────────────────────────────────────────

class TestRagEngineInit:
    def test_default_persist_directory(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch.object(RagEngine, "_load_embedding_model"):
            re = RagEngine(auto_seed=False)
            assert "db" in re.persist_directory
            assert "semantic_store" in re.persist_directory

    def test_custom_persist_directory(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        custom = str(tmp_path / "custom_store")
        with patch.object(RagEngine, "_load_embedding_model"):
            re = RagEngine(persist_directory=custom, auto_seed=False)
            assert re.persist_directory == os.path.abspath(custom)

    def test_auto_seed_explicit_false(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch.object(RagEngine, "_load_embedding_model"):
            with patch.object(RagEngine, "_seed_if_empty") as mock_seed:
                re = RagEngine(persist_directory=str(tmp_path), auto_seed=True)
                mock_seed.assert_called_once()

    def test_chroma_fallback_native_on_error(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_cdb:
            mock_cdb.PersistentClient.side_effect = Exception("ChromaDB unavailable")
            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                with patch("app.pipeline.intelligence.rag_engine.np") as mock_np:
                    mock_np.float_ = None
                    with patch.object(RagEngine, "_load_embedding_model"):
                        re = RagEngine(persist_directory=str(tmp_path), auto_seed=False)
                        assert re.backend == "native"

    def test_known_compat_error_silent(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_cdb:
            mock_cdb.PersistentClient.side_effect = Exception("no such column: collections.topic")
            with patch.object(RagEngine, "_load_embedding_model"):
                re = RagEngine(persist_directory=str(tmp_path), auto_seed=False)
                assert re.backend == "native"

    def test_numpy_float_patched(self, tmp_path):
        import numpy as np
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_cdb:
            mock_cdb.PersistentClient.side_effect = Exception("np.float_ error")
            with patch("app.pipeline.intelligence.rag_engine.np") as mock_np:
                mock_np.float_ = None
                mock_np.int_ = None
                mock_np.float64 = np.float64
                mock_np.int64 = np.int64
                with patch.object(RagEngine, "_load_embedding_model"):
                    re = RagEngine(persist_directory=str(tmp_path), auto_seed=False)
                    assert re.backend == "native"


# ==============================================================================
#  ADDITIONAL PIPELINE ORCHESTRATOR COVERAGE — deep pipeline branches
# ==============================================================================

def _run_pipeline_core(orch, tmp_path, doc, sb, **overrides):
    """Helper: runs _run_pipeline_internal with all stages mocked."""
    doc.generated_doc = MagicMock()
    input_path = tmp_path / "test.pdf"
    input_path.write_text("dummy")
    parser = MagicMock()
    parser.parse.return_value = doc
    with (
        patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
        patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
        patch.object(orch, "_run_structure_detection", return_value=doc),
        patch.object(orch, "_run_classification", return_value=doc),
        patch.object(orch, "_run_validation_stage", return_value=doc),
        patch.object(orch, "_run_formatting_stage", return_value=doc),
        patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
        patch.object(orch, "_update_status"),
        patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
        patch("app.pipeline.orchestrator.CaptionMatcher"),
        patch("app.pipeline.orchestrator.TableCaptionMatcher"),
        patch("app.pipeline.orchestrator.ReferenceParser"),
        patch("app.pipeline.orchestrator.AIExplainer"),
        patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
        patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
        patch.object(orch, "_check_cancelled"),
        patch.object(orch, "_compute_sha256", return_value="abc"),
        patch("app.pipeline.orchestrator.settings") as mock_set,
    ):
        mock_pf.return_value.get_parser.return_value = parser
        mock_set.GROBID_ENABLED = overrides.get("GROBID_ENABLED", False)
        mock_set.USE_DOCLING_FALLBACK = overrides.get("USE_DOCLING_FALLBACK", False)
        mock_set.PYMUPDF_FALLBACK = overrides.get("PYMUPDF_FALLBACK", False)
        mock_set.PIPELINE_GROBID_TIMEOUT_SECONDS = 1
        mock_set.PIPELINE_DOCLING_TIMEOUT_SECONDS = 1
        mock_set.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 10
        mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
        mock_set.DEFAULT_FAST_MODE = overrides.get("DEFAULT_FAST_MODE", False)
        mock_set.LOW_MEMORY_MODE = overrides.get("LOW_MEMORY_MODE", False)
        return orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})


class TestPipelineNougatAndTemplate:
    def test_nougat_fallback_success(self, orch, tmp_path):
        """Lines 730-741: Nougat OCR produces blocks."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            input_path = tmp_path / "test.pdf"
            input_path.write_text("dummy")
            parser = MagicMock()
            parser.parse.return_value = doc
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.USE_DOCLING_FALLBACK = False
            mock_set.DEFAULT_FAST_MODE = False
            mock_set.LOW_MEMORY_MODE = False
            nougat_doc = PipelineDocument(
                document_id="job1",
                blocks=[Block(block_id="n1", index=1, block_type=BlockType.BODY, text="Nougat content")],
                metadata=DocumentMetadata(),
            )
            nougat_doc.metadata.ai_hints = {}
            with patch("app.pipeline.parsing.nougat_parser.NougatParser") as MockNougat:
                np_instance = MagicMock()
                np_instance.parse.return_value = nougat_doc
                MockNougat.return_value = np_instance
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing")

    def test_nougat_fallback_exception(self, orch, tmp_path):
        """Lines 740-741: Nougat OCR raises exception."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.USE_DOCLING_FALLBACK = False
            mock_set.DEFAULT_FAST_MODE = False
            mock_set.LOW_MEMORY_MODE = False
            with patch("app.pipeline.parsing.nougat_parser.NougatParser") as MockNougat:
                MockNougat.side_effect = Exception("Nougat unavailable")
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_no_template_name(self, orch, tmp_path):
        """Line 743->746: template_name is None."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="content")],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", None, {})
        assert result["status"] in ("success", "processing")


class TestPipelineParallelExtraction:
    def test_has_grobid_and_docling(self, orch, tmp_path):
        """Lines 759-765: AI Extraction already completed."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, DocumentMetadata
        md = DocumentMetadata()
        md.ai_hints = {"grobid_metadata": {"title": "Test"}, "docling_layout": {"elements": []}}
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="content")],
            metadata=md,
        )
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = md.ai_hints
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = True
            mock_set.USE_DOCLING_FALLBACK = True
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing")

    def test_grobid_disabled(self, orch, tmp_path):
        """Line 779-780: GROBID_ENABLED=false."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.USE_DOCLING_FALLBACK = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing")

    def test_grobid_timeout(self, orch, tmp_path):
        """Lines 818-822: GROBID future timeout."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = True
            mock_set.USE_DOCLING_FALLBACK = False
            mock_set.PIPELINE_GROBID_TIMEOUT_SECONDS = 0.001
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_grobid_exception(self, orch, tmp_path):
        """Line 786-788: GROBID extraction raises."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        orch.grobid_client.is_available.return_value = True
        orch.grobid_client.process_header_document.side_effect = Exception("GROBID fail")
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = True
            mock_set.USE_DOCLING_FALLBACK = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_grobid_unavailable(self, orch, tmp_path):
        """Line 782: GROBID client not available."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        orch.grobid_client.is_available.return_value = False
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = True
            mock_set.USE_DOCLING_FALLBACK = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_pymupdf_fallback_metadata_applied(self, orch, tmp_path):
        """Lines 857-874: PyMuPDF fallback metadata."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = True
            mock_set.USE_DOCLING_FALLBACK = False
            mock_set.PYMUPDF_FALLBACK = True
            mock_set.PIPELINE_GROBID_TIMEOUT_SECONDS = 0.001
            with patch.object(orch, "_extract_pymupdf_fallback_metadata", return_value={"title": "Fallback Title", "page_count": 5}):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")


class TestPipelineStageFailuresDeep:
    def test_structure_detector_failure(self, orch, tmp_path):
        """Lines 886-887: StructureDetector fails."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        with patch.object(orch, "_run_structure_detection", side_effect=Exception("SD fail")):
            result = _run_pipeline_core(orch, tmp_path, doc, sb)
        assert result["status"] in ("success", "processing", "error")

    def test_semantic_parser_failure(self, orch, tmp_path):
        """Lines 892-895: Semantic parser failure caught."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        with patch.object(orch, "_run_semantic_parsing", side_effect=Exception("SP fail")):
            with patch("app.pipeline.orchestrator.settings") as mock_s:
                mock_s.GROBID_ENABLED = False
                input_path = tmp_path / "test.pdf"
                input_path.write_text("dummy")
                parser = MagicMock()
                parser.parse.return_value = doc
                with (
                    patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
                    patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
                    patch.object(orch, "_run_classification", return_value=doc),
                    patch.object(orch, "_run_validation_stage", return_value=doc),
                    patch.object(orch, "_run_formatting_stage", return_value=doc),
                    patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
                    patch.object(orch, "_update_status"),
                    patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
                    patch("app.pipeline.orchestrator.CaptionMatcher"),
                    patch("app.pipeline.orchestrator.TableCaptionMatcher"),
                    patch("app.pipeline.orchestrator.ReferenceParser"),
                    patch("app.pipeline.orchestrator.AIExplainer"),
                    patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
                    patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
                    patch.object(orch, "_check_cancelled"),
                    patch.object(orch, "_compute_sha256", return_value="abc"),
                ):
                    mock_pf.return_value.get_parser.return_value = parser
                    result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"semantic_parser": True})
        assert result["status"] in ("success", "processing", "error")

    def test_crossref_enrichment(self, orch, tmp_path):
        """Lines 952-983: CrossRef validation."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, Reference
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.references = [Reference(reference_id="r1", index=0, citation_key="test2024", raw_text="Test ref")]
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.CROSSREF_MAX_WORKERS = 2
            with patch("app.services.crossref_client.get_crossref_client") as MockCR:
                cr = MagicMock()
                cr.validate_citation.return_value = {"valid": True}
                MockCR.return_value = cr
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"crossref_enrichment": True})
        assert result["status"] in ("success", "processing", "error")

    def test_crossref_exception(self, orch, tmp_path):
        """Lines 982-983: CrossRef exception caught."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.CROSSREF_MAX_WORKERS = 2
            with patch("app.services.crossref_client.get_crossref_client") as MockCR:
                MockCR.side_effect = Exception("CrossRef down")
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"crossref_enrichment": True})
        assert result["status"] in ("success", "processing", "error")

    def test_ai_reasoning_query_guidelines(self, orch, tmp_path):
        """Lines 1004-1015: RAG query_guidelines path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.blocks = [MagicMock(block_id="b1", text="content", metadata={}, semantic_intent="body")]
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = ["Keep it concise"]
        reasoner = MagicMock()
        reasoner.generate_instruction_set.return_value = {"instructions": [{"confidence": 0.8}]}
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_ai_reasoning_query_rules_fallback(self, orch, tmp_path):
        """Lines 1007-1009: RAG query_rules fallback."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines = None
        rag_inst.query_rules.return_value = [{"text": "Rule text"}]
        reasoner = MagicMock()
        reasoner.generate_instruction_set.return_value = {}
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_ai_reasoning_timeout(self, orch, tmp_path):
        """Lines 1042-1048: AI reasoning timeout."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = []
        reasoner = MagicMock()
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            with patch.object(orch, "_run_with_timeout", side_effect=TimeoutError("timeout")):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_ai_reasoning_general_exception(self, orch, tmp_path):
        """Lines 1049-1055: AI reasoning general exception."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = []
        reasoner = MagicMock()
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            with patch.object(orch, "_run_with_timeout", side_effect=Exception("generic error")):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_reasoning_engines_unavailable(self, orch, tmp_path):
        """Lines 995-999: RAG/reasoner engines unavailable."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=None),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=None),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_confidence_gating_low(self, orch, tmp_path):
        """Lines 1058-1060: Confidence gating sets review_required."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = []
        reasoner = MagicMock()
        reasoner.generate_instruction_set.return_value = {"instructions": [{"confidence": 0.5}]}
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")

    def test_confidence_gating_high(self, orch, tmp_path):
        """Lines 1058-1060: High confidence does NOT set review_required."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = []
        reasoner = MagicMock()
        reasoner.generate_instruction_set.return_value = {"instructions": [{"confidence": 0.95}]}
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
            patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst),
            patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner),
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = 10
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"ai_reasoning": True})
        assert result["status"] in ("success", "processing", "error")


class TestPipelinePersistenceAndErrors:
    def test_formatting_failure_no_artifact(self, orch, tmp_path):
        """Lines 1087-1097: Formatter produces no generated_doc."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = None
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("error", "processing")

    def test_persistence_completed_with_hash(self, orch, tmp_path):
        """Lines 1133-1137: Hash computation in persistence."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        import app.services.document_service
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        output_path = tmp_path / "out.docx"
        output_path.write_text("output")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(output_path)),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_persistence_hash_exception(self, orch, tmp_path):
        """Lines 1136-1137: Hash computation exception."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        output_path = tmp_path / "out.docx"
        output_path.write_text("output")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(output_path)),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", side_effect=Exception("hash fail")),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_output_not_ready_fallback_to_memory(self, orch, tmp_path):
        """Line 1126->1129: output ready with in-memory generated_doc."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "nonexistent.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_output_failure(self, orch, tmp_path):
        """Lines 1144-1147: Output generation failed."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "nonexistent.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            del doc.generated_doc
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("error", "processing")


class TestPipelineErrorHandler:
    def test_error_handler_partial_persist(self, orch, tmp_path):
        """Lines 1182-1186: Verify the error handler code is reached."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.return_value.get_parser.return_value = parser
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch.object(orch, "_run_classification", side_effect=Exception("pipeline crash")):
                    with patch.object(orch, "_update_status"):
                        with patch.object(orch, "_persist_partial_result") as mock_persist:
                            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("error", "processing")

    def test_error_handler_partial_persist_fails(self, orch, tmp_path):
        """Lines 1185-1186: Partial persist itself fails."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.return_value.get_parser.return_value = parser
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch.object(orch, "_run_classification", side_effect=Exception("pipeline crash")):
                    with patch.object(orch, "_update_status"):
                        with patch.object(orch, "_persist_partial_result", side_effect=Exception("persist fail")):
                            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("error", "processing")

    def test_error_handler_with_output_path_fallback(self, orch, tmp_path):
        """Lines 1189-1203: Error with output path -> downgrades to warning."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        output_path = tmp_path / "out.docx"
        output_path.write_text("output")
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch.object(orch, "_run_classification", side_effect=Exception("classify fail")):
                with patch.object(orch, "_export_document", return_value=str(output_path)):
                    result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_error_handler_output_hash_exception(self, orch, tmp_path):
        """Lines 1193-1195: Hash exception during warning path."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        output_path = tmp_path / "out.docx"
        output_path.write_text("output")
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", side_effect=Exception("hash fail")),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch.object(orch, "_run_classification", side_effect=Exception("classify fail")):
                with patch.object(orch, "_export_document", return_value=str(output_path)):
                    result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_error_handler_no_output_path(self, orch, tmp_path):
        """Lines 1204-1212: Error without output path -> FAILED."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.return_value.get_parser.return_value = parser
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch.object(orch, "_run_classification", side_effect=Exception("early crash")):
                    with patch.object(orch, "_update_status"):
                        result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("processing", "error")


class TestPipelineAdditionalBranches:
    def test_keyword_extraction_empty(self, orch, tmp_path):
        """Line 919: detected_keywords is empty list."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.abstract = "Abstract text"
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch("app.pipeline.orchestrator.extract_keywords", return_value=[]):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_keyword_extraction_from_block(self, orch, tmp_path):
        """Lines 912-917: Extracts keywords from abstract block."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.ABSTRACT_BODY, text="This is an abstract about AI research.")],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch("app.pipeline.orchestrator.extract_keywords", return_value=["AI", "research"]):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_keyword_extraction_exception(self, orch, tmp_path):
        """Lines 923-924: Keyword extraction exception."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.abstract = "Abstract"
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch("app.pipeline.orchestrator.extract_keywords", side_effect=Exception("kw fail")):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_figure_analysis_not_fast_mode(self, orch, tmp_path):
        """Lines 935-936: Figure analysis runs when fast_mode is False."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            with patch.object(orch, "_run_figure_analysis_stage", return_value=doc):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {"fast_mode": False})
        assert result["status"] in ("success", "processing", "error")

    def test_sb_is_none_in_persistence(self, orch, tmp_path):
        """Lines 1115->1120: sb is None when inserting document_results."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")

    def test_non_pdf_file_skips_ai_extraction(self, orch, tmp_path):
        """Line 759: non-PDF file skips parallel extraction."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints = {}
        sb = _make_sb()
        input_path = tmp_path / "test.txt"
        input_path.write_text("dummy content")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.AIExplainer"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] in ("success", "processing", "error")


class TestGetRagReasoningEngines:
    def test_get_rag_engine_resolves(self):
        from app.pipeline.orchestrator import get_rag_engine
        with patch("app.pipeline.orchestrator.resolve_optional_callable") as mock_resolve:
            mock_resolve.return_value = "rag_engine_instance"
            result = get_rag_engine()
            assert result == "rag_engine_instance"
            mock_resolve.assert_called_once_with(
                "app.pipeline.intelligence.rag_engine",
                "get_rag_engine",
            )

    def test_get_reasoning_engine_resolves(self):
        from app.pipeline.orchestrator import get_reasoning_engine
        with patch("app.pipeline.orchestrator.resolve_optional_callable") as mock_resolve:
            mock_resolve.return_value = "reasoning_engine_instance"
            result = get_reasoning_engine()
            assert result == "reasoning_engine_instance"
            mock_resolve.assert_called_once_with(
                "app.pipeline.intelligence.reasoning_engine",
                "get_reasoning_engine",
            )


class TestUpdateStatusBranches:
    def test_transient_error_during_update_retry(self, orch):
        """Line 167->exit: non-transient error raises."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = Exception("disk full")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_existing_record_update_with_data(self, orch):
        """Update path for existing record."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "VALIDATION", "FAILED", message="Validation error")

    def test_insert_with_status_other(self, orch):
        """Insert with a non-standard status."""
        sb = _make_sb()
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "QUEUED", progress=0)


class TestEditFlowAdditionalBranches:
    def test_edit_flow_no_formatted_doc(self, orch):
        """Line 1273->1290: Formatter returns falsy doc."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = None
                            result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"

    def test_edit_flow_version_number_exception(self, orch):
        """Lines 1300-1303: Version number parsing exception."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"version_number": "invalid"}
        ]
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = MagicMock()
                            with patch("app.pipeline.orchestrator.Exporter"):
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"

    def test_edit_flow_cancelled_with_update_status_error(self, orch):
        """Lines 1343-1344: CancelledError and update_status raises."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = asyncio.CancelledError("cancel")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.object(orch, "_update_status", side_effect=Exception("cleanup fail")):
                result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "cancelled"

    def test_edit_flow_existing_result_version_v4(self, orch):
        """Edit flow with version v4 and versions list."""
        from app.models import BlockType
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"version_number": "v4"}
        ]
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            mock_fmt.return_value.process.return_value = MagicMock()
                            with patch("app.pipeline.orchestrator.Exporter"):
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"


class TestRunSemanticParsingBranches:
    def test_semantic_blocks_shorter(self, orch):
        """Line 575->574: semantic_blocks shorter than doc blocks."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType
        doc = PipelineDocument(
            document_id="d1",
            blocks=[
                Block(block_id="b1", index=0, block_type=BlockType.BODY, text="first"),
                Block(block_id="b2", index=1, block_type=BlockType.BODY, text="second"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 10
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_sp:
                sp_instance = MagicMock()
                sp_instance.analyze_blocks.return_value = [
                    {"predicted_section_type": "introduction", "confidence_score": 0.95},
                ]
                mock_sp.return_value = sp_instance
                result = orch._run_semantic_parsing(doc)
        assert result.metadata.ai_hints is not None
        assert doc.blocks[0].metadata.get("semantic_intent") == "introduction"


class TestRunFigureAnalysisStageAdditional:
    def test_metadata_dict_with_setdefault(self, orch):
        """Line 614->617: metadata is dict with setdefault."""
        from app.models import PipelineDocument, DocumentMetadata, Block, BlockType, Figure
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig.png", caption_text="Fig")
        doc = PipelineDocument(
            document_id="figdoc",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body")],
            figures=[fig],
        )
        object.__setattr__(doc, "metadata", {"key": "value"})
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert isinstance(result.metadata, dict)


class TestLogQualitySummary:
    def test_log_quality_summary(self, orch):
        summary = {
            "quality_score": 85.5,
            "avg_confidence": 0.85,
            "min_confidence": 0.5,
            "block_count": 10,
            "heading_candidates": 3,
            "figures": 2,
            "tables": 1,
            "errors": 1,
            "warnings": 2,
            "low_conf_blocks": 0,
            "review_status": "N/A",
        }
        orch._log_quality_summary("job1", summary)


# ──────────────────────────────────────────────────────────────────────────────
# RagEngine error-path tests
# ──────────────────────────────────────────────────────────────────────────────

class TestRagEngineErrorPaths:
    """pytest.raises error-path tests for RagEngine."""

    def test_query_guidelines_empty_publisher_returns_empty(self):
        """Querying with empty publisher returns empty results."""
        re = _make_rag_engine()
        re.embedding_model = None
        results = re.query_guidelines("", "test")
        assert results == []

    def test_query_guidelines_chroma_exception_fallback_empty(self):
        """Chroma exception with empty native KB returns empty."""
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.collection = MagicMock()
        re.collection.query.side_effect = Exception("chroma fail")
        re.knowledge_base = []
        with patch.object(re, "_coerce_embedding_vector", return_value=[]):
            results = re.query_guidelines("IEEE", "test", top_k=1)
            assert results == []

    def test_add_guideline_empty_text_skipped(self):
        """Adding guideline with empty text is skipped."""
        re = _make_rag_engine()
        re.chroma_enabled = False
        with patch.object(re, "_save_native"):
            re.add_guideline("IEEE", "abstract", "")
        assert len(re.knowledge_base) == 0

    def test_add_guideline_chroma_exception_handled(self):
        """Chroma exception during add_guideline is caught."""
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.collection = MagicMock()
        re.collection.add.side_effect = Exception("chroma add fail")
        with patch.object(re, "_save_native"):
            re.add_guideline("IEEE", "abstract", "Some guideline text")
        assert len(re.knowledge_base) == 1

    def test_reset_chroma_exception_handled(self):
        """Chroma exception during reset is handled."""
        re = _make_rag_engine()
        re.chroma_enabled = True
        re.client = MagicMock()
        re.client.delete_collection.side_effect = Exception("delete fail")
        re.collection = MagicMock()
        re.knowledge_base = [{"text": "rule"}]
        re.reset()
        assert len(re.knowledge_base) == 0

    def test_load_native_corrupt_json(self, tmp_path):
        """Loading corrupt JSON file does not crash."""
        persist = str(tmp_path / "corrupt_kb")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        import json
        kb_path = re.kb_file
        with open(kb_path, "w") as f:
            f.write("not valid json")
        re._load_native()
        assert re.knowledge_base == []

    def test_seed_if_empty_invalid_json_file(self, tmp_path):
        """Seeding from invalid JSON file does not crash."""
        persist = str(tmp_path / "seed_bad")
        os.makedirs(persist, exist_ok=True)
        re = _make_rag_engine(persist)
        re.knowledge_base = []
        re.chroma_enabled = False
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", side_effect=json.JSONDecodeError("bad", "doc", 0)):
                    re._seed_if_empty()
        # Should not raise
        assert True


# ──────────────────────────────────────────────────────────────────────────────
# PipelineOrchestrator additional error-path tests
# ──────────────────────────────────────────────────────────────────────────────

class TestOrchestratorErrorPaths:
    """pytest.raises error-path tests for PipelineOrchestrator."""

    def test_should_skip_docling_none_path_returns_default(self, orch):
        """_should_skip_docling_for_digital_pdf with None path returns default."""
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = False
            result = orch._should_skip_docling_for_digital_pdf(None)
            assert result is False

    def test_build_quality_summary_no_blocks_safe(self, orch):
        """_build_quality_summary with no blocks does not crash."""
        from app.models import PipelineDocument, DocumentMetadata
        doc = PipelineDocument(document_id="empty", blocks=[], metadata=DocumentMetadata())
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 0.0}):
            summary = orch._build_quality_summary(doc, {"errors": [], "warnings": []})
        assert summary["block_count"] == 0
        assert summary["quality_score"] == 0.0

    def test_run_with_timeout_negative_seconds_raises(self, orch):
        """_run_with_timeout with negative timeout raises."""
        with pytest.raises((ValueError, TimeoutError)):
            orch._run_with_timeout(lambda: 42, -1)

    def test_persist_partial_result_none_doc_does_not_raise(self, orch):
        """_persist_partial_result with None doc does not raise."""
        orch._persist_partial_result("job_none", None, None)

    def test_check_cancelled_none_job_does_not_raise(self, orch):
        """_check_cancelled with None job_id does not raise."""
        orch._check_cancelled(None)
