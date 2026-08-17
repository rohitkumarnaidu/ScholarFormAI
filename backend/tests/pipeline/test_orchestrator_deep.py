# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep integration tests for PipelineOrchestrator — covers error paths,
parallel extraction, figure analysis, keyword extraction, completion logic,
and edge cases not exercised by the base test suite.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType, DocumentMetadata, Figure, PipelineDocument, Reference
from app.pipeline.orchestrator import PipelineOrchestrator


@pytest.fixture
def orch():

    with (
        patch("app.pipeline.orchestrator.InputConverter"),
        patch("app.pipeline.orchestrator.ContentAnalyzer"),
        patch("app.pipeline.orchestrator.ContractLoader"),
        patch("app.pipeline.orchestrator.ReferenceFormatterEngine"),
        patch("app.pipeline.orchestrator.GROBIDClient"),
        patch("app.pipeline.orchestrator.DoclingClient"),
        patch("app.pipeline.orchestrator.orchestrator.DocumentRepository"),
        patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository"),
        patch("app.pipeline.orchestrator.orchestrator.ProcessingStatusRepository"),
        patch("app.pipeline.orchestrator.phases.DocumentRepository"),
        patch("app.pipeline.orchestrator.phases.DocumentResultRepository"),
    ):
        o = PipelineOrchestrator(templates_dir="app/templates", temp_dir="/tmp/test_temp_deep")
        return o


def _make_sb():
    sb = MagicMock()
    sb.table.return_value.select.return_value.match.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    return sb


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1a: Figure Analysis Stage
# ══════════════════════════════════════════════════════════════════════════════


class TestFigureAnalysisStage:
    def _make_doc(self, figures=None):
        return PipelineDocument(
            document_id="figdoc",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body")],
            metadata=DocumentMetadata(),
            figures=figures or [],
        )

    def test_figure_analysis_success(self, orch):
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig1.png", caption_text="Fig 1")
        doc = self._make_doc([fig])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True, "resolution": 300}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert result is doc
        assert "figure_analysis" in result.metadata.ai_hints
        assert len(result.metadata.ai_hints["figure_analysis"]) == 1

    def test_figure_analysis_no_path(self, orch):
        fig = Figure(figure_id="f3", index=1, export_path=None, caption_text="No path")
        doc = self._make_doc([fig])
        mock_analyzer = MagicMock()
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=False):
                result = orch._run_figure_analysis_stage(doc)
        analysis = result.metadata.ai_hints["figure_analysis"]
        assert analysis[0]["valid"] is False
        assert "No export path" in analysis[0]["error"]

    def test_figure_analysis_downsample(self, orch):
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig1.png", caption_text="Fig 1")
        doc = self._make_doc([fig])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = "/tmp/downsampled_fig1.png"
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert result.figures[0].export_path == "/tmp/downsampled_fig1.png"

    def test_figure_analysis_no_figures(self, orch):
        doc = self._make_doc([])
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer") as mock_get:
            orch._run_figure_analysis_stage(doc)
        mock_get.return_value.analyze_image.assert_not_called()
        assert "figure_analysis" not in doc.metadata.ai_hints

    def test_figure_analysis_error_is_handled(self, orch):
        """safe_execution catches the error and returns None."""
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig1.png", caption_text="Fig 1")
        doc = self._make_doc([fig])
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.side_effect = Exception("analysis failed")
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert result is None

    def test_figure_analysis_with_image_data(self, orch):
        fig = Figure(figure_id="f_img", index=1, export_path="/tmp/img.png", image_data=b"fake", caption_text="X")
        doc = self._make_doc([fig])
        mock_analyzer = MagicMock()
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=False):
                result = orch._run_figure_analysis_stage(doc)
        assert result.metadata.ai_hints["figure_analysis"][0]["valid"] is False

    def test_figure_analysis_already_has_ai_hints(self, orch):
        fig = Figure(figure_id="f1", index=1, export_path="/tmp/fig1.png", caption_text="Fig 1")
        meta = DocumentMetadata()
        meta.ai_hints = {"existing": "value"}
        doc = PipelineDocument(
            document_id="meta_attr",
            blocks=[Block(block_id="b1", index=1, block_type=BlockType.BODY, text="x")],
            metadata=meta,
            figures=[fig],
        )
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_image.return_value = {"valid": True}
        mock_analyzer.downsample_if_needed.return_value = None
        with patch("app.pipeline.orchestrator.stages._get_figure_analyzer", return_value=mock_analyzer):
            with patch("os.path.exists", return_value=True):
                result = orch._run_figure_analysis_stage(doc)
        assert result.metadata.ai_hints["existing"] == "value"
        assert result.metadata.ai_hints["figure_analysis"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1b: Semantic parser error paths
# ══════════════════════════════════════════════════════════════════════════════


class TestSemanticParserErrors:
    def _make_doc(self):
        return PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="test"),
            ],
            metadata=DocumentMetadata(),
        )

    def test_semantic_parser_timeout(self, orch):
        doc = self._make_doc()
        with patch.object(orch, "_run_with_timeout", side_effect=TimeoutError("timed out")):
            with patch("app.pipeline.orchestrator.settings") as mock_s:
                mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 1
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser"):
                    with pytest.raises(TimeoutError):
                        orch._run_semantic_parsing(doc)

    def test_semantic_parser_generic_error(self, orch):
        doc = self._make_doc()
        with patch.object(orch, "_run_with_timeout", side_effect=Exception("unknown error")):
            with patch("app.pipeline.orchestrator.settings") as mock_s:
                mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 1
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser"):
                    with pytest.raises(Exception):
                        orch._run_semantic_parsing(doc)

    def test_semantic_parser_empty_results(self, orch):
        doc = self._make_doc()
        with patch.object(orch, "_run_with_timeout", return_value=[]):
            with patch("app.pipeline.orchestrator.settings") as mock_s:
                mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 1
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser"):
                    result = orch._run_semantic_parsing(doc)
        assert result.blocks[0].metadata.get("semantic_intent") is None

    def test_semantic_parser_partial_results(self, orch):
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="a"),
                Block(block_id="b2", index=2, block_type=BlockType.BODY, text="b"),
            ],
            metadata=DocumentMetadata(),
        )
        results = [{"predicted_section_type": "introduction", "confidence_score": 0.9}]
        with patch.object(orch, "_run_with_timeout", return_value=results):
            with patch("app.pipeline.orchestrator.settings") as mock_s:
                mock_s.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 1
                with patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser"):
                    result = orch._run_semantic_parsing(doc)
        assert result.blocks[0].metadata["semantic_intent"] == "introduction"
        assert result.blocks[1].metadata.get("semantic_intent") is None


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1c: Runtime flags edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestRuntimeFlagsEdgeCases:
    def test_flags_all_false(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags(
                {
                    "fast_mode": False,
                    "semantic_parser": False,
                    "crossref_enrichment": False,
                    "ai_reasoning": False,
                }
            )
        assert flags["fast_mode"] is False
        assert flags["semantic_parser"] is False
        assert flags["crossref_enrichment"] is False
        assert flags["ai_reasoning"] is False

    def test_flags_all_true(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            flags = orch._resolve_runtime_flags(
                {
                    "fast_mode": True,
                    "semantic_parser": True,
                    "crossref_enrichment": True,
                    "ai_reasoning": True,
                }
            )
        assert flags["fast_mode"] is True
        assert flags["semantic_parser"] is True
        assert flags["crossref_enrichment"] is True
        assert flags["ai_reasoning"] is True

    def test_flags_pytest_default(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "True"}, clear=False):
                flags = orch._resolve_runtime_flags({})
        assert flags["fast_mode"] is True

    def test_flags_empty_options(self, orch):
        with patch("app.pipeline.orchestrator.settings") as mock_s:
            mock_s.DEFAULT_FAST_MODE = False
            mock_s.LOW_MEMORY_MODE = False
            with patch.dict(os.environ, {}, clear=True):
                flags = orch._resolve_runtime_flags(None)
        assert flags["fast_mode"] is False


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1d: SHA256 edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestSHA256EdgeCases:
    def test_sha256_file_not_found(self, orch):
        with pytest.raises(FileNotFoundError):
            orch._compute_sha256("/nonexistent/path/file.txt")

    def test_sha256_empty_file(self, orch, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = orch._compute_sha256(str(f))
        assert result == hashlib.sha256(b"").hexdigest()

    def test_coerce_bool_none(self):
        assert PipelineOrchestrator._coerce_bool(None, False) is False
        assert PipelineOrchestrator._coerce_bool(None, True) is True

    def test_coerce_bool_int(self):
        assert PipelineOrchestrator._coerce_bool(1, False) is True
        assert PipelineOrchestrator._coerce_bool(0, True) is False
        assert PipelineOrchestrator._coerce_bool(42, False) is True

    def test_coerce_bool_float(self):
        assert PipelineOrchestrator._coerce_bool(0.0, True) is False
        assert PipelineOrchestrator._coerce_bool(0.1, False) is True

    def test_coerce_bool_unknown_string(self):
        assert PipelineOrchestrator._coerce_bool("random", True) is True
        assert PipelineOrchestrator._coerce_bool("random", False) is False


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1e: Persist partial result edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestPersistPartialEdgeCases:
    def test_persist_partial_null_sb_and_doc(self, orch):
        orch._persist_partial_result("job1", None, None)

    def test_persist_partial_null_doc(self, orch):
        orch._persist_partial_result("job1", None, MagicMock())

    def test_persist_partial_null_sb(self, orch):
        doc = PipelineDocument(document_id="doc1", blocks=[], metadata=DocumentMetadata())
        orch._persist_partial_result("job1", doc, None)

    def test_persist_partial_existing_record_error(self, orch):
        sb = _make_sb()
        doc = PipelineDocument(document_id="doc1", blocks=[], metadata=DocumentMetadata())
        with patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]
            mock_repo.upsert_sync.side_effect = Exception("update failed")
            with patch("app.pipeline.orchestrator.build_structured_data", return_value={"key": "val"}):
                orch._persist_partial_result("job1", doc, sb)

    def test_persist_partial_insert_on_missing(self, orch):
        sb = _make_sb()
        doc = PipelineDocument(document_id="doc1", blocks=[], metadata=DocumentMetadata())
        with patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo._table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            with patch("app.pipeline.orchestrator.build_structured_data", return_value={"key": "val"}):
                orch._persist_partial_result("job1", doc, sb)
            mock_repo.insert_sync.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1f: Pipeline error handler paths
# ══════════════════════════════════════════════════════════════════════════════


class TestPipelineErrorHandlers:
    def _run_shallow_pipeline(self, orch, tmp_path, config_fn):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
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
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=_make_sb()),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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
            config_fn(doc, mock_set)
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})

    def test_cancelled_in_extraction(self, orch, tmp_path):
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        with patch.object(orch, "_update_status"), patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.return_value.get_parser.side_effect = asyncio.CancelledError("cancel")
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "cancelled"

    def test_error_safe_execution_swallows(self, orch, tmp_path):
        """safe_execution swallows pipeline exceptions; returns 'processing'."""
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        with patch.object(orch, "_update_status"), patch("app.pipeline.orchestrator.ParserFactory") as mock_pf:
            mock_pf.side_effect = Exception("Factory failed before doc_obj")
            result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "processing"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1g: Atomic completion / Persistence logic
# ══════════════════════════════════════════════════════════════════════════════


class TestAtomicCompletion:
    def test_output_ready_with_generated_doc_fallback(self, orch, tmp_path):
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()
        doc.output_path = str(tmp_path / "nonexistent.docx")
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=doc.output_path),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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

    def test_output_not_ready_no_generated_doc(self, orch, tmp_path):
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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

    def test_hash_update_failure_at_completion(self, orch, tmp_path):
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.generated_doc = MagicMock()
        parser.parse.return_value = doc
        out_path = tmp_path / "out.docx"
        out_path.write_text("output")
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(out_path)),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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

            def _fake_update_hash(*args, **kwargs):
                raise Exception("hash fail")

            with patch(
                "app.services.document_service.DocumentService.update_output_hash", side_effect=_fake_update_hash
            ):
                result = orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1h: Edit flow error paths
# ══════════════════════════════════════════════════════════════════════════════


class TestEditFlowErrors:
    def test_edit_flow_no_generated_doc(self, orch):
        with (
            patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_doc_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_result_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentVersionRepository") as mock_ver_repo_cls,
        ):
            mock_doc_repo = MagicMock()
            mock_doc_repo_cls.return_value = mock_doc_repo
            mock_doc_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]
            )

            mock_result_repo = MagicMock()
            mock_result_repo_cls.return_value = mock_result_repo
            mock_result_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "structured_data": {"old": "data"}}]
            )

            mock_ver_repo = MagicMock()
            mock_ver_repo_cls.return_value = mock_ver_repo
            mock_ver_repo._table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"version_number": "v2"}]
            )

            with patch.object(orch, "_update_status"):
                with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
                    with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                        mock_val.return_value = MagicMock()
                        with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                            with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                                pipeline_doc = MagicMock()
                                pipeline_doc.generated_doc = None
                                mock_fmt.return_value.process.return_value = pipeline_doc
                                with patch("app.pipeline.orchestrator.AIExplainer"):
                                    with patch("app.pipeline.orchestrator.Exporter"):
                                        with patch("os.makedirs"):
                                            with patch("os.path.splitext", return_value=("test", ".docx")):
                                                with patch(
                                                    "os.path.abspath", return_value="/tmp/output/test_edited.docx"
                                                ):
                                                    result = orch.run_edit_flow(
                                                        "job1", {"sections": {"body": ["Edited"]}}, "ieee"
                                                    )
        assert result["status"] == "success"

    def test_edit_flow_version_numbering(self, orch):
        with (
            patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_doc_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_result_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentVersionRepository") as mock_ver_repo_cls,
        ):
            mock_doc_repo = MagicMock()
            mock_doc_repo_cls.return_value = mock_doc_repo
            mock_doc_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]
            )

            mock_result_repo = MagicMock()
            mock_result_repo_cls.return_value = mock_result_repo
            mock_result_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "structured_data": {"old": "data"}}]
            )

            mock_ver_repo = MagicMock()
            mock_ver_repo_cls.return_value = mock_ver_repo
            mock_ver_repo._table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"version_number": "v2"}]
            )

            with patch.object(orch, "_update_status"):
                with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
                    with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                        mock_val.return_value = MagicMock()
                        with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                            with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                                pipeline_doc = MagicMock()
                                pipeline_doc.generated_doc = MagicMock()
                                mock_fmt.return_value.process.return_value = pipeline_doc
                                with patch("app.pipeline.orchestrator.Exporter"):
                                    with patch("os.makedirs"):
                                        with patch("os.path.splitext", return_value=("test", ".docx")):
                                            with patch("os.path.abspath", return_value="/tmp/output/test_edited.docx"):
                                                with patch.object(orch, "_compute_sha256", return_value="hash"):
                                                    with patch("app.pipeline.orchestrator.AIExplainer"):
                                                        result = orch.run_edit_flow(
                                                            "job1", {"sections": {"body": ["Text"]}}, "ieee"
                                                        )
        assert result["status"] == "success"

    def test_edit_flow_invalid_version_string(self, orch):
        with (
            patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_doc_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_result_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentVersionRepository") as mock_ver_repo_cls,
        ):
            mock_doc_repo = MagicMock()
            mock_doc_repo_cls.return_value = mock_doc_repo
            mock_doc_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]
            )

            mock_result_repo = MagicMock()
            mock_result_repo_cls.return_value = mock_result_repo
            mock_result_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "structured_data": {"old": "data"}}]
            )

            mock_ver_repo = MagicMock()
            mock_ver_repo_cls.return_value = mock_ver_repo
            mock_ver_repo._table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"version_number": "abc"}]
            )

            with patch.object(orch, "_update_status"):
                with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
                    with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                        mock_val.return_value = MagicMock()
                        with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                            with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                                pipeline_doc = MagicMock()
                                pipeline_doc.generated_doc = MagicMock()
                                mock_fmt.return_value.process.return_value = pipeline_doc
                                with patch("app.pipeline.orchestrator.Exporter"):
                                    with patch("os.makedirs"):
                                        with patch("os.path.splitext", return_value=("test", ".docx")):
                                            with patch("os.path.abspath", return_value="/tmp/output/test_edited.docx"):
                                                with patch.object(orch, "_compute_sha256", return_value="hash"):
                                                    with patch("app.pipeline.orchestrator.AIExplainer"):
                                                        result = orch.run_edit_flow(
                                                            "job1", {"sections": {"body": ["Text"]}}, "ieee"
                                                        )
        assert result["status"] == "success"

    def test_edit_flow_no_versions(self, orch):
        with (
            patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_doc_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentResultRepository") as mock_result_repo_cls,
            patch("app.pipeline.orchestrator.orchestrator.DocumentVersionRepository") as mock_ver_repo_cls,
        ):
            mock_doc_repo = MagicMock()
            mock_doc_repo_cls.return_value = mock_doc_repo
            mock_doc_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"filename": "test.docx", "output_path": "/orig/output.docx"}]
            )

            mock_result_repo = MagicMock()
            mock_result_repo_cls.return_value = mock_result_repo
            mock_result_repo._table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 1, "structured_data": {"old": "data"}}]
            )

            mock_ver_repo = MagicMock()
            mock_ver_repo_cls.return_value = mock_ver_repo
            mock_ver_repo._table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )

            with patch.object(orch, "_update_status"):
                with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
                    with patch("app.pipeline.orchestrator.validate_document") as mock_val:
                        mock_val.return_value = MagicMock()
                        with patch("app.pipeline.orchestrator.safe_model_dump", return_value={"valid": True}):
                            with patch("app.pipeline.orchestrator.Formatter") as mock_fmt:
                                pipeline_doc = MagicMock()
                                pipeline_doc.generated_doc = MagicMock()
                                mock_fmt.return_value.process.return_value = pipeline_doc
                                with patch("app.pipeline.orchestrator.Exporter"):
                                    with patch("os.makedirs"):
                                        with patch("os.path.splitext", return_value=("test", ".docx")):
                                            with patch("os.path.abspath", return_value="/tmp/output/test_edited.docx"):
                                                with patch.object(orch, "_compute_sha256", return_value="hash"):
                                                    with patch("app.pipeline.orchestrator.AIExplainer"):
                                                        result = orch.run_edit_flow(
                                                            "job1", {"sections": {"body": ["Text"]}}, "ieee"
                                                        )
        assert result["status"] == "success"

    def test_edit_flow_cancelled_during_update(self, orch):
        with patch("app.pipeline.orchestrator.orchestrator.DocumentRepository") as mock_doc_repo_cls:
            mock_doc_repo = MagicMock()
            mock_doc_repo_cls.return_value = mock_doc_repo
            import asyncio

            mock_doc_repo._table.return_value.select.return_value.eq.return_value.execute.side_effect = (
                asyncio.CancelledError("cancel")
            )
            with patch.object(orch, "_update_status"):
                with patch("app.pipeline.orchestrator.get_supabase_client", return_value=MagicMock()):
                    result = orch.run_edit_flow("job1", {"sections": {"body": ["Text"]}}, "ieee")
        assert result["status"] == "cancelled"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1i: Keyword extraction
# ══════════════════════════════════════════════════════════════════════════════


class TestKeywordExtraction:
    def _run_pipeline_with_doc(self, orch, tmp_path, doc, **overrides):
        sb = _make_sb()
        doc.generated_doc = MagicMock()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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
            for k, v in overrides.items():
                setattr(mock_set, k, v)
            return orch._run_pipeline_internal(str(input_path), "job1", "ieee", {})

    def test_keywords_from_metadata_abstract(self, orch, tmp_path):
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        doc.metadata.abstract = "This research explores machine learning and AI."
        self._run_pipeline_with_doc(orch, tmp_path, doc)
        assert len(doc.metadata.keywords) > 0

    def test_keywords_from_abstract_block(self, orch, tmp_path):
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(
                    block_id="b1",
                    index=1,
                    block_type=BlockType.ABSTRACT,
                    text="This paper studies neural network architectures for NLP.",
                ),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        doc.metadata.abstract = ""
        self._run_pipeline_with_doc(orch, tmp_path, doc)
        assert len(doc.metadata.keywords) > 0
        assert doc.metadata.ai_hints.get("keywords") is not None

    def test_keywords_extraction_failure_does_not_crash(self, orch, tmp_path):
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        with patch("app.pipeline.orchestrator.extract_keywords", side_effect=Exception("kw fail")):
            result = self._run_pipeline_with_doc(orch, tmp_path, doc)
        assert result["status"] == "success"

    def test_keywords_no_abstract_or_block(self, orch, tmp_path):
        doc = PipelineDocument(
            document_id="job1",
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="body"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.abstract = ""
        doc.metadata.ai_hints = {}
        result = self._run_pipeline_with_doc(orch, tmp_path, doc)
        assert result["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4.1j: GROBID/Docling parallel extraction + AI reasoning
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegrationScenarios:
    """Tests for GROBID/Docling parallel pass, Agent V2 cache, AI reasoning etc."""

    def _mk_doc(self, job_id="job1"):
        doc = PipelineDocument(
            document_id=job_id,
            blocks=[
                Block(block_id="b1", index=1, block_type=BlockType.BODY, text="t"),
            ],
            metadata=DocumentMetadata(),
        )
        doc.metadata.ai_hints = {}
        return doc

    def _run_pipeline(self, orch, tmp_path, doc, settings_overrides=None, **options):
        sb = _make_sb()
        input_path = tmp_path / "test.pdf"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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

    def test_grobid_success(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(
                orch.grobid_client,
                "process_header_document",
                return_value={"title": "Test", "authors": [{"name": "A"}]},
            ):
                with patch.object(orch.docling_client, "is_available", return_value=True):
                    with patch.object(
                        orch.docling_client, "analyze_layout", return_value={"elements": [{"type": "text"}]}
                    ):
                        with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=False):
                            self._run_pipeline(
                                orch, tmp_path, doc, {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True}
                            )
        assert doc.metadata.ai_hints.get("grobid_metadata", {}).get("title") == "Test"
        assert doc.metadata.ai_hints.get("docling_layout", {}).get("elements") is not None

    def test_grobid_disabled(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                self._run_pipeline(orch, tmp_path, doc, {"GROBID_ENABLED": False, "USE_DOCLING_FALLBACK": True})
        assert "grobid_metadata" not in doc.metadata.ai_hints

    def test_docling_disabled(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(orch.grobid_client, "process_header_document", return_value={"title": "Test"}):
                with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=False):
                    self._run_pipeline(orch, tmp_path, doc, {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": False})
        assert "docling_layout" not in doc.metadata.ai_hints

    def test_grobid_timeout(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()

        def _slow(*a, **kw):
            time.sleep(10)
            return {"title": "Test"}

        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(orch.grobid_client, "process_header_document", side_effect=_slow):
                with patch.object(orch, "_should_skip_docling_for_digital_pdf", return_value=True):
                    self._run_pipeline(
                        orch,
                        tmp_path,
                        doc,
                        {
                            "GROBID_ENABLED": True,
                            "USE_DOCLING_FALLBACK": True,
                            "PIPELINE_GROBID_TIMEOUT_SECONDS": 1,
                        },
                    )
        assert "grobid_metadata" not in doc.metadata.ai_hints

    def test_agent_v2_cache_skip(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        doc.metadata.ai_hints["grobid_metadata"] = {"title": "Existing"}
        doc.metadata.ai_hints["docling_layout"] = {"elements": []}
        with patch.object(orch.grobid_client, "is_available", return_value=True):
            with patch.object(
                orch.grobid_client, "process_header_document", return_value={"title": "SHOULD NOT BE CALLED"}
            ):
                self._run_pipeline(orch, tmp_path, doc, {"GROBID_ENABLED": True, "USE_DOCLING_FALLBACK": True})
        assert doc.metadata.ai_hints["grobid_metadata"]["title"] == "Existing"

    def test_pymupdf_fallback_in_pipeline(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.metadata.title = ""
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
                    self._run_pipeline(orch, tmp_path, doc, {"PYMUPDF_FALLBACK": True})
        assert doc.metadata.ai_hints.get("pymupdf_fallback", {}).get("source") == "pymupdf"
        assert doc.metadata.title == "PyMuPDF Title"

    def test_non_pdf_skips_parallel_extraction(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        sb = _make_sb()
        input_path = tmp_path / "test.docx"
        input_path.write_text("dummy")
        parser = MagicMock()
        parser.parse.return_value = doc
        orch.converter.convert_to_docx.return_value = str(tmp_path / "converted.docx")
        with (
            patch("app.pipeline.orchestrator.ParserFactory") as mock_pf,
            patch("app.pipeline.orchestrator.get_supabase_client", return_value=sb),
            patch("app.db.repositories.base.get_supabase_client", return_value=sb),
            patch.object(orch, "_run_structure_detection", return_value=doc),
            patch.object(orch, "_run_classification", return_value=doc),
            patch.object(orch, "_run_validation_stage", return_value=doc),
            patch.object(orch, "_run_formatting_stage", return_value=doc),
            patch.object(orch, "_export_document", return_value=str(tmp_path / "out.docx")),
            patch.object(orch, "_update_status"),
            patch("app.pipeline.orchestrator.execute_with_retry", side_effect=lambda fn, doc: doc),
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
        orch.converter.convert_to_docx.assert_called_once()

    def test_ai_reasoning_enabled(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = ["Some guideline"]
        reasoner_inst = MagicMock()
        reasoner_inst.generate_instruction_set.return_value = {
            "instructions": [
                {"text": "Do X", "confidence": 0.85},
                {"text": "Check Y", "confidence": 0.50},
            ]
        }
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline(orch, tmp_path, doc, {}, fast_mode=False, ai_reasoning=True)
        assert result["status"] == "success"
        assert doc.metadata.ai_hints.get("semantic_advice", {}).get("instructions") is not None

    def test_ai_reasoning_engines_unavailable(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=None):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=None):
                result = self._run_pipeline(orch, tmp_path, doc, {}, fast_mode=False, ai_reasoning=True)
        assert result["status"] == "success"

    def test_ai_reasoning_timeout(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock()
        rag_inst.query_guidelines.return_value = ["Guide"]
        reasoner_inst = MagicMock()
        reasoner_inst.generate_instruction_set.side_effect = TimeoutError("reasoning timed out")
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline(orch, tmp_path, doc, {}, fast_mode=False, ai_reasoning=True)
        assert result["status"] == "success"

    def test_ai_reasoning_generic_exception(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        rag_inst = MagicMock()
        rag_inst.query_guidelines.side_effect = Exception("RAG crash")
        reasoner_inst = MagicMock()
        with patch("app.pipeline.orchestrator.get_rag_engine", return_value=rag_inst):
            with patch("app.pipeline.orchestrator.get_reasoning_engine", return_value=reasoner_inst):
                result = self._run_pipeline(orch, tmp_path, doc, {}, fast_mode=False, ai_reasoning=True)
        assert result["status"] == "success"

    def test_crossref_enrichment(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        doc.references = [Reference(raw_text="Some citation", citation_key="cit1", reference_id="r1", index=1)]
        with patch("app.services.crossref_client.get_crossref_client") as mock_cr:
            mock_cr_inst = MagicMock()
            mock_cr_inst.validate_citation.return_value = {"valid": True, "doi": "10.1234/test"}
            mock_cr.return_value = mock_cr_inst
            self._run_pipeline(
                orch, tmp_path, doc, {"CROSSREF_MAX_WORKERS": 2}, fast_mode=False, crossref_enrichment=True
            )
        assert doc.references[0].metadata["crossref_validation"]["valid"] is True

    def test_crossref_exception_handled(self, orch, tmp_path):
        doc = self._mk_doc()
        doc.generated_doc = MagicMock()
        doc.references = [Reference(raw_text="Test", citation_key="cit2", reference_id="r1", index=1)]
        with patch("app.services.crossref_client.get_crossref_client", side_effect=Exception("CrossRef unavailable")):
            result = self._run_pipeline(orch, tmp_path, doc, {}, fast_mode=False, crossref_enrichment=True)
        assert result["status"] == "success"
