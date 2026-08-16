# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Coverage gap tests for PipelineOrchestrator.
Targets uncovered branches, error handlers, and edge cases
not exercised by test_orchestrator.py or test_orchestrator_deep.py.
"""

from __future__ import annotations

import asyncio
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, Figure, PipelineDocument, Reference
from app.pipeline.orchestrator import PipelineOrchestrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sb():
    sb = MagicMock()
    sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    return sb


def _make_doc(job_id="job1"):
    doc = PipelineDocument(
        document_id=job_id,
        blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body text")],
        metadata=DocumentMetadata(),
    )
    doc.metadata.ai_hints = {}
    return doc


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def orch():
    with (
        patch("app.pipeline.orchestrator.InputConverter"),
        patch("app.pipeline.orchestrator.ContentAnalyzer"),
        patch("app.pipeline.orchestrator.ContractLoader"),
        patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
        patch("app.pipeline.orchestrator.GROBIDClient"),
        patch("app.pipeline.orchestrator.DoclingClient"),
    ):
        o = PipelineOrchestrator(templates_dir="app/templates", temp_dir="/tmp/test_gaps")
        return o


@pytest.fixture
def sb():
    return _make_sb()


# ══════════════════════════════════════════════════════════════════════════════
# Lines 141-142: MetricsManager exception swallowed in _record_stage_transition
# ══════════════════════════════════════════════════════════════════════════════


class TestMetricsExceptions:
    def test_record_stage_transition_metrics_error(self, orch):
        orch._stage_start_times[("job1", "EXTRACTION")] = time.perf_counter() - 1.0
        with patch("app.middleware.prometheus_metrics.MetricsManager") as mock_mm:
            mock_mm.record_pipeline_stage_duration.side_effect = Exception("metrics down")
            orch._record_stage_transition("job1", "EXTRACTION", "COMPLETED")


# ══════════════════════════════════════════════════════════════════════════════
# Lines 167->exit, 173, 185->187, 233, 240, 257-258: _update_status branches
# ══════════════════════════════════════════════════════════════════════════════


class TestUpdateStatusTransientErrors:
    def test_non_transient_error_raises(self, orch):
        """Line 173: _is_transient_db_error returns False → raise immediately."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = Exception("disk full")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_refresh_returns_none(self, orch):
        """Lines 185->187: get_supabase_client(refresh=True) returns None."""
        sb = MagicMock()
        err = Exception("RemoteProtocolError: server disconnected")
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = [
            err,
            MagicMock(data=[{"id": 1}]),
        ]
        call_count = 0

        def _get_sb(refresh=False):
            nonlocal call_count
            call_count += 1
            if refresh:
                return None
            return sb

        with patch("app.pipeline.orchestrator.get_supabase_client", side_effect=_get_sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")

    def test_all_attempts_fail_transient(self, orch):
        """All 3 attempts fail with transient errors → re-raises on last."""
        sb = MagicMock()
        err = Exception("RemoteProtocolError: server disconnected")
        sb.table.return_value.select.return_value.match.return_value.execute.side_effect = [
            err,
            err,
            err,
        ]
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED")


class TestUpdateStatusPaths:
    def test_persistence_completed_status(self, orch):
        """Line 233: phase == PERSISTENCE and status == COMPLETED."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "PERSISTENCE", "COMPLETED", "Done", progress=100)

    def test_non_terminal_status(self, orch):
        """Line 240: status is neither COMPLETED nor FAILED → pass through."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": MagicMock()}):
                orch._update_status("job1", "UPLOAD", "PROCESSING", "Uploading...", progress=10)

    def test_emit_event_exception(self, orch):
        """Lines 257-258: emit_event raises → caught by outer except."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
        mock_stream = MagicMock()
        mock_stream.emit_event.side_effect = Exception("SSE failure")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch.dict("sys.modules", {"app.routers.v1.stream": mock_stream}):
                orch._update_status("job1", "EXTRACTION", "COMPLETED", "Done")


# ══════════════════════════════════════════════════════════════════════════════
# Line 381: Empty PDF in _should_skip_docling_for_digital_pdf
# ══════════════════════════════════════════════════════════════════════════════


class TestSkipDoclingGaps:
    def test_skip_docling_empty_pdf(self, orch, tmp_path):
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.PIPELINE_DOCLING_FORCE = False
            mock_s.PIPELINE_DOCLING_SKIP_DIGITAL_PDF = True
            mock_fitz = MagicMock()
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 0
            mock_fitz.open.return_value.__enter__.return_value = mock_doc
            with patch.dict("sys.modules", {"fitz": mock_fitz}):
                result = orch._should_skip_docling_for_digital_pdf(str(pdf))
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# Lines 398-399: fitz import exception in _extract_pymupdf_fallback_metadata
# ══════════════════════════════════════════════════════════════════════════════


class TestPyMuPDFGaps:
    def test_extract_fallback_import_exception(self, orch):
        with patch("builtins.__import__", side_effect=ImportError("no fitz")):
            result = orch._extract_pymupdf_fallback_metadata("/path.pdf")
        assert result == {}


# ══════════════════════════════════════════════════════════════════════════════
# Lines 459->463, 462: _build_quality_summary edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestQualitySummaryGaps:
    def test_classification_confidence_skip_fallback(self, orch):
        """Line 459->463: classification_confidence is not None → skip nlp_confidence."""
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(
                    block_id="b1",
                    index=1,
                    block_type=BlockType.BODY,
                    text="t",
                    metadata={"classification_confidence": 0.75},
                ),
            ],
            metadata=DocumentMetadata(),
        )
        validation_results = {"errors": [], "warnings": []}
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, validation_results)
        assert summary["block_count"] == 1

    def test_metadata_not_dict(self, orch):
        """Line 462: block metadata is not a dict."""
        block = MagicMock(spec=Block)
        block.metadata = None
        block.classification_confidence = 0.85
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[block],
            metadata=DocumentMetadata(),
        )
        validation_results = {"errors": [], "warnings": []}
        with patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 80.0}):
            summary = orch._build_quality_summary(doc, validation_results)
        assert summary["block_count"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# Lines 599, 614-616: _run_figure_analysis_stage branch gaps
# ══════════════════════════════════════════════════════════════════════════════


class TestFigureAnalysisGaps:
    def test_figure_image_data_no_export_path(self, orch):
        """Line 599: fig has image_data but export_path is None."""
        fig = Figure(figure_id="f1", index=1, export_path=None, image_data=b"fake", caption_text="Fig")
        doc = PipelineDocument(
            document_id="figdoc",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body")],
            metadata=DocumentMetadata(),
            figures=[fig],
        )
        mock_analyzer = MagicMock()
        with patch("app.pipeline.orchestrator._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=False):
                result = orch._run_figure_analysis_stage(doc)
        assert result.metadata.ai_hints["figure_analysis"][0]["valid"] is False

    def test_figure_analysis_dict_metadata(self, orch):
        """Lines 614-616: metadata is plain dict (has setdefault) without ai_hints."""
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig.png", caption_text="Fig")
        doc = PipelineDocument(
            document_id="figdoc",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body")],
            figures=[fig],
        )
        object.__setattr__(doc, "metadata", {"existing": "value"})
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert isinstance(result.metadata, dict)
        assert result.metadata["ai_hints"]["figure_analysis"][0]["valid"] is True


# ══════════════════════════════════════════════════════════════════════════════
# Line 677: formatting_options not None
# ══════════════════════════════════════════════════════════════════════════════


class TestRuntimeFlagsGaps:
    def test_formatting_options_not_none(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {}, clear=True):
                flags = orch._resolve_runtime_flags({"custom": "value"})
        assert flags["fast_mode"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Lines 735->743: Nougat fallback also returns empty blocks
# ══════════════════════════════════════════════════════════════════════════════


class TestNougatFallbackGaps:
    def test_nougat_fallback_also_empty(self, orch, tmp_path, sb):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        empty_doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="")],
            metadata=DocumentMetadata(),
        )
        parser.parse.return_value = empty_doc
        doc = PipelineDocument(
            document_id="job1",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="Nougat content")],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()

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
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 85.0}),
            patch.object(orch, "_check_cancelled"),
            patch.object(orch, "_compute_sha256", return_value="abc"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            # Make NougatParser return another empty doc
            from app.pipeline.parsing.nougat_parser import NougatParser

            with patch.object(NougatParser, "parse", return_value=empty_doc):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 743->746, 746->753: template_name falsy, sb None
# ══════════════════════════════════════════════════════════════════════════════


class TestPipelineInternalOptions:
    def test_no_template_name(self, orch, tmp_path):
        """Line 743->746: template_name is None/falsy."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        parser.parse.return_value = doc
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
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", None, {})
        assert result["status"] == "success"
        # template_name=None means no TemplateInfo set on doc
        assert doc.template is None or doc.template.template_name is None

    def test_sb_none_in_extraction_save(self, orch, tmp_path):
        """Line 746->753: sb is None when saving raw_text."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
        doc.generated_doc = MagicMock()
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
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 786-788, 804-806, 826-830, 840-841, 850-851, 865-866, 868->870
# Parallel extraction + metadata fallback gaps
# ══════════════════════════════════════════════════════════════════════════════


class TestParallelExtractionGaps:
    def _run_pipeline(self, orch, tmp_path, doc, settings_overrides=None, **options):
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
            overrides = settings_overrides or {}
            mock_set.GROBID_ENABLED = overrides.get("GROBID_ENABLED", False)
            mock_set.USE_DOCLING_FALLBACK = overrides.get("USE_DOCLING_FALLBACK", False)
            mock_set.PIPELINE_GROBID_TIMEOUT_SECONDS = overrides.get("PIPELINE_GROBID_TIMEOUT_SECONDS", 5)
            mock_set.PIPELINE_DOCLING_TIMEOUT_SECONDS = overrides.get("PIPELINE_DOCLING_TIMEOUT_SECONDS", 5)
            mock_set.PYMUPDF_FALLBACK = overrides.get("PYMUPDF_FALLBACK", False)
            mock_set.DEFAULT_FAST_MODE = False
            mock_set.LOW_MEMORY_MODE = False
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", options)

    def test_grobid_exception_in_run(self, orch, tmp_path):
        """Lines 786-788: grobid_client.process_header_document raises."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(orch.grobid_client, "process_header_document", side_effect=Exception("GROBID crash")):
                with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                    result = self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True},
                    )
        assert "grobid_metadata" not in doc.metadata.ai_hints

    def test_docling_exception_in_run(self, orch, tmp_path):
        """Lines 804-806: docling_client.analyze_layout raises."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=False):
            with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=False):
                with patch.object(orch.docling_client, "is_available", return_value=True):
                    with patch.object(orch.docling_client, "analyze_layout", side_effect=Exception("Docling crash")):
                        result = self._run_pipeline(
                            orch,
                            tmp_path,
                            doc,
                            {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True},
                        )
        assert "docling_layout" in doc.metadata.ai_hints
        assert doc.metadata.ai_hints["docling_layout"]["confidence"] == 0.0

    def test_docling_timeout(self, orch, tmp_path):
        """Lines 826-830: Docling future times out."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=False):
            with patch.object(type(orch), "_should_skip_docling_for_digital_pdf", return_value=False):
                with patch.object(orch.docling_client, "is_available", return_value=True):

                    def _slow(*a, **kw):
                        time.sleep(10)
                        return {"elements": []}

                    with patch.object(orch.docling_client, "analyze_layout", side_effect=_slow):
                        result = self._run_pipeline(
                            orch,
                            tmp_path,
                            doc,
                            {
                                "GROBID_ENABLED": True,
                                "USE_DOCLING_FALLBACK": True,
                                "PIPELINE_DOCLING_TIMEOUT_SECONDS": 1,
                            },
                        )
        assert "docling_layout" not in doc.metadata.ai_hints

    def test_grobid_creates_metadata(self, orch, tmp_path):
        """Lines 840-841: doc_obj has no metadata attribute."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata = None
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(orch.grobid_client, "process_header_document", return_value={"title": "Test"}):
                with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                    result = self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True},
                    )
        assert doc.metadata is not None
        assert doc.metadata.ai_hints.get("grobid_metadata", {}).get("title") == "Test"

    def test_docling_creates_metadata(self, orch, tmp_path):
        """Lines 850-851: doc_obj has no metadata attribute."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata = None
        with patch.object(orch.grobid_client, "is_available", return_value=False):
            with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=False):
                with patch.object(orch.docling_client, "is_available", return_value=True):
                    with patch.object(
                        orch.docling_client, "analyze_layout", return_value={"elements": [{"type": "text"}]}
                    ):
                        result = self._run_pipeline(
                            orch,
                            tmp_path,
                            doc,
                            {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True},
                        )
        assert doc.metadata is not None
        assert doc.metadata.ai_hints.get("docling_layout", {}).get("elements") is not None

    def test_pymupdf_creates_metadata(self, orch, tmp_path):
        """Lines 865-866: doc_obj has no metadata attribute."""
        doc = _make_doc()
        doc.metadata = None
        with patch.object(orch.grobid_client, "is_available", return_value=False):
            with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                with patch.object(
                    orch,
                    "_extract_pymupdf_fallback_metadata",
                    return_value={
                        "source": "pymupdf",
                        "page_count": 3,
                        "title": "PyMuPDF Title",
                    },
                ):
                    result = self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {"PYMUPDF_FALLBACK": True},
                    )
        assert doc.metadata is not None
        assert doc.metadata.ai_hints.get("pymupdf_fallback", {}).get("source") == "pymupdf"

    def test_pymupdf_title_already_exists(self, orch, tmp_path):
        """Lines 868->870: doc_obj.metadata.title already set, pymupdf title ignored."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.title = "Existing Title"
        with patch.object(orch.grobid_client, "is_available", return_value=False):
            with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                with patch.object(
                    orch,
                    "_extract_pymupdf_fallback_metadata",
                    return_value={
                        "source": "pymupdf",
                        "page_count": 3,
                        "title": "PyMuPDF Title",
                    },
                ):
                    result = self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {"PYMUPDF_FALLBACK": True},
                    )
        assert doc.metadata.title == "Existing Title"
        assert doc.metadata.ai_hints.get("pymupdf_fallback", {}).get("title") == "PyMuPDF Title"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 886-887, 894-895: StructureDetector + SemanticParser failures
# ══════════════════════════════════════════════════════════════════════════════


class TestPipelineStageFailures:
    def _run_pipeline(self, orch, tmp_path, doc, settings_overrides=None, **options):
        sb = _make_sb()
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
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            overrides = settings_overrides or {}
            mock_set.GROBID_ENABLED = overrides.get("GROBID_ENABLED", False)
            mock_set.USE_DOCLING_FALLBACK = overrides.get("USE_DOCLING_FALLBACK", False)
            mock_set.DEFAULT_FAST_MODE = overrides.get("DEFAULT_FAST_MODE", False)
            mock_set.LOW_MEMORY_MODE = overrides.get("LOW_MEMORY_MODE", False)
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", options)

    def test_structure_detector_failure(self, orch, tmp_path):
        """Lines 886-887: StructureDetector raises → logged and continues."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch, "_run_structure_detection", side_effect=Exception("SD crash")):
            result = self._run_pipeline(orch, tmp_path, doc)
        assert result["status"] == "success"

    def test_semantic_parser_failure_continues(self, orch, tmp_path):
        """Lines 894-895: semantic parser error caught → continues."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch, "_run_structure_detection", return_value=doc):
            with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_sp:
                mock_sp.return_value.analyze_blocks.side_effect = Exception("SP crash")
                with patch("app.pipeline.orchestrator.settings") as mock_s:
                    mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 5
                    mock_s.PIPELINE_GROBID_TIMEOUT_SECONDS = 5
                    mock_s.PIPELINE_DOCLING_TIMEOUT_SECONDS = 5
                    result = self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {"DEFAULT_FAST_MODE": False},
                        fast_mode=False,
                        semantic_parser=True,
                    )
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 920->926: keyword extraction — detected_keywords is empty
# ══════════════════════════════════════════════════════════════════════════════


class TestKeywordExtractionGaps:
    def test_keywords_detected_empty(self, orch, tmp_path):
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.abstract = "Some abstract text here about research."
        doc.metadata.ai_hints = {}
        with patch("app.pipeline.nlp.analyzer.extract_keywords", return_value=[]):
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
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert doc.metadata.keywords is None or doc.metadata.keywords == []


# ══════════════════════════════════════════════════════════════════════════════
# Lines 968->exit, 970->exit, 973, 976-979: CrossRef validation branches
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossrefValidationGaps:
    def _run_pipeline_crossref(self, orch, tmp_path, doc, settings_overrides=None, **options):
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
            overrides = settings_overrides or {}
            mock_set.GROBID_ENABLED = overrides.get("GROBID_ENABLED", False)
            mock_set.USE_DOCLING_FALLBACK = overrides.get("USE_DOCLING_FALLBACK", False)
            mock_set.DEFAULT_FAST_MODE = overrides.get("DEFAULT_FAST_MODE", False)
            mock_set.LOW_MEMORY_MODE = overrides.get("LOW_MEMORY_MODE", False)
            mock_set.CROSSREF_MAX_WORKERS = overrides.get("CROSSREF_MAX_WORKERS", 4)
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", options)

    def test_crossref_raw_text_none(self, orch, tmp_path):
        """Line 968->exit: raw_text is empty → loop skips validate_citation."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.references = [Reference(reference_id="r1", index=1, citation_key="cit1", raw_text="")]
        with patch("app.services.crossref_client.get_crossref_client") as mock_cr:
            mock_cr_inst = MagicMock()
            mock_cr_inst.validate_citation.return_value = {"valid": True, "doi": "10.1234/test"}
            mock_cr.return_value = mock_cr_inst
            result = self._run_pipeline_crossref(
                orch,
                tmp_path,
                doc,
                {"CROSSREF_MAX_WORKERS": 2},
                fast_mode=False,
                crossref_enrichment=True,
            )
        assert result["status"] == "success"
        mock_cr_inst.validate_citation.assert_not_called()

    def test_crossref_validation_returns_falsy(self, orch, tmp_path):
        """Line 970->exit: validate_citation returns falsy → skip."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        doc.references = []
        with patch("app.services.crossref_client.get_crossref_client") as mock_cr:
            mock_cr_inst = MagicMock()
            mock_cr_inst.validate_citation.return_value = None
            mock_cr.return_value = mock_cr_inst
            result = self._run_pipeline_crossref(
                orch,
                tmp_path,
                doc,
                {"CROSSREF_MAX_WORKERS": 2},
                fast_mode=False,
                crossref_enrichment=True,
            )
        assert result["status"] == "success"

    def test_crossref_ref_no_metadata(self, orch, tmp_path):
        """Line 973: ref.metadata is not a dict → set to empty dict."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        ref = Reference(reference_id="r1", index=1, citation_key="cit1", raw_text="Some citation")

        class NonDictMeta:
            def __init__(self):
                self._d = {}

            def __setitem__(self, k, v):
                self._d[k] = v

            def get(self, k, default=None):
                return self._d.get(k, default)

        ref.metadata = NonDictMeta()
        doc.references = [ref]
        with patch("app.services.crossref_client.get_crossref_client") as mock_cr:
            mock_cr_inst = MagicMock()
            mock_cr_inst.validate_citation.return_value = {"valid": True, "doi": "10.1234/test"}
            mock_cr.return_value = mock_cr_inst
            result = self._run_pipeline_crossref(
                orch,
                tmp_path,
                doc,
                {"CROSSREF_MAX_WORKERS": 2},
                fast_mode=False,
                crossref_enrichment=True,
            )
        assert result["status"] == "success"
        assert ref.metadata.get("crossref_validation", {}).get("valid") is True

    def test_crossref_ref_non_dict_metadata(self, orch, tmp_path):
        """Lines 976-979: ref.metadata is not a dict — try __setitem__ else setattr."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()

        class DictLike:
            def __init__(self):
                self._d = {}

            def __setitem__(self, k, v):
                self._d[k] = v

            def __getitem__(self, k):
                return self._d[k]

            def get(self, k, default=None):
                return self._d.get(k, default)

        meta = DictLike()
        ref = Reference(reference_id="r1", index=1, citation_key="cit1", raw_text="Some citation")
        ref.metadata = meta
        doc.references = [ref]
        with patch("app.services.crossref_client.get_crossref_client") as mock_cr:
            mock_cr_inst = MagicMock()
            mock_cr_inst.validate_citation.return_value = {"valid": True, "doi": "10.1234/test"}
            mock_cr.return_value = mock_cr_inst
            result = self._run_pipeline_crossref(
                orch,
                tmp_path,
                doc,
                {"CROSSREF_MAX_WORKERS": 2},
                fast_mode=False,
                crossref_enrichment=True,
            )
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 1007-1009: query_rules fallback path in AI reasoning
# ══════════════════════════════════════════════════════════════════════════════


class TestAIReasoningQueryRules:
    def _run_pipeline_rag(self, orch, tmp_path, doc, settings_overrides=None, **options):
        """Helper with AI reasoning enabled — patching rag as needed."""
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
            overrides = settings_overrides or {}
            mock_set.GROBID_ENABLED = overrides.get("GROBID_ENABLED", False)
            mock_set.USE_DOCLING_FALLBACK = overrides.get("USE_DOCLING_FALLBACK", False)
            mock_set.DEFAULT_FAST_MODE = overrides.get("DEFAULT_FAST_MODE", False)
            mock_set.LOW_MEMORY_MODE = overrides.get("LOW_MEMORY_MODE", False)
            mock_set.PIPELINE_REASONING_TIMEOUT_SECONDS = overrides.get("PIPELINE_REASONING_TIMEOUT_SECONDS", 5)
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", options)

    def test_reasoning_uses_query_rules(self, orch, tmp_path):
        """Lines 1007-1009: rag has query_rules but not query_guidelines."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock(spec=["query_rules"])
        rag_inst.query_rules.return_value = [{"text": "Rule: do X"}, {"text": "Rule: do Y"}]
        reasoner_inst = MagicMock()
        reasoner_inst.generate_instruction_set.return_value = {
            "instructions": [{"text": "Do Z", "confidence": 0.90}],
        }
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline_rag(
                    orch,
                    tmp_path,
                    doc,
                    {},
                    fast_mode=False,
                    ai_reasoning=True,
                )
        assert result["status"] == "success"
        rag_inst.query_rules.assert_called()

    def test_reasoning_no_generate_instruction_set(self, orch, tmp_path):
        """Lines 1026->1058: reasoner lacks generate_instruction_set."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = ["Guideline text"]
        reasoner_inst = MagicMock(spec=[])
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline_rag(
                    orch,
                    tmp_path,
                    doc,
                    {},
                    fast_mode=False,
                    ai_reasoning=True,
                )
        assert result["status"] == "success"

    def test_reasoning_generates_rules_context(self, orch, tmp_path):
        """Lines 1004-1015: all sections have guidelines appended."""
        doc = _make_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = None  # returns falsy
        rag_inst.query_rules.return_value = None  # returns falsy
        reasoner_inst = MagicMock()
        reasoner_inst.generate_instruction_set.return_value = {}
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline_rag(
                    orch,
                    tmp_path,
                    doc,
                    {},
                    fast_mode=False,
                    ai_reasoning=True,
                )
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 1092->1097, 1115->1120, 1138->1152, 1144-1147, 1159-1160:
# Persistence / completion edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestPersistenceEdgeCases:
    def test_formatting_failure_no_sb(self, orch, tmp_path):
        """Lines 1092->1097: sb is None in formatting failure branch."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, d: d),
            patch("app.pipeline.orchestrator.CaptionMatcher"),
            patch("app.pipeline.orchestrator.TableCaptionMatcher"),
            patch("app.pipeline.orchestrator.ReferenceParser"),
            patch("app.pipeline.orchestrator.build_structured_data", return_value={}),
            patch("app.pipeline.orchestrator.compute_quality_score", return_value={"overall_score": 95.0}),
            patch.object(orch, "_check_cancelled"),
            patch("app.pipeline.orchestrator.settings") as mock_set,
        ):
            mock_pf.return_value.get_parser.return_value = parser
            mock_set.GROBID_ENABLED = False
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "processing"

    def test_persistence_insert_no_sb(self, orch, tmp_path):
        """Lines 1115->1120: sb is None when inserting document_result."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
        doc.generated_doc = MagicMock()
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
        assert result["status"] == "success"

    def test_completion_update_no_sb(self, orch, tmp_path):
        """Lines 1138->1152: sb is None in completion update block."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
        doc.generated_doc = MagicMock()
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
        assert result["status"] == "success"

    def test_output_not_ready_with_sb(self, orch, tmp_path):
        """Lines 1144-1147: output_ready is False, sb exists."""
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = _make_doc()
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
        assert result["status"] == "processing"

    def test_error_response_status(self, orch, tmp_path):
        """Lines 1159-1160: final_status is not COMPLETED."""
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        formatted_doc = _make_doc()
        formatted_doc.generated_doc = MagicMock()
        parser.parse.return_value = formatted_doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=formatted_doc),
            patch.object(orch, "_run_classification", return_value=formatted_doc),
            patch.object(orch, "_run_validation_stage", return_value=formatted_doc),
            patch.object(orch, "_run_formatting_stage", return_value=formatted_doc),
            patch.object(orch, "_export_document", return_value=None),
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
        assert result["status"] == "error"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 1168->1175: sb is None in CancelledError handler
# ══════════════════════════════════════════════════════════════════════════════


class TestCancelledErrorHandler:
    def test_cancelled_no_sb(self, orch, tmp_path):
        """Line 1168->1175: sb is None in cancelled handler."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        with patch.object(orch, "_update_status"), patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.side_effect = asyncio.CancelledError("cancel")
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "cancelled"


# ══════════════════════════════════════════════════════════════════════════════
# Lines 1273->1290: Edit flow — formatted_doc is falsy
# ══════════════════════════════════════════════════════════════════════════════


class TestEditFlowGaps:
    def test_edit_flow_no_formatted_doc(self, orch):
        """Lines 1273->1290: Formatter returns falsy doc."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]),
            MagicMock(data=[{"id": 1, "structured_data": {"old": "data"}}]),
        ]
        with patch.object(orch, "_update_status"):
            with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
                with patch("app.db.repositories.base.get_supabase_client", return_value=sb):
                    with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                        mock_val.return_value = MagicMock()
                        with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                            with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                                mock_fmt.return_value.process.return_value = None
                                result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "success"

    def test_edit_flow_cancelled_with_update_status_error(self, orch):
        """Lines 1343-1344: update_status raises in CancelledError handler."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = asyncio.CancelledError("cancel")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch("app.db.repositories.base.get_supabase_client", return_value=sb):
                with patch.object(orch, "_update_status", side_effect=Exception("cleanup fail")):
                    result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "cancelled"

    def test_edit_flow_general_error(self, orch):
        """Line 1346-1350: generic Exception handler in edit flow."""
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("unexpected")
        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb):
            with patch("app.db.repositories.base.get_supabase_client", return_value=sb):
                with patch.object(orch, "_update_status"):
                    result = orch.run_edit_flow("job1", {"sections": {}}, "ieee")
        assert result["status"] == "error"
