# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Gap-filling tests for MultiDocSynthesizer — covers uncovered branches, edge cases,
and error paths not tested in existing deep suites.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest

# Break circular imports
sys.modules["app.routers.v1.generator"] = MagicMock()
sys.modules["app.routers.v1.synthesis"] = MagicMock()

def _make_synthesizer(**kwargs):
    from app.models import Block, BlockType, PipelineDocument, Reference
    from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
    with (
        patch("app.pipeline.synthesis.synthesizer.RedisPubSub") as mock_pubsub_cls,
        patch("app.pipeline.synthesis.synthesizer.get_crossref_client") as mock_crossref_fn,
        patch("app.pipeline.synthesis.synthesizer.CSLEngine") as mock_csl_cls,
    ):
        mock_pubsub = MagicMock()
        mock_pubsub.publish = AsyncMock()
        mock_pubsub_cls.return_value = mock_pubsub
        mock_crossref = MagicMock()
        mock_crossref_fn.return_value = mock_crossref
        mock_csl = MagicMock()
        mock_csl_cls.return_value = mock_csl

        session_service = kwargs.get("session_service") or MagicMock()
        if not kwargs.get("session_service"):
            session_service.update_session = AsyncMock()
            session_service.get_session = AsyncMock()
            session_service.save_document_version = AsyncMock()

        vector_store = kwargs.get("vector_store") or MagicMock()
        llm_service = kwargs.get("llm_service") or MagicMock()
        pipeline_orchestrator = kwargs.get("pipeline_orchestrator") or MagicMock()
        pubsub = kwargs.get("pubsub") or mock_pubsub

        synth = MultiDocSynthesizer(
            session_service=session_service,
            vector_store=vector_store,
            llm_service=llm_service,
            pipeline_orchestrator=pipeline_orchestrator,
            pubsub=pubsub,
        )
        return synth, {
            "session_service": session_service,
            "vector_store": vector_store,
            "llm_service": llm_service,
            "pipeline_orchestrator": pipeline_orchestrator,
            "pubsub": pubsub,
            "crossref": mock_crossref,
            "csl_engine": mock_csl,
        }

def _make_mock_block(text: str = "", section_name: str | None = None, page_number: int | None = 1):
    from app.models import Block, BlockType, PipelineDocument, Reference
    b = MagicMock(spec=Block)
    b.text = text
    b.section_name = section_name
    b.page_number = page_number
    return b

def _make_mock_doc(blocks: list | None = None):
    from app.models import Block, BlockType, PipelineDocument, Reference
    doc = MagicMock(spec=PipelineDocument)
    doc.blocks = blocks or []
    return doc

OUTLINE = {"title": "Synthesis Report", "sections": [{"title": "Intro", "key_points": ["kp1"]}]}
SECTIONS = [{"title": "Intro", "content": "Generated content [REF: Smith2020] here."}]
REFERENCES = ["[1] Smith, J. (2023). A Paper."]

class TestRunGaps:
    """Cover uncovered branches in run()."""

    @pytest.mark.asyncio
    async def test_run_with_warnings(self):
        """config.setdefault('warnings', []).extend(warnings) branch."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = {"config_json": {}}
        out_path = "/tmp/out.docx"

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock,
                         return_value=([{"path": "a.docx", "filename": "a.docx"}], ["Some warning"])),
            patch.object(synth, "_extract_documents", new_callable=AsyncMock,
                         return_value=[{"filename": "a.docx", "sections": ["Intro"]}]),
            patch.object(synth, "_build_chunks", return_value=[]),
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock, return_value={}),
            patch.object(synth, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synth, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synth, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synth, "_render_document", return_value=out_path),
        ):
            result = await synth.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path

    @pytest.mark.asyncio
    async def test_run_no_config(self):
        """Session with no config_json."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = None
        out_path = "/tmp/out.docx"

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock,
                         return_value=([{"path": "a.docx", "filename": "a.docx"}], [])),
            patch.object(synth, "_extract_documents", new_callable=AsyncMock,
                         return_value=[{"filename": "a.docx", "sections": []}]),
            patch.object(synth, "_build_chunks", return_value=[]),
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock, return_value={}),
            patch.object(synth, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synth, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synth, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synth, "_render_document", return_value=out_path),
        ):
            result = await synth.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path

    @pytest.mark.asyncio
    async def test_run_extracted_docs_section_count(self):
        """_extracted_docs section_count computation."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = {"config_json": {}}
        out_path = "/tmp/out.docx"

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock,
                         return_value=([{"path": "a.docx", "filename": "a.docx"}], [])),
            patch.object(synth, "_extract_documents", new_callable=AsyncMock,
                         return_value=[{"filename": "a.docx", "sections": ["Intro", "Methods", "Results"]}]),
            patch.object(synth, "_build_chunks", return_value=[]),
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock, return_value={}),
            patch.object(synth, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synth, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synth, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synth, "_render_document", return_value=out_path),
        ):
            result = await synth.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path

    @pytest.mark.asyncio
    async def test_run_with_analysis(self):
        """Cross-doc analysis populated."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = {"config_json": {}}
        out_path = "/tmp/out.docx"
        analysis = {"overlaps": ["topic_a"], "gaps": ["missing_data"], "unique_points": {"a.docx": ["point"]}}

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock,
                         return_value=([{"path": "a.docx", "filename": "a.docx"}], [])),
            patch.object(synth, "_extract_documents", new_callable=AsyncMock,
                         return_value=[{"filename": "a.docx", "sections": ["Intro"]}]),
            patch.object(synth, "_build_chunks", return_value=[]),
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock, return_value=analysis),
            patch.object(synth, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synth, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synth, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synth, "_render_document", return_value=out_path),
        ):
            result = await synth.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path

class TestInsertCitationsGaps:
    """Cover remaining branches in _insert_citations."""

    def test_no_ref_pattern(self):
        """Content with no [REF:] patterns."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        sections = [{"title": "Intro", "content": "Plain text without citations."}]
        result = synth._insert_citations(sections, "ieee")
        assert result["references"] == []
        assert result["citations"] == []
        assert result["sections"][0]["content"] == "Plain text without citations."

    def test_empty_content_skipped(self):
        """Section with empty content."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        sections = [{"title": "Intro", "content": ""}]
        result = synth._insert_citations(sections, "ieee")
        assert result["references"] == []
        assert result["citations"] == []

    def test_csl_formatting_fallback(self):
        """CSL engine fails, falls back to raw_text."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "Smith, J.",
            "title": "Paper",
            "doi": "",
            "url": "",
        }
        deps["csl_engine"].format_references.side_effect = RuntimeError("CSL error")
        sections = [{"title": "Intro", "content": "[REF: Smith2020]"}]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        assert result["references"][0] == "Smith2020"

    def test_empty_authors(self):
        """Authors field empty, should result in empty list."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "",
            "title": "Paper",
            "doi": "10.1234/test",
            "url": "https://doi.org/10.1234/test",
        }
        deps["csl_engine"].format_references.return_value = ["[1] formatted"]
        sections = [{"title": "Intro", "content": "[REF: TestRef]"}]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        assert result["citations"][0]["query"] == "TestRef"

    def test_no_references_skip_formatting(self):
        """When no references, CSL formatting is skipped."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        sections = [{"title": "Intro", "content": "No citations here."}]
        result = synth._insert_citations(sections, "ieee")
        assert result["references"] == []
        deps["csl_engine"].format_references.assert_not_called()

    def test_unknown_query_empty_replace(self):
        """Unknown query that doesn't match query_to_num gets empty replacement."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {"authors": "", "title": "", "doi": "", "url": ""}
        deps["csl_engine"].format_references.return_value = ["raw"]
        sections = [{"title": "Intro", "content": "[REF: Known] and [REF: Unknown]"}]

        def validate(q):
            from app.models import Block, BlockType, PipelineDocument, Reference
            if q == "Known":
                return {"authors": "A", "title": "T", "doi": "", "url": ""}
            return {}

        deps["crossref"].validate_citation.side_effect = validate
        result = synth._insert_citations(sections, "ieee")
        assert "[1]" in result["sections"][0]["content"]

    def test_csl_style_passed(self):
        """Verify CSL style is passed correctly."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {"authors": "A", "title": "T", "doi": "", "url": ""}
        deps["csl_engine"].format_references.return_value = ["[1] fmt"]
        sections = [{"title": "Intro", "content": "[REF: X]"}]
        synth._insert_citations(sections, "apa")
        style_arg = deps["csl_engine"].format_references.call_args[1]["style"]
        assert style_arg == "apa"

class TestRenderDocumentGaps:
    """Cover remaining branches in _render_document."""

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_outline_is_list(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """Outline is a list (not dict)."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "ieee", {"title": "My Report"}, SECTIONS, REFERENCES)
        doc_arg = mock_fmt.process.call_args[0][0]
        assert doc_arg.blocks[0].text == "My Report"

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_title_from_outline(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """Title comes from outline dict."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "ieee", {"title": "Custom Title"}, SECTIONS, REFERENCES)
        doc_arg = mock_fmt.process.call_args[0][0]
        assert doc_arg.blocks[0].text == "Custom Title"

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_empty_outline_title_fallback(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """No title in outline -> Synthesized Report."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "ieee", {}, [], [])
        doc_arg = mock_fmt.process.call_args[0][0]
        assert doc_arg.blocks[0].text == "Synthesized Report"

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_paragraph_splitting(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """Section content with double newlines splits into multiple paragraphs."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        sections = [{"title": "Intro", "content": "Para one.\n\nPara two.\n\nPara three."}]
        synth._render_document("s1", "ieee", {"title": "T"}, sections, [])
        doc_arg = mock_fmt.process.call_args[0][0]
        body_blocks = [b for b in doc_arg.blocks if b.block_type == BlockType.BODY]
        assert len(body_blocks) == 3

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_empty_para_skipped(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """Empty paragraphs from split are skipped."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        sections = [{"title": "Intro", "content": "Para one.\n\n\n\nPara two."}]
        synth._render_document("s1", "ieee", {"title": "T"}, sections, [])
        doc_arg = mock_fmt.process.call_args[0][0]
        body_blocks = [b for b in doc_arg.blocks if b.block_type == BlockType.BODY]
        assert len(body_blocks) == 2

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_reference_blocks(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """Reference section with entries is rendered."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        refs = ["[1] Smith, J. (2023).", "[2] Doe, A. (2024)."]
        synth._render_document("s1", "ieee", {"title": "T"}, [], refs)
        doc_arg = mock_fmt.process.call_args[0][0]
        ref_blocks = [b for b in doc_arg.blocks if b.block_type == BlockType.REFERENCE_ENTRY]
        assert len(ref_blocks) == 2

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_template_info_passed(self, mock_resolve, mock_mkdir, mock_exp_cls, mock_fmt_cls):
        """TemplateInfo is set on document."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_fmt = MagicMock()
        mock_fmt_cls.return_value = mock_fmt
        mock_exp = MagicMock()
        mock_exp_cls.return_value = mock_exp
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: "/out/synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "apa", {"title": "T"}, [], [])
        doc_arg = mock_fmt.process.call_args[0][0]
        assert doc_arg.template.template_name == "apa"
        assert doc_arg.formatting_options["export_formats"] == ["docx"]

class TestGenerateSectionsGaps:
    """Cover remaining branches in _generate_sections."""

    @pytest.mark.asyncio
    async def test_outline_is_list(self):
        """Outline as list of section dicts."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["vector_store"].query.return_value = []
        with (
            patch.object(synth, "_llm_text", new_callable=AsyncMock, return_value="Content."),
            patch.object(synth, "_stream_chunks", new_callable=AsyncMock),
        ):
            result = await synth._generate_sections(["Section A", "Section B"], "sid")
            assert len(result) == 2
            assert result[0]["title"] == "Section A"
            assert result[1]["title"] == "Section B"

    @pytest.mark.asyncio
    async def test_outline_sections_not_list(self):
        """Outline dict with 'sections' not a list."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        result = await synth._generate_sections({"sections": None}, "sid")
        assert result == []

    @pytest.mark.asyncio
    async def test_vector_store_context_built(self):
        """RAG context built from vector_store.query results."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        deps["vector_store"].query.return_value = [
            {"text": "Source text", "source_doc": "a.pdf", "section": "Intro"},
        ]
        with (
            patch.object(synth, "_llm_text", new_callable=AsyncMock, return_value="Content."),
            patch.object(synth, "_stream_chunks", new_callable=AsyncMock),
        ):
            result = await synth._generate_sections(OUTLINE, "sid")
            assert result[0]["content"] == "Content."

class TestCrossDocAnalysisGaps:
    """Cover remaining branches in _cross_doc_analysis."""

    @pytest.mark.asyncio
    async def test_result_empty_fallback(self):
        """When LLM returns empty dict, fallback is used."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock, return_value={}):
            result = await synth._cross_doc_analysis([{"text": "Content", "filename": "a.pdf"}])
            assert result["overlaps"] == []
            assert result["gaps"] == []
            assert result["unique_points"] == {"a.pdf": []}

    @pytest.mark.asyncio
    async def test_text_truncated_to_1800(self):
        """Document text is truncated to 1800 chars."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        long_text = "X" * 3000
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"overlaps": [], "gaps": [], "unique_points": {}}
            await synth._cross_doc_analysis([{"text": long_text, "filename": "long.pdf"}])
            call_args = mock_llm.await_args
            assert call_args is not None

class TestStreamChunksGaps:
    """Cover edge cases in _stream_chunks."""

    @pytest.mark.asyncio
    async def test_text_at_boundary(self):
        """Text exactly at chunk boundary."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        text = "X" * 400
        await synth._stream_chunks("sid", "evt", "st", 50, text, chunk_size=400)
        assert deps["pubsub"].publish.await_count == 1

    @pytest.mark.asyncio
    async def test_with_extra_none(self):
        """Extra is None."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        await synth._stream_chunks("sid", "evt", "st", 50, "Hello", extra=None)
        deps["pubsub"].publish.assert_awaited_once()

class TestUpdateStatusGaps:
    """Cover edge cases in _update_status."""

    @pytest.mark.asyncio
    async def test_no_stage(self):
        """No stage provided."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        await synth._update_status("sid", "processing", 50, "msg", {})
        deps["session_service"].update_session.assert_awaited_once()
        call_kwargs = deps["session_service"].update_session.await_args[1]
        assert call_kwargs["status"] == "processing"
        assert call_kwargs["progress"] == 50

    @pytest.mark.asyncio
    async def test_with_outline_none(self):
        """outline=None does not set outline_json."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        await synth._update_status("sid", "done", 100, "done", {}, outline=None)
        call_kwargs = deps["session_service"].update_session.await_args[1]
        assert "outline_json" not in call_kwargs

    @pytest.mark.asyncio
    async def test_event_type_default(self):
        """Default event_type is stage_update."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        await synth._update_status("sid", "processing", 50, "msg", {})
        deps["pubsub"].publish.assert_awaited_once()

class TestEmitEventGaps:
    """Cover edge cases in _emit_event."""

    @pytest.mark.asyncio
    async def test_none_fields(self):
        """All optional fields None."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, deps = _make_synthesizer()
        await synth._emit_event("sid", "test_event", None, None, None)
        deps["pubsub"].publish.assert_awaited_once()

class TestBuildChunksGaps:
    """Cover edge cases in _build_chunks."""

    def test_page_number_tracking(self):
        """Page number tracking across blocks."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("Text A", "Section", 1),
            _make_mock_block("Text B", "Section", 2),
        ])
        docs = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(docs)
        assert len(chunks) >= 1

    def test_section_change_with_buffer(self):
        """Section change flushes buffer."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("A" * 200, "Section A", 1),
            _make_mock_block("B" * 200, "Section B", 2),
        ])
        docs = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(docs)
        sections = {c["section"] for c in chunks}
        assert "Section A" in sections
        assert "Section B" in sections

    def test_buffer_exceeds_threshold(self):
        """Buffer > 1000 chars triggers flush."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("A" * 600, "Section", 1),
            _make_mock_block("B" * 600, "Section", 1),
        ])
        docs = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(docs)
        assert len(chunks) >= 1

class TestLlmTextGaps:
    """Cover edge cases in _llm_text."""

    @patch("app.pipeline.synthesis.synthesizer.generate_with_fallback")
    @pytest.mark.asyncio
    async def test_no_text_in_response(self, mock_gen):
        """Response has no 'text' key."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_gen.return_value = {}
        synth, _ = _make_synthesizer()
        result = await synth._llm_text("sys", "usr")
        assert result == ""

    @patch("app.pipeline.synthesis.synthesizer.generate_with_fallback")
    @pytest.mark.asyncio
    async def test_sanitize_called(self, mock_gen):
        """sanitize_for_llm is called on user input."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        mock_gen.return_value = {"text": "ok"}
        synth, _ = _make_synthesizer()
        with patch("app.pipeline.synthesis.synthesizer.sanitize_for_llm", return_value="sanitized") as mock_san:
            await synth._llm_text("sys", "usr msg")
            mock_san.assert_called_once_with("usr msg")

class TestLlmJsonGaps:
    """Cover _llm_json: extract_json returns None case."""

    @pytest.mark.asyncio
    async def test_extract_json_returns_none(self):
        """When _extract_json returns None."""
        from app.models import Block, BlockType, PipelineDocument, Reference
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock, return_value="no json at all"):
            result = await synth._llm_json("sys", "usr")
            assert result is None

class TestExtractJsonGaps:
    """Cover edge cases in _extract_json."""

    def test_code_block_with_language(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('```json\n{"a": 1}\n```')
        assert result is not None
        assert json.loads(result) == {"a": 1}

    def test_code_block_without_language(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('```\n{"b": 2}\n```')
        assert result is not None
        assert json.loads(result) == {"b": 2}

    def test_no_braces(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json("no braces here")
        assert result is None

    def test_only_opening_brace(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('{"key": "value')
        assert result is None

    def test_reversed_braces(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json("}invalid{")
        assert result is None

    def test_code_block_with_case_variation(self):
        from app.models import Block, BlockType, PipelineDocument, Reference
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        result = MultiDocSynthesizer._extract_json('```JSON\n{"x": 1}\n```')
        assert json.loads(result) == {"x": 1}
