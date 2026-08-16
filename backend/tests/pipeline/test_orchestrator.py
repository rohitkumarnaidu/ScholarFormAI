# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import hashlib
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, Figure, PipelineDocument


@pytest.fixture
def orch():
    from app.pipeline.orchestrator import PipelineOrchestrator

    with (
        patch("app.pipeline.orchestrator.InputConverter"),
        patch("app.pipeline.orchestrator.ContentAnalyzer"),
        patch("app.pipeline.orchestrator.ContractLoader"),
        patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
        patch("app.pipeline.orchestrator.GROBIDClient"),
        patch("app.pipeline.orchestrator.DoclingClient"),
    ):
        o = PipelineOrchestrator(templates_dir="app/templates", temp_dir="/tmp/test_temp")
        return o


@pytest.fixture
def minimal_doc():
    return PipelineDocument(
        document_id="doc1",
        blocks=[],
        metadata=DocumentMetadata(),
    )


@pytest.fixture
def doc_with_blocks():
    blocks = [
        Block(block_id="b1", index=1, block_type=BlockType.TITLE, text="Title", section_name="title"),
        Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Body text.", section_name="body"),
        Block(block_id="b3", index=3, block_type=BlockType.HEADING_1, text="Section", section_name="section"),
    ]
    doc = PipelineDocument(document_id="doc2", blocks=blocks, metadata=DocumentMetadata())
    doc.formatting_options = {}
    return doc


# ── Init ────────────────────────────────────────────────────────────────────


class TestOrchestratorInit:
    def test_init_defaults(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        with (
            patch("app.pipeline.orchestrator.InputConverter"),
            patch("app.pipeline.orchestrator.ContentAnalyzer"),
            patch("app.pipeline.orchestrator.ContractLoader"),
            patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
            patch("app.pipeline.orchestrator.GROBIDClient"),
            patch("app.pipeline.orchestrator.DoclingClient"),
            patch("os.makedirs"),
        ):
            o = PipelineOrchestrator()
        assert o.templates_dir == "app/templates"
        assert o.temp_dir == "temp"
        assert o.converter is not None
        assert o.analyzer is not None
        assert o.contract_loader is not None
        assert o.ref_normalizer is not None
        assert o.grobid_client is not None
        assert o.docling_client is not None

    def test_init_custom_paths(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        with (
            patch("app.pipeline.orchestrator.InputConverter"),
            patch("app.pipeline.orchestrator.ContentAnalyzer"),
            patch("app.pipeline.orchestrator.ContractLoader"),
            patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
            patch("app.pipeline.orchestrator.GROBIDClient"),
            patch("app.pipeline.orchestrator.DoclingClient"),
            patch("os.makedirs"),
        ):
            o = PipelineOrchestrator(templates_dir="/custom/templates", temp_dir="/custom/temp")
        assert o.templates_dir == "/custom/templates"
        assert o.temp_dir == "/custom/temp"

    def test_init_creates_temp_dir(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        with (
            patch("app.pipeline.orchestrator.InputConverter"),
            patch("app.pipeline.orchestrator.ContentAnalyzer"),
            patch("app.pipeline.orchestrator.ContractLoader"),
            patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
            patch("app.pipeline.orchestrator.GROBIDClient"),
            patch("app.pipeline.orchestrator.DoclingClient"),
            patch("os.makedirs") as mock_mkdir,
        ):
            PipelineOrchestrator(temp_dir="/tmp/custom")
        mock_mkdir.assert_called_with("/tmp/custom", exist_ok=True)


# ── Stage interface check ───────────────────────────────────────────────────


class TestOrchestratorStageInterface:
    def test_check_stage_interface_passes(self, orch):
        obj = MagicMock()
        obj.process = MagicMock()
        orch._check_stage_interface(obj, "process", "TestStage")

    def test_check_stage_interface_raises(self, orch):
        obj = MagicMock(spec=[])
        with pytest.raises(RuntimeError, match="Pipeline Stage Error"):
            orch._check_stage_interface(obj, "missing_method", "BadStage")


# ── Coerce bool ──────────────────────────────────────────────────────────────


class TestOrchestratorCoerceBool:
    def test_none(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool(None, True) is True
        assert PipelineOrchestrator._coerce_bool(None, False) is False

    def test_bool_passthrough(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool(True, False) is True
        assert PipelineOrchestrator._coerce_bool(False, True) is False

    def test_int_float(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool(1, False) is True
        assert PipelineOrchestrator._coerce_bool(0, True) is False
        assert PipelineOrchestrator._coerce_bool(0.0, True) is False

    def test_string_true(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool("true", False) is True
        assert PipelineOrchestrator._coerce_bool("yes", False) is True
        assert PipelineOrchestrator._coerce_bool("1", False) is True
        assert PipelineOrchestrator._coerce_bool("on", False) is True

    def test_string_false(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool("false", True) is False
        assert PipelineOrchestrator._coerce_bool("no", True) is False
        assert PipelineOrchestrator._coerce_bool("0", True) is False
        assert PipelineOrchestrator._coerce_bool("off", True) is False

    def test_unknown(self):
        from app.pipeline.orchestrator import PipelineOrchestrator

        assert PipelineOrchestrator._coerce_bool("maybe", True) is True
        assert PipelineOrchestrator._coerce_bool("maybe", False) is False


# ── Resolve runtime flags ───────────────────────────────────────────────────


class TestOrchestratorRuntimeFlags:
    def test_default_fast_mode_false(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_settings:
            mock_settings.DEFAULT_FAST_MODE = False
            mock_settings.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags({})
        assert flags["fast_mode"] is True

    def test_fast_mode_enabled(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_settings:
            mock_settings.DEFAULT_FAST_MODE = False
            mock_settings.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags({"fast_mode": True})
        assert flags["fast_mode"] is True
        assert flags["semantic_parser"] is False
        assert flags["crossref_enrichment"] is False
        assert flags["ai_reasoning"] is False

    def test_fast_mode_disabled(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_settings:
            mock_settings.DEFAULT_FAST_MODE = False
            mock_settings.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags({"fast_mode": False})
        assert flags["fast_mode"] is False
        assert flags["semantic_parser"] is True
        assert flags["crossref_enrichment"] is True
        assert flags["ai_reasoning"] is True

    def test_low_memory_force_fast(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_settings:
            mock_settings.DEFAULT_FAST_MODE = False
            mock_settings.LOW_MEMORY_MODE = True
            flags = orch._resolve_runtime_flags({"fast_mode": False})
        assert flags["fast_mode"] is False


# ── SHA256 ───────────────────────────────────────────────────────────────────


class TestOrchestratorSHA256:
    def test_compute_sha256(self, orch, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        result = orch._compute_sha256(str(f))
        assert result == expected

    def test_compute_sha256_large_file(self, orch, tmp_path):
        f = tmp_path / "large.bin"
        data = b"x" * (1024 * 1024 * 2 + 100)
        f.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert orch._compute_sha256(str(f)) == expected


# ── Record stage transition / Prometheus metrics ─────────────────────────────


class TestOrchestratorMetrics:
    def test_record_stage_transition_processing(self, orch):
        orch._record_stage_transition("job1", "EXTRACTION", "PROCESSING")
        assert ("job1", "EXTRACTION") in orch._stage_start_times

    def test_record_stage_transition_completed(self, orch):
        orch._stage_start_times[("job1", "EXTRACTION")] = time.perf_counter() - 1.0
        with patch("app.middleware.prometheus_metrics.MetricsManager"):
            orch._record_stage_transition("job1", "EXTRACTION", "COMPLETED")
        assert ("job1", "EXTRACTION") not in orch._stage_start_times

    def test_record_stage_transition_unknown_status(self, orch):
        orch._record_stage_transition("job1", "EXTRACTION", "UNKNOWN_STATUS")


# ── Update status (Supabase) ────────────────────────────────────────────────


class TestOrchestratorUpdateStatus:
    def test_update_status_no_supabase(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            with patch.dict(sys.modules, {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "PROCESSING", "Working...")

    def test_update_status_success(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict(sys.modules, {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED", "Done", progress=50)
        assert sb.table.call_count >= 2

    def test_update_status_existing_record(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict(sys.modules, {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED", "Done", progress=50)

    def test_update_status_failed(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict(sys.modules, {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "FAILED", "Error occurred", progress=0)

    def test_update_status_transient_error_retry(self, orch):
        sb = MagicMock()
        from httpx import RemoteProtocolError

        mock_execute = MagicMock()
        mock_execute.side_effect = [
            RemoteProtocolError("Server disconnected"),
            MagicMock(data=[]),
        ]
        sb.table.return_value.select.return_value.match.return_value.execute = mock_execute
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict(sys.modules, {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED", "Done")


# ── Check cancelled ─────────────────────────────────────────────────────────


class TestOrchestratorCheckCancelled:
    def test_not_cancelled(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"status": "PROCESSING"}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            orch._check_cancelled("job1")

    def test_cancelled_raises(self, orch):
        import asyncio

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"status": "CANCELLED"}]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with pytest.raises(asyncio.CancelledError):
                orch._check_cancelled("job1")

    def test_no_supabase(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orch._check_cancelled("job1")

    def test_query_error(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            orch._check_cancelled("job1")


# ── Persist partial result ──────────────────────────────────────────────────


class TestOrchestratorPersistPartial:
    def test_persist_partial_result_no_sb(self, orch):
        orch._persist_partial_result("job1", MagicMock(), None)

    def test_persist_partial_result_no_doc(self, orch):
        orch._persist_partial_result("job1", None, MagicMock())

    def test_persist_partial_result_insert(self, orch):
        doc = MagicMock()
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.build_structured_data", return_value={"key": "val"}):
            orch._persist_partial_result("job1", doc, sb)
        sb.table.return_value.insert.assert_called_once()

    def test_persist_partial_result_update(self, orch):
        doc = MagicMock()
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]
        with patch("app.pipeline.orchestrator.build_structured_data", return_value={"key": "val"}):
            orch._persist_partial_result("job1", doc, sb)
        sb.table.return_value.update.assert_called_once()

    def test_persist_partial_result_error(self, orch):
        doc = MagicMock()
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("oops")
        orch._persist_partial_result("job1", doc, sb)


# ── Run with timeout ────────────────────────────────────────────────────────


class TestOrchestratorRunWithTimeout:
    def test_run_with_timeout_success(self, orch):
        result = orch._run_with_timeout(lambda x: x.upper(), 5, "hello")
        assert result == "HELLO"

    def test_run_with_timeout_timeout(self, orch):
        def slow_func():
            import time

            time.sleep(10)
            return "done"

        with pytest.raises(TimeoutError, match="timed out"):
            orch._run_with_timeout(slow_func, 1)

    def test_run_with_timeout_cancel_event(self, orch):
        cancel_event = threading.Event()

        def slow_func():
            import time

            time.sleep(10)
            return "done"

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow_func, 1, cancel_event=cancel_event)
        assert cancel_event.is_set()


# ── Skip docling for digital PDF ────────────────────────────────────────────


class TestOrchestratorSkipDocling:
    def test_skip_docling_force(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = True
            result = orch._should_skip_docling_for_digital_pdf("/path/to.pdf")
        assert result is False

    def test_skip_docling_disabled(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = False
            result = orch._should_skip_docling_for_digital_pdf("/path/to.pdf")
        assert result is False

    def test_skip_docling_skip_digital(self, orch, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 some text content")
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            with patch("fitz.open") as mock_fitz:
                mock_page = MagicMock()
                mock_page.get_text.return_value = (
                    "Hello world, this is a digital PDF with enough text to qualify for skipping the Docling layout pass completely. "
                    * 5
                )
                mock_doc = MagicMock()
                mock_doc.__len__.return_value = 1
                mock_doc.__getitem__.return_value = mock_page
                mock_fitz.return_value.__enter__.return_value = mock_doc
                result = orch._should_skip_docling_for_digital_pdf(str(pdf))
        assert result is True

    def test_skip_docling_scanned_pdf(self, orch, tmp_path):
        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            with patch("fitz.open") as mock_fitz:
                mock_page = MagicMock()
                mock_page.get_text.return_value = ""
                mock_doc = MagicMock()
                mock_doc.__len__.return_value = 1
                mock_doc.__getitem__.return_value = mock_page
                mock_fitz.return_value.__enter__.return_value = mock_doc
                result = orch._should_skip_docling_for_digital_pdf(str(pdf))
        assert result is False

    def test_skip_docling_error(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            with patch("fitz.open", side_effect=Exception("no fitz")):
                result = orch._should_skip_docling_for_digital_pdf("/bad/path.pdf")
        assert result is False


# ── PyMuPDF fallback metadata ───────────────────────────────────────────────


class TestOrchestratorPyMuPDF:
    def test_extract_fallback_no_fitz(self, orch):
        result = orch._extract_pymupdf_fallback_metadata("/nonexistent/path.pdf")
        assert result == {}

    def test_extract_fallback_success(self, orch, tmp_path):
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with patch("fitz.open") as mock_fitz:
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Sample abstract text"
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 5
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.metadata = {"title": "Test Title", "author": "Author"}
            mock_fitz.return_value.__enter__.return_value = mock_doc
            result = orch._extract_pymupdf_fallback_metadata(str(pdf))
        assert result["source"] == "pymupdf"
        assert result["page_count"] == 5
        assert result["title"] == "Test Title"
        assert result["sample_text_chars"] > 0

    def test_extract_fallback_exception(self, orch):
        with patch("fitz.open", side_effect=Exception("fail")):
            result = orch._extract_pymupdf_fallback_metadata("/path.pdf")
        assert result == {}


# ── Sync block confidence ────────────────────────────────────────────────────


class TestOrchestratorSyncConfidence:
    def test_sync_block_confidence(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(
                    block_id="b1",
                    index=1,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": 0.85},
                ),
                Block(
                    block_id="b2",
                    index=2,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": 0.45},
                ),
            ],
            metadata=DocumentMetadata(),
        )
        orch._sync_block_confidence(doc)
        assert doc.blocks[0].metadata["nlp_confidence"] == 0.85
        assert doc.blocks[1].metadata["nlp_confidence"] == 0.45

    def test_sync_block_confidence_fallback_nlp_confidence(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t", metadata={"nlp_confidence": 0.72}),
            ],
            metadata=DocumentMetadata(),
        )
        orch._sync_block_confidence(doc)
        assert doc.blocks[0].metadata["nlp_confidence"] == 0.72

    def test_sync_block_confidence_clamps(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(
                    block_id="b1",
                    index=1,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": 1.5},
                ),
                Block(
                    block_id="b2",
                    index=2,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": -0.5},
                ),
            ],
            metadata=DocumentMetadata(),
        )
        orch._sync_block_confidence(doc)
        assert doc.blocks[0].metadata["nlp_confidence"] == 1.0
        assert doc.blocks[1].metadata["nlp_confidence"] == 0.0

    def test_sync_block_confidence_no_conf(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        orch._sync_block_confidence(doc)
        assert "nlp_confidence" not in doc.blocks[0].metadata

    def test_sync_block_confidence_semantic_intent(self, orch):
        block = Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t")
        block.semantic_intent = "introduction"
        doc = PipelineDocument(document_id="doc1", blocks=[block], metadata=DocumentMetadata())
        block.metadata["classification_confidence"] = 0.9
        orch._sync_block_confidence(doc)
        assert doc.blocks[0].metadata["semantic_intent"] == "introduction"

    def test_sync_block_confidence_invalid_value(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(
                    block_id="b1",
                    index=1,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": "not_a_number"},
                ),
            ],
            metadata=DocumentMetadata(),
        )
        orch._sync_block_confidence(doc)
        assert "nlp_confidence" not in doc.blocks[0].metadata

    def test_sync_block_confidence_no_blocks(self, orch):
        orch._sync_block_confidence(MagicMock(spec=[]))


# ── Build quality summary ────────────────────────────────────────────────────


class TestOrchestratorQualitySummary:
    def test_build_quality_summary(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t", metadata={"nlp_confidence": 0.9}),
                Block(
                    block_id="b2",
                    index=2,
                    block_type=BlockType.HEADING_1,
                    text="Section",
                    metadata={"nlp_confidence": 0.8, "is_heading_candidate": True},
                ),
            ],
            metadata=DocumentMetadata(),
            figures=[
                Figure(figure_id="f1", index=1, export_path="fig.png", caption_text="Figure"),
            ],
        )
        validation_results = {"errors": [], "warnings": []}
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 85.0}):
            summary = orch._build_quality_summary(doc, validation_results)
        assert summary["block_count"] == 2
        assert summary["heading_candidates"] == 1
        assert summary["figures"] == 1
        assert isinstance(summary["quality_score"], (int, float))

    def test_build_quality_summary_empty(self, orch):
        doc = PipelineDocument(document_id="doc1", blocks=[], metadata=DocumentMetadata())
        validation_results = {"errors": [], "warnings": []}
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 0.0}):
            summary = orch._build_quality_summary(doc, validation_results)
        assert summary["block_count"] == 0
        assert summary["figures"] == 0
        assert summary["tables"] == 0

    def test_build_quality_summary_with_errors(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t", metadata={"nlp_confidence": 0.3}),
            ],
            metadata=DocumentMetadata(),
        )
        validation_results = {"errors": ["err1"], "warnings": ["warn1"]}
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 50.0}):
            summary = orch._build_quality_summary(doc, validation_results)
        assert summary["errors"] == 1
        assert summary["warnings"] == 1


# ── Log quality summary ──────────────────────────────────────────────────────


class TestOrchestratorLogQuality:
    def test_log_quality_summary(self, orch):
        summary = {
            "quality_score": 85.0,
            "avg_confidence": 0.8,
            "min_confidence": 0.5,
            "block_count": 10,
            "heading_candidates": 3,
            "figures": 2,
            "tables": 1,
            "errors": 0,
            "warnings": 1,
            "review_status": "N/A",
        }
        with patch("app.pipeline.orchestrator.logger") as mock_log:
            orch._log_quality_summary("job1", summary)
        assert mock_log.info.call_count >= 2


# ── Pipeline stage methods ──────────────────────────────────────────────────


class TestOrchestratorPipelineStages:
    def test_run_extraction_stage_pdf(self, orch):
        factory = MagicMock()
        parser = MagicMock()
        doc = MagicMock()
        parser.parse.return_value = doc
        factory.get_parser.return_value = parser
        result = orch._run_extraction_stage(factory, "/path/file.pdf", "job1", {}, ".pdf")
        factory.get_parser.assert_called_with("/path/file.pdf")
        parser.parse.assert_called_with("/path/file.pdf", "job1")
        assert result.formatting_options == {}

    def test_run_extraction_stage_non_pdf(self, orch):
        factory = MagicMock()
        parser = MagicMock()
        doc = MagicMock()
        parser.parse.return_value = doc
        factory.get_parser.return_value = parser
        orch.converter.convert_to_docx.return_value = "/tmp/converted.docx"
        orch._run_extraction_stage(factory, "/path/file.doc", "job1", {}, ".doc")
        orch.converter.convert_to_docx.assert_called_with("/path/file.doc", "job1")
        factory.get_parser.assert_called_with("/tmp/converted.docx")

    def test_run_extraction_stage_docx(self, orch):
        factory = MagicMock()
        parser = MagicMock()
        doc = MagicMock()
        parser.parse.return_value = doc
        factory.get_parser.return_value = parser
        orch._run_extraction_stage(factory, "/path/file.docx", "job1", {}, ".docx")
        orch.converter.convert_to_docx.assert_called_once()

    def test_run_structure_detection(self, orch):
        doc = MagicMock()
        with patch("app.pipeline.orchestrator.StructureDetector") as mock_sd:
            sd_instance = mock_sd.return_value
            sd_instance.process.return_value = doc
            result = orch._run_structure_detection(doc)
        assert result is doc

    def test_run_classification(self, orch):
        doc = MagicMock()
        with patch("app.pipeline.orchestrator.ContentClassifier") as mock_cc:
            cc_instance = mock_cc.return_value
            cc_instance.process.return_value = doc
            result = orch._run_classification(doc)
        assert result is doc

    def test_run_validation_stage(self, orch):
        doc = MagicMock()
        with patch("app.pipeline.orchestrator.DocumentValidator") as mock_dv:
            dv_instance = mock_dv.return_value
            dv_instance.process.return_value = doc
            with patch.object(orch, "_run_with_timeout", return_value=doc):
                result = orch._run_validation_stage(doc)
        assert result is doc

    def test_run_formatting_stage(self, orch):
        doc = MagicMock()
        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
            fmt_instance = mock_fmt.return_value
            fmt_instance.process.return_value = doc
            with patch.object(orch, "_run_with_timeout", return_value=doc):
                result = orch._run_formatting_stage(doc)
        assert result is doc

    def test_run_semantic_parsing_fast_mode(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 10
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_sp:
                sp_instance = mock_sp.return_value
                sp_instance.analyze_blocks.return_value = [
                    {"predicted_section_type": "introduction", "confidence_score": 0.85}
                ]
                result = orch._run_semantic_parsing(doc)
        assert result.blocks[0].metadata["semantic_intent"] == "introduction"

    def test_run_semantic_parsing_fallback(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 10
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_sp:
                sp_instance = mock_sp.return_value
                sp_instance.analyze_blocks.return_value = []
                result = orch._run_semantic_parsing(doc)
        assert result.blocks[0].metadata.get("semantic_intent") is None


# ── Export document ─────────────────────────────────────────────────────────


class TestOrchestratorExport:
    def test_export_document(self, orch, tmp_path):
        doc = MagicMock()
        doc.output_path = None
        exporter_mock = MagicMock()
        with patch("app.pipeline.orchestrator.Exporter", return_value=exporter_mock), patch("os.makedirs"):
            with patch("os.path.abspath", return_value="/tmp/output/file_formatted.docx"):
                result = orch._export_document(doc, "/path/file.docx", "job1")
        assert result == "/tmp/output/file_formatted.docx"
        assert doc.output_path == "/tmp/output/file_formatted.docx"

    def test_export_document_check_stage_interface(self, orch):
        doc = MagicMock()
        with patch("app.pipeline.orchestrator.Exporter") as mock_exp:
            exporter = mock_exp.return_value
            del exporter.process
            with patch("os.makedirs"), pytest.raises(RuntimeError, match="Pipeline Stage Error"):
                orch._export_document(doc, "/path/file.docx", "job1")


# ── Run pipeline ────────────────────────────────────────────────────────────


class TestOrchestratorRunPipeline:
    def test_run_pipeline_busy_semaphore(self, orch):
        with patch("app.pipeline.orchestrator._pipeline_semaphore") as mock_sem:
            mock_sem.acquire.return_value = False
            with patch.object(orch, "_update_status"):
                result = orch.run_pipeline("/path/file.pdf", "job1")
        assert result["status"] == "failed"
        assert "busy" in result["reason"]

    def test_run_pipeline_success(self, orch):
        with patch.object(orch, "_run_pipeline_internal", return_value={"status": "success", "job_id": "job1"}):
            result = orch.run_pipeline("/path/file.pdf", "job1")
        assert result["status"] == "success"

    def test_run_pipeline_releases_semaphore(self, orch):
        with patch("app.pipeline.orchestrator._pipeline_semaphore") as mock_sem:
            mock_sem.acquire.return_value = True
            with patch.object(orch, "_run_pipeline_internal", return_value={}):
                orch.run_pipeline("/path/file.pdf", "job1")
        mock_sem.release.assert_called_once()

    def test_run_pipeline_releases_on_exception(self, orch):
        with patch("app.pipeline.orchestrator._pipeline_semaphore") as mock_sem:
            mock_sem.acquire.return_value = True
            with patch.object(orch, "_run_pipeline_internal", side_effect=Exception("fail")):
                with pytest.raises(Exception):
                    orch.run_pipeline("/path/file.pdf", "job1")
            mock_sem.release.assert_called_once()


# ── Run pipeline internal (complete flow) ───────────────────────────────────


class TestOrchestratorRunPipelineInternal:
    @patch("app.pipeline.orchestrator.ParserFactory")
    @patch("app.pipeline.orchestrator.get_supabase_client")
    def test_internal_flow_success(self, mock_sb, mock_pf, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.return_value = sb

        parser = MagicMock()
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Hello world"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()
        parser.parse.return_value = doc
        mock_pf.return_value.get_parser.return_value = parser

        with patch.object(orch, "_run_structure_detection", return_value=doc):
            with patch.object(orch, "_run_classification", return_value=doc):
                with patch.object(orch, "_run_validation_stage", return_value=doc):
                    with patch.object(orch, "_run_formatting_stage", return_value=doc):
                        with patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")):
                            with patch.object(orch, "analyzer"):
                                with patch.object(orch, "_update_status"):
                                    with patch(
                                        "app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc
                                    ):
                                        with patch("app.pipeline.orchestrator.CaptionMatcher"):
                                            with patch("app.pipeline.orchestrator.TableCaptionMatcher"):
                                                with patch("app.pipeline.orchestrator.ReferenceParser"):
                                                    with patch("app.pipeline.orchestrator.AIExplainer"):
                                                        with patch(
                                                            "app.pipeline.orchestrator.build_structured_data",
                                                            return_value={"data": "test"},
                                                        ):
                                                            with patch(
                                                                "app.pipeline.orchestrator.compute_quality_score",
                                                                return_value={"overall_score": 95.0},
                                                            ):
                                                                with patch.object(
                                                                    orch, "_compute_sha256", return_value="abc123"
                                                                ):
                                                                    with patch.object(orch, "_check_cancelled"):
                                                                        with patch(
                                                                            "app.pipeline.orchestrator.settings"
                                                                        ) as mock_set:
                                                                            mock_set.GROBID_ENABLED = False
                                                                            result = orch._run_pipeline_internal(
                                                                                str(input_path), "job1", "ieee", {}
                                                                            )
        assert result["status"] == "success"

    @patch("app.pipeline.orchestrator.ParserFactory")
    @patch("app.pipeline.orchestrator.get_supabase_client")
    def test_internal_failure_no_generated_doc(self, mock_sb, mock_pf, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = MagicMock()
        mock_sb.return_value = sb

        parser = MagicMock()
        doc = PipelineDocument(document_id="job1", blocks=[], metadata=DocumentMetadata())
        parser.parse.return_value = doc
        mock_pf.return_value.get_parser.return_value = parser

        with patch.object(orch, "_run_structure_detection", return_value=doc):
            with patch.object(orch, "_run_classification", return_value=doc):
                with patch.object(orch, "_run_validation_stage", return_value=doc):
                    with patch.object(orch, "_run_formatting_stage", return_value=doc):
                        with patch.object(orch, "_update_status"):
                            with patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc):
                                with patch("app.pipeline.orchestrator.CaptionMatcher"):
                                    with patch("app.pipeline.orchestrator.TableCaptionMatcher"):
                                        with patch("app.pipeline.orchestrator.ReferenceParser"):
                                            with patch(
                                                "app.pipeline.orchestrator.build_structured_data", return_value={}
                                            ):
                                                with patch(
                                                    "app.pipeline.orchestrator.compute_quality_score",
                                                    return_value={"overall_score": 0.0},
                                                ):
                                                    with patch.object(orch, "_check_cancelled"):
                                                        with patch("app.pipeline.orchestrator.settings") as mock_set:
                                                            mock_set.GROBID_ENABLED = False
                                                            result = orch._run_pipeline_internal(
                                                                str(input_path), "job1", "ieee", {}
                                                            )
        assert result["status"] == "processing"

    @patch("app.pipeline.orchestrator.ParserFactory")
    @patch("app.pipeline.orchestrator.get_supabase_client")
    def test_internal_fast_mode_disables_optional_stages(self, mock_sb, mock_pf, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = MagicMock()
        mock_sb.return_value = sb

        parser = MagicMock()
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Hello"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()
        parser.parse.return_value = doc
        mock_pf.return_value.get_parser.return_value = parser

        with patch.object(orch, "_run_structure_detection", return_value=doc):
            with patch.object(orch, "_run_classification", return_value=doc):
                with patch.object(orch, "_run_validation_stage", return_value=doc):
                    with patch.object(orch, "_run_formatting_stage", return_value=doc):
                        with patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")):
                            with patch.object(orch, "_update_status"):
                                with patch(
                                    "app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc
                                ):
                                    with patch("app.pipeline.orchestrator.CaptionMatcher"):
                                        with patch("app.pipeline.orchestrator.TableCaptionMatcher"):
                                            with patch("app.pipeline.orchestrator.ReferenceParser"):
                                                with patch("app.pipeline.orchestrator.AIExplainer"):
                                                    with patch(
                                                        "app.pipeline.orchestrator.build_structured_data",
                                                        return_value={},
                                                    ):
                                                        with patch(
                                                            "app.pipeline.orchestrator.compute_quality_score",
                                                            return_value={"overall_score": 90.0},
                                                        ):
                                                            with patch.object(
                                                                orch, "_compute_sha256", return_value="abc"
                                                            ):
                                                                with patch.object(orch, "_check_cancelled"):
                                                                    with patch(
                                                                        "app.pipeline.orchestrator.settings"
                                                                    ) as mock_set:
                                                                        mock_set.GROBID_ENABLED = False
                                                                        result = orch._run_pipeline_internal(
                                                                            str(input_path),
                                                                            "job1",
                                                                            "ieee",
                                                                            {"fast_mode": True},
                                                                        )
        assert result["status"] == "success"

    @patch("app.pipeline.orchestrator.ParserFactory")
    @patch("app.pipeline.orchestrator.get_supabase_client")
    def test_internal_nougat_fallback(self, mock_sb, mock_pf, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = MagicMock()
        mock_sb.return_value = sb

        parser = MagicMock()
        empty_doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text=""),
            ],
            metadata=DocumentMetadata(),
        )
        parser.parse.return_value = empty_doc
        mock_pf.return_value.get_parser.return_value = parser

        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Nougat content"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()

        with patch.object(orch, "_run_structure_detection", return_value=doc):
            with patch.object(orch, "_run_classification", return_value=doc):
                with patch.object(orch, "_run_validation_stage", return_value=doc):
                    with patch.object(orch, "_run_formatting_stage", return_value=doc):
                        with patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")):
                            with patch.object(orch, "_update_status"):
                                with patch(
                                    "app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc
                                ):
                                    with patch("app.pipeline.parsing.nougat_parser.NougatParser") as mock_np:
                                        nougat_doc = PipelineDocument(
                                            document_id="job1",
                                            blocks=[
                                                Block(
                                                    block_id="n1",
                                                    index=1,
                                                    block_type=BlockType.BODY,
                                                    text="Nougat content",
                                                ),
                                            ],
                                            metadata=DocumentMetadata(),
                                        )
                                        mock_np.return_value.parse.return_value = nougat_doc
                                        with patch("app.pipeline.orchestrator.CaptionMatcher"):
                                            with patch("app.pipeline.orchestrator.TableCaptionMatcher"):
                                                with patch("app.pipeline.orchestrator.ReferenceParser"):
                                                    with patch("app.pipeline.orchestrator.AIExplainer"):
                                                        with patch(
                                                            "app.pipeline.orchestrator.build_structured_data",
                                                            return_value={},
                                                        ):
                                                            with patch(
                                                                "app.pipeline.orchestrator.compute_quality_score",
                                                                return_value={"overall_score": 85.0},
                                                            ):
                                                                with patch.object(
                                                                    orch, "_compute_sha256", return_value="abc"
                                                                ):
                                                                    with patch.object(orch, "_check_cancelled"):
                                                                        with patch(
                                                                            "app.pipeline.orchestrator.settings"
                                                                        ) as mock_set:
                                                                            mock_set.GROBID_ENABLED = False
                                                                            result = orch._run_pipeline_internal(
                                                                                str(input_path), "job1", "ieee", {}
                                                                            )
        assert result["status"] == "success"

    @patch("app.pipeline.orchestrator.ParserFactory")
    @patch("app.pipeline.orchestrator.get_supabase_client")
    def test_internal_cancelled_error(self, mock_sb, mock_pf, orch, tmp_path):
        import asyncio

        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        sb = MagicMock()
        mock_sb.return_value = sb

        parser = MagicMock()
        parser.parse.side_effect = asyncio.CancelledError("cancelled")
        mock_pf.return_value.get_parser.return_value = parser
        with patch.object(orch, "_update_status"):
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "cancelled"


# ── Run edit flow ───────────────────────────────────────────────────────────


class TestOrchestratorEditFlow:
    def test_edit_flow_success(self, orch, tmp_path):
        sb = MagicMock()
        execute_results = iter(
            [
                MagicMock(data=[{"filename": "test.docx", "output_path": "/original/output.docx"}]),
                MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
                MagicMock(data=[{"version_number": "v2"}]),
                MagicMock(),
                MagicMock(),
            ]
        )
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = execute_results

        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            fmt_instance = mock_fmt.return_value
                            pipeline_doc = MagicMock()
                            pipeline_doc.generated_doc = MagicMock()
                            fmt_instance.process.return_value = pipeline_doc
                            with patch("app.pipeline.orchestrator.Exporter"):
                                with patch("os.makedirs"):
                                    with patch("os.path.splitext", return_value=("test", ".docx")):
                                        with patch("os.path.abspath", return_value="/tmp/output/test_edited.docx"):
                                            with patch.object(orch, "_compute_sha256", return_value="hash"):
                                                result = orch.run_edit_flow(
                                                    "job1", {"sections": {"body": ["Edited text"]}}, "ieee"
                                                )
        assert result["status"] == "success"

    def test_edit_flow_no_supabase(self, orch):
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"

    def test_edit_flow_no_original(self, orch):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"

    def test_edit_flow_cancelled(self, orch):
        import asyncio

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = asyncio.CancelledError("cancel")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.object(orch, "_update_status"):
                result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "cancelled"

    def test_edit_flow_no_existing_result(self, orch):
        sb = MagicMock()
        execute_results = iter(
            [
                MagicMock(data=[{"filename": "test.docx", "output_path": "/original/output.docx"}]),
                MagicMock(data=[]),
                MagicMock(),
                MagicMock(),
            ]
        )
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = execute_results

        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                    mock_val.return_value = MagicMock()
                    with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                        with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                            fmt_instance = mock_fmt.return_value
                            pipeline_doc = MagicMock()
                            pipeline_doc.generated_doc = MagicMock()
                            fmt_instance.process.return_value = pipeline_doc
                            with patch("app.pipeline.orchestrator.Exporter"):
                                with patch("app.pipeline.orchestrator.AIExplainer"):
                                    with patch("os.makedirs"):
                                        with patch("os.path.splitext", return_value=("test", ".docx")):
                                            with patch("os.path.abspath", return_value="/tmp/output/test_edited.docx"):
                                                with patch.object(orch, "_compute_sha256", return_value="hash"):
                                                    result = orch.run_edit_flow(
                                                        "job1", {"sections": {"body": ["Text"]}}, "ieee"
                                                    )
        assert result["status"] == "success"
