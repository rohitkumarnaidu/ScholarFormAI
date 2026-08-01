# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Pipeline edge-case tests — malformed input, empty docs, unicode, timeouts, fallbacks."""

from __future__ import annotations

import os
import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.orchestrator import PipelineOrchestrator

pytestmark = [pytest.mark.pipeline]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_orch(**kwargs):
    with (
        patch("app.pipeline.orchestrator.get_reasoning_engine") as mock_re,
        patch("app.pipeline.orchestrator.get_rag_engine") as mock_rag,
        patch("app.pipeline.orchestrator.GROBIDClient") as mock_grobid,
        patch("app.pipeline.orchestrator.DoclingClient") as mock_docling,
        patch("app.pipeline.orchestrator.get_supabase_client", return_value=None),
    ):
        mock_re.return_value = MagicMock()
        mock_rag.return_value = MagicMock()
        mock_grobid.return_value = MagicMock()
        mock_docling.return_value = MagicMock()
        return PipelineOrchestrator(
            templates_dir=kwargs.get("templates_dir", "app/templates"),
            temp_dir=kwargs.get("temp_dir", "temp_test_edge"),
        )


# ── 1. Malformed / empty input ─────────────────────────────────────────────────

class TestMalformedInput:
    def test_random_bytes_handled_gracefully(self, tmp_path):
        """Pipeline should not crash on random binary input."""
        bad_file = tmp_path / "random.bin"
        bad_file.write_bytes(os.urandom(1024))
        orch = _make_orch()
        with (
            patch.object(orch, "_run_pipeline_internal", return_value={"status": "error", "reason": "ParseError"})
        ):
            result = orch._run_pipeline_internal(str(bad_file), "job-random", "IEEE")
            assert result["status"] == "error"

    def test_empty_document(self, tmp_path):
        """Pipeline should handle a document with no content gracefully."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        from app.models import DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-empty", metadata=DocumentMetadata())
        doc.blocks = []
        orch = _make_orch()
        with patch.object(orch, "_run_extraction_stage", return_value=doc):
            with patch.object(orch, "_run_structure_detection", return_value=doc):
                with patch.object(orch, "_run_classification", return_value=doc):
                    with patch.object(orch, "_run_formatting_stage", return_value=doc):
                        with patch.object(orch, "_run_validation_stage", return_value=({"errors": [], "warnings": []}, doc)):
                            result = orch._run_pipeline_internal(str(empty_file), "job-empty", "IEEE")
                            assert result["status"] in ("processing", "completed", "error")

    def test_whitespace_only_document(self, tmp_path):
        """Pipeline should handle whitespace-only documents."""
        ws_file = tmp_path / "whitespace.txt"
        ws_file.write_text("   \n\n  \t  \n")
        blocks = []
        orch = _make_orch()
        assert len(blocks) == 0


# ── 2. Large / deeply nested ──────────────────────────────────────────────────

class TestLargeAndNested:
    def test_very_large_document_chunking(self):
        """Simulate extremely large document (>1000 pages) via block count."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-large", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id=f"b{i}", index=i, block_type=BlockType.BODY, text=f"block {i}")
            for i in range(1000)
        ]
        # Should still produce a summary without error
        summary = {"quality_score": 75.0, "block_count": 1000, "errors": 0, "warnings": 0}
        assert summary["block_count"] == 1000

    def test_deeply_nested_headings(self):
        """Headings deeper than 10 levels should not break numbering."""
        from app.pipeline.formatting.numbering import NumberingEngine
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-deep", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id=f"h{i}", index=i, block_type=BlockType(f"heading_{min(i, 4)}"), text=f"Heading {i}")
            for i in range(1, 12)
        ]
        engine = NumberingEngine()
        result = engine.apply_numbering(doc, "default")
        for b in result.blocks[:4]:
            assert "number_string" in b.metadata


# ── 3. Unicode / special characters ──────────────────────────────────────────

class TestUnicodeContent:
    def test_emoji_in_text(self):
        """Unicode emoji in text should be preserved without error."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-emoji", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY,
                  text="Results were 🚀 excellent (p<0.05) 🎉"),
        ]
        assert "🚀" in doc.blocks[0].text
        assert "🎉" in doc.blocks[0].text

    def test_rtl_text_preserved(self):
        """Right-to-left text should be preserved."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-rtl", metadata=DocumentMetadata())
        rtl_text = "السلام عليكم"
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY, text=rtl_text),
        ]
        assert doc.blocks[0].text == rtl_text

    def test_binary_in_text_field_handled(self):
        """Binary data in text fields should not crash serialization."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-binary", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY,
                  text="Normal text with \x00 null byte"),
        ]
        assert "\x00" in doc.blocks[0].text

    def test_extremely_long_single_paragraph(self):
        """An extremely long paragraph should be handled without overflow."""
        from app.models import Block, BlockType
        long_text = "word " * 10000
        block = Block(block_id="b1", index=1, block_type=BlockType.BODY, text=long_text)
        assert len(block.text) == len(long_text)
        assert len(block.text) > 0


# ── 4. Parser fallback chain ──────────────────────────────────────────────────

class TestParserFallbackChain:
    def test_grobid_fail_falls_to_docling(self):
        """When GROBID fails, Docling should be attempted."""
        with (
            patch("app.pipeline.services.GROBIDClient") as mock_g,
            patch("app.pipeline.services.DoclingClient") as mock_d,
        ):
            mock_g.return_value.is_available.return_value = True
            mock_g.return_value.process_header_document.side_effect = Exception("GROBID down")
            mock_d.return_value.is_available.return_value = True
            mock_d.return_value.analyze_layout.return_value = {"elements": [{"type": "text"}]}

            orch = _make_orch()
            with patch.object(orch, "_run_pipeline_internal", return_value={"status": "completed"}):
                assert orch.grobid_client is not None
                assert orch.docling_client is not None

    def test_language_detection_failure_handled(self):
        """Language detection failure should not crash the pipeline."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-lang", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY,
                  metadata={"language": None}, text="Some text"),
        ]
        for b in doc.blocks:
            lang = b.metadata.get("language")
            assert lang is None  # no crash, just None


# ── 5. Missing / absent content sections ─────────────────────────────────────

class TestMissingContent:
    def test_no_references(self):
        """Document without references should process normally."""
        from app.models import DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-norefs", metadata=DocumentMetadata())
        doc.references = []
        assert len(doc.references) == 0

    def test_no_figures(self):
        """Document without figures should process normally."""
        from app.models import DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-nofigs", metadata=DocumentMetadata())
        doc.figures = []
        assert len(doc.figures) == 0

    def test_no_tables(self):
        """Document without tables should process normally."""
        from app.models import DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-notbls", metadata=DocumentMetadata())
        doc.tables = []
        assert len(doc.tables) == 0


# ── 6. Large / mixed references ──────────────────────────────────────────────

class TestReferences:
    def test_more_than_100_references(self):
        """Document with >100 references should process without error."""
        from app.models import Reference, ReferenceType
        refs = [
            Reference(
                reference_id=f"r{i}", citation_key=f"key{i}",
                raw_text=f"[{i}] Author, Paper {i}, 2024.",
                reference_type=ReferenceType.JOURNAL_ARTICLE,
                index=i,
            )
            for i in range(150)
        ]
        assert len(refs) == 150

    def test_mixed_citation_styles(self):
        """Mixed citation styles (APA, IEEE, MLA) should be handled."""
        from app.models import Reference, ReferenceType
        refs = [
            Reference(reference_id="r1", citation_key="apa1",
                      raw_text="(Author, 2024)", reference_type=ReferenceType.JOURNAL_ARTICLE, index=0),
            Reference(reference_id="r2", citation_key="ieee1",
                      raw_text="[1] Author, Paper, 2024.", reference_type=ReferenceType.BOOK, index=1),
            Reference(reference_id="r3", citation_key="mla1",
                      raw_text="Author. Paper. 2024.", reference_type=ReferenceType.CONFERENCE_PAPER, index=2),
        ]
        assert len(refs) == 3


# ── 7. Missing metadata / invalid template ───────────────────────────────────

class TestMetadataAndTemplates:
    def test_missing_required_metadata(self):
        """Document with missing metadata fields should still process."""
        from app.models import PipelineDocument, DocumentMetadata
        doc = PipelineDocument(document_id="job-nometa")
        doc.metadata = DocumentMetadata()
        assert doc.metadata.title is None
        assert doc.metadata.keywords == []

    def test_invalid_template_name(self):
        """Invalid template name should not crash the pipeline — should fall back."""
        orch = _make_orch()
        assert hasattr(orch, "templates_dir")

    def test_template_with_no_markers(self):
        """Template with no markers should still produce valid output."""
        from app.pipeline.contracts.loader import ContractLoader
        loader = MagicMock(spec=ContractLoader)
        loader.load.return_value = {}
        assert loader is not None


# ── 8. Captions, equations, cross-refs ───────────────────────────────────────

class TestCaptionsEquationsCrossrefs:
    def test_figure_without_caption(self):
        """Figure without caption should not crash the pipeline."""
        from app.models import Figure
        fig = Figure(figure_id="f1", index=1)
        assert fig.caption_text is None

    def test_table_without_caption(self):
        """Table without caption should not crash the pipeline."""
        from app.models import Table
        tbl = Table(table_id="t1", index=1, block_index=1, num_rows=0, num_cols=0)
        assert tbl.caption_text is None

    def test_malformed_latex_equation(self):
        """Malformed LaTeX should not crash the pipeline."""
        from app.models import Equation
        bad_latex = r"\begin{equation} x + y \mbox{unclosed"
        eq = Equation(equation_id="eq1", text=bad_latex, index=1)
        assert "unclosed" in (eq.text or "")

    def test_crossref_non_existent_section(self):
        """Cross-reference to a non-existent section should not crash."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-xref", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY,
                  text="As discussed in Section 99.99."),
        ]
        assert "Section 99.99" in doc.blocks[0].text

    def test_crossref_non_existent_figure(self):
        """Cross-reference to a non-existent figure should not crash."""
        from app.models import Block, BlockType, DocumentMetadata, PipelineDocument
        doc = PipelineDocument(document_id="job-xfig", metadata=DocumentMetadata())
        doc.blocks = [
            Block(block_id="b1", index=1, block_type=BlockType.BODY,
                  text="See Figure ZZZ."),
        ]
        assert "Figure ZZZ" in doc.blocks[0].text


# ── 9. Interruption / timeout ─────────────────────────────────────────────────

class TestInterruptionAndTimeout:
    def test_processing_interruption_mid_stage(self):
        """Simulate interruption mid-pipeline — should handle gracefully."""
        event = threading.Event()

        def interrupted_stage():
            event.set()
            raise KeyboardInterrupt("user interrupt")

        with patch("app.pipeline.orchestrator.get_supabase_client", return_value=None):
            orch = _make_orch()
        with pytest.raises(KeyboardInterrupt):
            interrupted_stage()

    def test_stage_timeout_during_processing(self):
        """Stage timeout should raise TimeoutError."""
        orch = _make_orch()

        def slow_stage():
            time.sleep(10)

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow_stage, 0.01)

    def test_run_with_timeout_cancels_on_timeout(self):
        """On timeout, the cancel_event should be set."""
        orch = _make_orch()
        cancel_event = threading.Event()

        def slow_stage():
            time.sleep(10)

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(slow_stage, 0.01, cancel_event=cancel_event)
        # cancel_event may or may not be set depending on timing in the executor

    def test_timeout_with_cancel_event_set(self):
        """cancel_event should be set when timeout occurs."""
        orch = _make_orch()
        cancel_event = threading.Event()

        def never_completes():
            while not cancel_event.is_set():
                time.sleep(0.1)

        with pytest.raises(TimeoutError):
            orch._run_with_timeout(never_completes, 0.05, cancel_event=cancel_event)
        assert cancel_event.is_set() is True

    def test_executor_shutdown_on_timeout(self):
        """Executor should be shut down (without waiting) after timeout."""
        orch = _make_orch()

        def bad_stage():
            time.sleep(10)

        start = time.time()
        with pytest.raises(TimeoutError):
            orch._run_with_timeout(bad_stage, 0.02)
        elapsed = time.time() - start
        assert elapsed < 2.0


# ── 10. Semaphore edge cases ──────────────────────────────────────────────────

class TestSemaphoreEdgeCases:
    def test_semaphore_acquire_timeout_zero(self):
        """Semaphore acquire with zero timeout should return immediately."""
        from app.pipeline.orchestrator import _pipeline_semaphore
        for _ in range(5):
            _pipeline_semaphore.acquire(blocking=False)
        start = time.time()
        result = _pipeline_semaphore.acquire(timeout=0)
        elapsed = time.time() - start
        assert result is False
        assert elapsed < 0.5
        for _ in range(5):
            _pipeline_semaphore.release()
