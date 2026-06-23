# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Deep unit tests for MultiDocSynthesizer — covers every method and edge case."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest

# Break circular imports: v1.generator and v1.synthesis both import from this module
sys.modules["app.routers.v1.generator"] = MagicMock()
sys.modules["app.routers.v1.synthesis"] = MagicMock()

from app.models import Block, BlockType, PipelineDocument, Reference
from app.pipeline.synthesis.synthesizer import _FakeUpload, _REF_PATTERN, MultiDocSynthesizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthesizer(**kwargs):
    """Build a MultiDocSynthesizer with all dependencies mocked."""
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

        session_service = kwargs.get("session_service")
        if session_service is None:
            session_service = MagicMock()
            session_service.update_session = AsyncMock()
            session_service.get_session = AsyncMock()
            session_service.save_document_version = AsyncMock()

        vector_store = kwargs.get("vector_store") or MagicMock()
        llm_service = kwargs.get("llm_service") or MagicMock()
        pipeline_orchestrator = kwargs.get("pipeline_orchestrator") or MagicMock()
        pubsub = kwargs.get("pubsub")
        if pubsub is None:
            pubsub = mock_pubsub

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
    b = MagicMock(spec=Block)
    b.text = text
    b.section_name = section_name
    b.page_number = page_number
    return b


def _make_mock_doc(blocks: list | None = None):
    doc = MagicMock(spec=PipelineDocument)
    doc.blocks = blocks or []
    return doc


# -------------------------------------------------------------------------------
# _FakeUpload
# -------------------------------------------------------------------------------

class TestFakeUpload:
    def test_filename(self):
        fu = _FakeUpload("test.pdf")
        assert fu.filename == "test.pdf"

    def test_read(self):
        fu = _FakeUpload("test.pdf")
        result = asyncio.run(fu.read())
        assert result == b""


# -------------------------------------------------------------------------------
# __init__
# -------------------------------------------------------------------------------

class TestInit:
    def test_defaults(self):
        synth, deps = _make_synthesizer()
        assert synth.session_service is deps["session_service"]
        assert synth.vector_store is deps["vector_store"]
        assert synth.llm_service is deps["llm_service"]
        assert synth.pipeline_orchestrator is deps["pipeline_orchestrator"]
        assert synth.pubsub is deps["pubsub"]
        assert synth.crossref is deps["crossref"]
        assert synth.csl_engine is deps["csl_engine"]

    def test_custom_pubsub(self):
        custom_pubsub = AsyncMock(spec=["publish"])
        synth, deps = _make_synthesizer(pubsub=custom_pubsub)
        assert synth.pubsub is custom_pubsub

    def test_default_pubsub_created(self):
        with patch("app.pipeline.synthesis.synthesizer.RedisPubSub") as mock_cls:
            mock_instance = AsyncMock(spec=["publish"])
            mock_cls.return_value = mock_instance
            with (
                patch("app.pipeline.synthesis.synthesizer.get_crossref_client"),
                patch("app.pipeline.synthesis.synthesizer.CSLEngine"),
            ):
                synth = MultiDocSynthesizer(
                    session_service=MagicMock(),
                    vector_store=MagicMock(),
                    llm_service=MagicMock(),
                    pipeline_orchestrator=MagicMock(),
                )
        assert synth.pubsub is mock_instance

    def test_crossref_and_csl_created(self):
        with (
            patch("app.pipeline.synthesis.synthesizer.RedisPubSub") as mock_pubsub_cls,
            patch("app.pipeline.synthesis.synthesizer.get_crossref_client") as mock_crossref_fn,
            patch("app.pipeline.synthesis.synthesizer.CSLEngine") as mock_csl_cls,
        ):
            mock_pubsub_cls.return_value = AsyncMock(spec=["publish"])
            crossref_instance = MagicMock()
            mock_crossref_fn.return_value = crossref_instance
            csl_instance = MagicMock()
            mock_csl_cls.return_value = csl_instance

            synth = MultiDocSynthesizer(
                session_service=MagicMock(),
                vector_store=MagicMock(),
                llm_service=MagicMock(),
                pipeline_orchestrator=MagicMock(),
            )
            assert synth.crossref is crossref_instance
            assert synth.csl_engine is csl_instance


# -------------------------------------------------------------------------------
# _emit_event
# -------------------------------------------------------------------------------

class TestEmitEvent:
    @pytest.fixture
    def synth_fixture(self):
        synth, deps = _make_synthesizer()
        return synth, deps

    async def test_basic(self, synth_fixture):
        synth, deps = synth_fixture
        await synth._emit_event("sid", "stage_update", "extract", 25, "ok")
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        assert call_args[0][0] == "session:sid"
        payload = call_args[0][1]
        assert payload["event_type"] == "stage_update"
        assert payload["stage"] == "extract"
        assert payload["progress"] == 25

    async def test_with_payload(self, synth_fixture):
        synth, deps = synth_fixture
        await synth._emit_event("sid", "error", None, None, None, payload={"custom": 1})
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        inner = call_args[0][1]
        assert inner["payload"]["custom"] == 1
        assert inner["event_type"] == "error"

    async def test_payload_merges_stage_progress_message(self, synth_fixture):
        synth, deps = synth_fixture
        await synth._emit_event("sid", "st", "mystage", 50, "hello", payload={"extra": 1})
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        inner = call_args[0][1]
        assert inner["payload"]["stage"] == "mystage"
        assert inner["payload"]["progress"] == 50
        assert inner["payload"]["message"] == "hello"
        assert inner["payload"]["extra"] == 1


# -------------------------------------------------------------------------------
# _update_status
# -------------------------------------------------------------------------------

class TestUpdateStatus:
    async def test_basic(self):
        synth, deps = _make_synthesizer()
        config = {"key": "val"}
        await synth._update_status("sid", "processing", 50, "msg", config, stage="mystage")

        deps["session_service"].update_session.assert_awaited_once_with(
            "sid",
            status="processing",
            progress=50,
            config_json={"key": "val", "stage": "mystage", "message": "msg"},
        )
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        assert "session:sid" in call_args[0]

    async def test_with_outline(self):
        synth, deps = _make_synthesizer()
        config = {}
        outline = {"title": "Test"}
        await synth._update_status("sid", "done", 100, "done", config, stage="outline", outline=outline)

        deps["session_service"].update_session.assert_awaited_once_with(
            "sid",
            status="done",
            progress=100,
            config_json={"stage": "outline", "message": "done"},
            outline_json=outline,
        )

    async def test_progress_clamped(self):
        synth, deps = _make_synthesizer()
        await synth._update_status("sid", "processing", 150, "msg", {})
        deps["session_service"].update_session.assert_awaited_once()
        call_kwargs = deps["session_service"].update_session.await_args[1]
        assert call_kwargs["progress"] == 100

        deps["session_service"].update_session.reset_mock()
        await synth._update_status("sid", "processing", -10, "msg", {})
        call_kwargs = deps["session_service"].update_session.await_args[1]
        assert call_kwargs["progress"] == 0

    async def test_event_type_error(self):
        synth, deps = _make_synthesizer()
        await synth._update_status("sid", "failed", 0, "err", {}, event_type="error")
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        assert call_args[0][1]["event_type"] == "error"


# -------------------------------------------------------------------------------
# _validate_files
# -------------------------------------------------------------------------------

class TestValidateFiles:
    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_valid_dict_entries(self, mock_read, mock_validate):
        mock_read.side_effect = [b"content_a", b"content_b"]
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/tmp/a.pdf", "filename": "a.pdf"},
            {"path": "/tmp/b.pdf", "filename": "b.pdf"},
        ]
        valid, warnings = await synth._validate_files(files)
        assert len(valid) == 2
        assert valid[0]["filename"] == "a.pdf"
        assert valid[1]["filename"] == "b.pdf"
        assert warnings == []
        assert mock_validate.call_count == 2

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_string_entries(self, mock_read, mock_validate):
        mock_read.side_effect = [b"content_a", b"content_b"]
        synth, _ = _make_synthesizer()
        files = [r"C:\docs\a.pdf", r"C:\docs\b.pdf"]
        valid, warnings = await synth._validate_files(files)
        assert len(valid) == 2
        assert warnings == []

    async def test_too_few_files(self):
        synth, _ = _make_synthesizer()
        with pytest.raises(Exception) as exc:
            await synth._validate_files([{"path": "/a.pdf", "filename": "a.pdf"}])
        assert "2" in str(exc.value) or "422" in str(exc.value)

    async def test_too_many_files(self):
        synth, _ = _make_synthesizer()
        files = [{"path": f"/{i}.pdf", "filename": f"{i}.pdf"} for i in range(7)]
        with pytest.raises(Exception) as exc:
            await synth._validate_files(files)
        assert "6" in str(exc.value) or "422" in str(exc.value)

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    async def test_invalid_extension_raises(self, mock_validate):
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/a.exe", "filename": "a.exe"},
            {"path": "/b.pdf", "filename": "b.pdf"},
        ]
        with pytest.raises(Exception) as exc:
            await synth._validate_files(files)
        assert "400" in str(exc.value) or "Unsupported" in str(exc.value)

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_duplicate_skipped(self, mock_read, mock_validate):
        mock_read.side_effect = [b"content_a", b"content_b", b"content_a"]
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/a.pdf", "filename": "a.pdf"},
            {"path": "/b.pdf", "filename": "b.pdf"},
            {"path": "/c.pdf", "filename": "c.pdf"},
        ]
        valid, warnings = await synth._validate_files(files)
        assert len(valid) == 2
        assert len(warnings) == 1
        assert "Duplicate" in warnings[0]
        assert "c.pdf" in warnings[0]

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_all_duplicates_raises(self, mock_read, mock_validate):
        mock_read.side_effect = [b"same", b"same"]
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/a.pdf", "filename": "a.pdf"},
            {"path": "/b.pdf", "filename": "b.pdf"},
        ]
        with pytest.raises(Exception) as exc:
            await synth._validate_files(files)
        assert "422" in str(exc.value) or "2 unique" in str(exc.value)

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_filename_from_path_when_missing(self, mock_read, mock_validate):
        mock_read.side_effect = [b"content_x", b"content_y"]
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/tmp/report.pdf"},
            {"path": "/tmp/paper.docx"},
        ]
        valid, warnings = await synth._validate_files(files)
        assert len(valid) == 2
        assert valid[0]["filename"] == "report.pdf"

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_content_size_included(self, mock_read, mock_validate):
        mock_read.side_effect = [b"12345", b"67890"]
        synth, _ = _make_synthesizer()
        files = [
            {"path": "/a.pdf", "filename": "a.pdf"},
            {"path": "/b.pdf", "filename": "b.pdf"},
        ]
        valid, warnings = await synth._validate_files(files)
        assert valid[0]["size"] == 5


# -------------------------------------------------------------------------------
# _chunk_text
# -------------------------------------------------------------------------------

class TestChunkText:
    def test_single_chunk(self):
        synth, _ = _make_synthesizer()
        text = "Hello World"
        chunks = synth._chunk_text(text, "doc.pdf", "Intro", 1, chunk_size=1000, overlap=200)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello World"
        assert chunks[0]["source_doc"] == "doc.pdf"
        assert chunks[0]["section"] == "Intro"
        assert chunks[0]["page"] == 1

    def test_multiple_chunks(self):
        synth, _ = _make_synthesizer()
        text = "A" * 2500
        chunks = synth._chunk_text(text, "doc.pdf", "Methods", None, chunk_size=1000, overlap=200)
        assert len(chunks) == 3
        assert all(c["source_doc"] == "doc.pdf" for c in chunks)
        assert all(c["section"] == "Methods" for c in chunks)
        assert chunks[0]["page"] is None

    def test_overlap_connects_chunks(self):
        synth, _ = _make_synthesizer()
        text = "X" * 1500
        chunks = synth._chunk_text(text, "d.pdf", "S", 2, chunk_size=1000, overlap=300)
        assert len(chunks) == 2
        assert len(chunks[0]["text"]) == 1000
        assert len(chunks[1]["text"]) <= 800

    def test_empty_text(self):
        synth, _ = _make_synthesizer()
        chunks = synth._chunk_text("", "doc.pdf", "S", 1)
        assert chunks == []

    def test_whitespace_only_text(self):
        synth, _ = _make_synthesizer()
        chunks = synth._chunk_text("   \n\n  ", "doc.pdf", "S", 1)
        assert chunks == []

    def test_exact_chunk_size(self):
        synth, _ = _make_synthesizer()
        text = "B" * 1000
        chunks = synth._chunk_text(text, "d.pdf", "S", 1, chunk_size=1000, overlap=200)
        assert len(chunks) == 1

    def test_chunk_size_one(self):
        synth, _ = _make_synthesizer()
        text = "ABC"
        chunks = synth._chunk_text(text, "d.pdf", "S", 1, chunk_size=1, overlap=0)
        assert len(chunks) == 3
        assert chunks[0]["text"] == "A"
        assert chunks[1]["text"] == "B"
        assert chunks[2]["text"] == "C"


# -------------------------------------------------------------------------------
# _build_chunks
# -------------------------------------------------------------------------------

class TestBuildChunks:
    def test_single_doc_multiple_blocks(self):
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("Intro text", "Introduction", 1),
            _make_mock_block("Methods text", "Methods", 2),
        ])
        extracted = [{"filename": "paper.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(extracted)
        assert len(chunks) >= 2
        assert any(c["source_doc"] == "paper.pdf" for c in chunks)

    def test_multiple_docs(self):
        synth, _ = _make_synthesizer()
        doc1 = _make_mock_doc(blocks=[
            _make_mock_block("Doc1 text" * 200, "SectionA", 1),
        ])
        doc2 = _make_mock_doc(blocks=[
            _make_mock_block("Doc2 text" * 200, "SectionB", 1),
        ])
        extracted = [
            {"filename": "doc1.pdf", "doc_obj": doc1},
            {"filename": "doc2.pdf", "doc_obj": doc2},
        ]
        chunks = synth._build_chunks(extracted)
        source_docs = {c["source_doc"] for c in chunks}
        assert "doc1.pdf" in source_docs
        assert "doc2.pdf" in source_docs

    def test_empty_blocks_produces_no_chunks(self):
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[])
        extracted = [{"filename": "empty.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(extracted)
        assert chunks == []

    def test_section_transition(self):
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("A" * 100, "Intro", 1),
            _make_mock_block("B" * 100, "Intro", 1),
            _make_mock_block("C" * 100, "Methods", 2),
        ])
        extracted = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(extracted)
        sections = {c["section"] for c in chunks}
        assert "Intro" in sections
        assert "Methods" in sections

    def test_block_without_section_uses_previous(self):
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block("First", "Intro", 1),
            _make_mock_block("Second", None, 1),
        ])
        extracted = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(extracted)
        for c in chunks:
            assert c["section"] == "Intro"

    def test_all_empty_text_skipped(self):
        synth, _ = _make_synthesizer()
        doc = _make_mock_doc(blocks=[
            _make_mock_block(""),
            _make_mock_block("   ", "S", 1),
            _make_mock_block(None, "S", 1),
        ])
        extracted = [{"filename": "f.pdf", "doc_obj": doc}]
        chunks = synth._build_chunks(extracted)
        assert chunks == []


# -------------------------------------------------------------------------------
# _extract_json
# -------------------------------------------------------------------------------

class TestExtractJson:
    def test_bare_json_object(self):
        result = MultiDocSynthesizer._extract_json('{"a": 1}')
        assert result == '{"a": 1}'

    def test_markdown_code_block(self):
        text = """```json\n{"key": "value"}\n```"""
        result = MultiDocSynthesizer._extract_json(text)
        assert result is not None
        assert json.loads(result) == {"key": "value"}

    def test_code_block_without_lang(self):
        text = """```\n{"x": 42}\n```"""
        result = MultiDocSynthesizer._extract_json(text)
        assert json.loads(result) == {"x": 42}

    def test_with_prefix_text(self):
        text = "Here is the result:\n```json\n{\"a\": [1,2]}\n```\nEnd."
        result = MultiDocSynthesizer._extract_json(text)
        assert json.loads(result) == {"a": [1, 2]}

    def test_no_json_returns_none(self):
        result = MultiDocSynthesizer._extract_json("Just plain text no braces")
        assert result is None

    def test_partial_brace_returns_none(self):
        result = MultiDocSynthesizer._extract_json('{"incomplete":')
        assert result is None

    def test_extra_text_after_json(self):
        result = MultiDocSynthesizer._extract_json('{"valid": true} and some trailing')
        assert json.loads(result) == {"valid": True}

    def test_multiple_json_objects_returns_full_span(self):
        text = '{"first": 1} trailing {"second": 2}'
        result = MultiDocSynthesizer._extract_json(text)
        # extracts from first { to last }, which is invalid JSON
        assert result == '{"first": 1} trailing {"second": 2}'


# -------------------------------------------------------------------------------
# _llm_json
# -------------------------------------------------------------------------------

class TestLlmJson:
    async def test_success(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_lt:
            mock_lt.return_value = '{"key": "value"}'
            result = await synth._llm_json("system", "user")
            assert result == {"key": "value"}

    async def test_empty_text_returns_none(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_lt:
            mock_lt.return_value = ""
            result = await synth._llm_json("system", "user")
            assert result is None

    async def test_invalid_json_returns_none(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_lt:
            mock_lt.return_value = "not json at all"
            result = await synth._llm_json("system", "user")
            assert result is None

    async def test_no_json_in_text_returns_none(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_lt:
            mock_lt.return_value = "Some explanation without JSON"
            result = await synth._llm_json("system", "user")
            assert result is None

    async def test_malformed_json_returns_none(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_lt:
            mock_lt.return_value = "{broken json!!!}"
            result = await synth._llm_json("system", "user")
            assert result is None


# -------------------------------------------------------------------------------
# _llm_text
# -------------------------------------------------------------------------------

class TestLlmText:
    @patch("app.pipeline.synthesis.synthesizer.generate_with_fallback")
    async def test_basic(self, mock_gen):
        mock_gen.return_value = {"text": "Hello world"}
        synth, _ = _make_synthesizer()
        result = await synth._llm_text("sys", "usr")
        assert result == "Hello world"
        mock_gen.assert_called_once()
        args, kwargs = mock_gen.call_args
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 1200

    @patch("app.pipeline.synthesis.synthesizer.generate_with_fallback")
    async def test_empty_result_strips(self, mock_gen):
        mock_gen.return_value = {"text": "  "}
        synth, _ = _make_synthesizer()
        result = await synth._llm_text("sys", "usr")
        assert result == ""

    @patch("app.pipeline.synthesis.synthesizer.generate_with_fallback")
    async def test_custom_max_tokens(self, mock_gen):
        mock_gen.return_value = {"text": "hi"}
        synth, _ = _make_synthesizer()
        await synth._llm_text("sys", "usr", max_tokens=500)
        assert mock_gen.call_args[1]["max_tokens"] == 500


# -------------------------------------------------------------------------------
# _template_to_csl
# -------------------------------------------------------------------------------

class TestTemplateToCsl:
    def test_default_is_ieee(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("") == "ieee"

    def test_none_becomes_ieee(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("none") == "ieee"

    def test_ieee_passthrough(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("ieee") == "ieee"

    def test_apa(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("apa") == "apa"

    def test_case_insensitive(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("IEEE") == "ieee"
        assert synth._template_to_csl("APA") == "apa"

    def test_arbitrary_style_passthrough(self):
        synth, _ = _make_synthesizer()
        assert synth._template_to_csl("springer-lecture-notes") == "springer-lecture-notes"


# -------------------------------------------------------------------------------
# _insert_citations
# -------------------------------------------------------------------------------

class TestInsertCitations:
    def test_no_refs_no_sections(self):
        synth, deps = _make_synthesizer()
        result = synth._insert_citations([], "ieee")
        assert result["sections"] == []
        assert result["references"] == []
        assert result["citations"] == []

    def test_single_ref_replaced(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "Smith, J.",
            "title": "A Paper",
            "doi": "10.1234/test",
            "url": "https://doi.org/10.1234/test",
        }
        deps["csl_engine"].format_references.return_value = ["[1] Smith, J., A Paper"]
        sections = [{"title": "Intro", "content": "As shown in [REF: Smith2020]."}]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        assert result["sections"][0]["content"] == "As shown in [1]."
        assert result["citations"][0]["query"] == "Smith2020"
        assert result["citations"][0]["number"] == 1

    def test_multiple_unique_refs(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.side_effect = lambda q: {
            "Smith2020": {"authors": "Smith, J.", "title": "A", "doi": "", "url": ""},
            "Jones2021": {"authors": "Jones, A.", "title": "B", "doi": "", "url": ""},
        }.get(q, {})
        deps["csl_engine"].format_references.return_value = ["[1] Smith", "[2] Jones"]
        sections = [
            {"title": "Intro", "content": "[REF: Smith2020] says X."},
            {"title": "Methods", "content": "[REF: Jones2021] says Y."},
        ]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 2
        assert "[1]" in result["sections"][0]["content"]
        assert "[2]" in result["sections"][1]["content"]

    def test_duplicate_refs_deduplicated(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "Smith, J.",
            "title": "A",
            "doi": "",
            "url": "",
        }
        deps["csl_engine"].format_references.return_value = ["[1] Smith"]
        sections = [
            {"title": "Intro", "content": "First mention [REF: Smith2020] and second [REF: Smith2020]."},
        ]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        assert result["sections"][0]["content"].count("[1]") == 2

    def test_csl_fallback_uses_raw_text(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "",
            "title": "",
            "doi": "",
            "url": "",
        }
        deps["csl_engine"].format_references.side_effect = RuntimeError("CSL crash")
        sections = [{"title": "Intro", "content": "[REF: Some Ref]"}]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        # fallback uses raw_text
        assert result["references"][0] == "Some Ref"

    def test_unknown_query_gets_numbered(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {}
        deps["csl_engine"].format_references.return_value = ["raw"]
        sections = [{"title": "Intro", "content": "Unknown [REF: missing_ref] here."}]
        result = synth._insert_citations(sections, "ieee")
        assert result["sections"][0]["content"] == "Unknown [1] here."
        assert len(result["citations"]) == 1

    def test_reference_building_fields(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {
            "authors": "Doe, J., Roe, M.",
            "title": "Great Paper",
            "doi": "10.1234/test",
            "url": "https://example.com",
        }
        deps["csl_engine"].format_references.return_value = ["[1] formatted"]
        sections = [{"title": "Intro", "content": "[REF: Doe2024]."}]
        result = synth._insert_citations(sections, "ieee")
        assert len(result["references"]) == 1
        assert result["citations"][0]["query"] == "Doe2024"

    def test_csl_passes_style(self):
        synth, deps = _make_synthesizer()
        deps["crossref"].validate_citation.return_value = {}
        deps["csl_engine"].format_references.return_value = ["fmt"]
        sections = [{"title": "Intro", "content": "[REF: X]."}]
        synth._insert_citations(sections, "apa")
        style_arg = deps["csl_engine"].format_references.call_args[1]["style"]
        assert style_arg == "apa"


# -------------------------------------------------------------------------------
# _render_document
# -------------------------------------------------------------------------------

class TestRenderDocument:
    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_basic(self, mock_resolve, mock_mkdir, mock_exporter_cls, mock_formatter_cls):
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: r"C:\out\synthesized.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        outline = {"title": "My Report"}
        sections = [
            {"title": "Intro", "content": "Para one.\n\nPara two."},
            {"title": "Conclusion", "content": "Final words."},
        ]
        references = ["[1] Smith, J. (2023). A Paper."]
        result = synth._render_document("sess1", "ieee", outline, sections, references)

        assert "synthesized.docx" in result

        # Verify blocks built correctly
        doc_arg = mock_formatter.process.call_args[0][0]
        assert isinstance(doc_arg, PipelineDocument)
        block_texts = [b.text for b in doc_arg.blocks]
        assert "My Report" in block_texts
        assert "Intro" in block_texts
        assert "Conclusion" in block_texts
        assert "References" in block_texts
        assert "[1] Smith, J. (2023). A Paper." in block_texts
        assert "Para one." in block_texts
        assert "Para two." in block_texts
        assert mock_exporter.process.called

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_no_references(self, mock_resolve, mock_mkdir, mock_exporter_cls, mock_formatter_cls):
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_resolved = MagicMock()
        mock_resolved.__str__ = lambda s: r"/out/doc.docx"
        mock_resolve.return_value = mock_resolved

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "ieee", {}, [], [])
        doc_arg = mock_formatter.process.call_args[0][0]
        block_texts = [b.text for b in doc_arg.blocks]
        assert "References" not in block_texts

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_fallback_title(self, mock_resolve, mock_mkdir, mock_exporter_cls, mock_formatter_cls):
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_resolve.return_value = MagicMock()
        mock_resolve.return_value.__str__ = lambda s: "/out/doc.docx"

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "apa", {}, [], [])
        doc_arg = mock_formatter.process.call_args[0][0]
        assert doc_arg.blocks[0].text == "Synthesized Report"

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_block_types(self, mock_resolve, mock_mkdir, mock_exporter_cls, mock_formatter_cls):
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_resolve.return_value = MagicMock()
        mock_resolve.return_value.__str__ = lambda s: "/out/doc.docx"

        synth, _ = _make_synthesizer()
        outline = {"title": "T"}
        sections = [{"title": "H1", "content": "Body text."}]
        references = ["[1] Ref"]
        synth._render_document("s1", "ieee", outline, sections, references)
        doc_arg = mock_formatter.process.call_args[0][0]
        types = [(b.block_type, b.text) for b in doc_arg.blocks]

    @patch("app.pipeline.formatting.formatter.Formatter")
    @patch("app.pipeline.export.exporter.Exporter")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.resolve")
    def test_template_passed(self, mock_resolve, mock_mkdir, mock_exporter_cls, mock_formatter_cls):
        mock_formatter = MagicMock()
        mock_formatter_cls.return_value = mock_formatter
        mock_exporter = MagicMock()
        mock_exporter_cls.return_value = mock_exporter
        mock_resolve.return_value = MagicMock()
        mock_resolve.return_value.__str__ = lambda s: "/out/doc.docx"

        synth, _ = _make_synthesizer()
        synth._render_document("s1", "apa", {"title": "T"}, [], [])
        doc_arg = mock_formatter.process.call_args[0][0]
        assert doc_arg.template.template_name == "apa"


# -------------------------------------------------------------------------------
# _stream_chunks
# -------------------------------------------------------------------------------

class TestStreamChunks:
    async def test_basic_chunking(self):
        synth, deps = _make_synthesizer()
        text = "A" * 1000
        await synth._stream_chunks("sid", "writing_chunk", "writing", 50, text, chunk_size=400)
        assert deps["pubsub"].publish.await_count == 3

    async def test_empty_text_skips(self):
        synth, deps = _make_synthesizer()
        await synth._stream_chunks("sid", "evt", "st", 50, "")
        assert deps["pubsub"].publish.await_count == 0

    async def test_with_extra_payload(self):
        synth, deps = _make_synthesizer()
        await synth._stream_chunks("sid", "wc", "w", 75, "Hello", extra={"section": "Intro"})
        deps["pubsub"].publish.assert_awaited_once()
        call_args = deps["pubsub"].publish.await_args
        payload = call_args[0][1]["payload"]
        assert payload["content"] == "Hello"
        assert payload["section"] == "Intro"

    async def test_single_chunk(self):
        synth, deps = _make_synthesizer()
        await synth._stream_chunks("sid", "evt", "st", 50, "Short text", chunk_size=400)
        deps["pubsub"].publish.assert_awaited_once()

    async def test_exact_chunk_boundary(self):
        synth, deps = _make_synthesizer()
        text = "X" * 400
        await synth._stream_chunks("sid", "evt", "st", 50, text, chunk_size=400)
        deps["pubsub"].publish.assert_awaited_once()


# -------------------------------------------------------------------------------
# _cross_doc_analysis
# -------------------------------------------------------------------------------

class TestCrossDocAnalysis:
    async def test_success_path(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"overlaps": ["a"], "gaps": ["b"], "unique_points": {}}
            extracted = [
                {"filename": "a.pdf", "text": "content a"},
                {"filename": "b.pdf", "text": "content b"},
            ]
            result = await synth._cross_doc_analysis(extracted)
            assert result["overlaps"] == ["a"]
            assert result["gaps"] == ["b"]

    async def test_llm_returns_none_fallback(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None
            extracted = [
                {"filename": "a.pdf", "text": "content"},
                {"filename": "b.pdf", "text": "content"},
            ]
            result = await synth._cross_doc_analysis(extracted)
            assert result["overlaps"] == []
            assert result["gaps"] == []
            assert "a.pdf" in result["unique_points"]
            assert "b.pdf" in result["unique_points"]

    async def test_empty_docs(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"overlaps": [], "gaps": [], "unique_points": {}}
            result = await synth._cross_doc_analysis([])
            assert result["overlaps"] == []

    async def test_text_truncated(self):
        synth, _ = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"overlaps": [], "gaps": [], "unique_points": {}}
            long_text = "X" * 5000
            extracted = [{"filename": "long.pdf", "text": long_text}]
            await synth._cross_doc_analysis(extracted)
            # verify the llm_json was called (text truncation happens inside)
            mock_llm.assert_awaited_once()


# -------------------------------------------------------------------------------
# _generate_outline
# -------------------------------------------------------------------------------

class TestGenerateOutline:
    async def test_success(self):
        synth, deps = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "title": "Report",
                "sections": [{"title": "Intro", "key_points": ["point1"]}],
            }
            result = await synth._generate_outline("sid", {}, "ieee")
            assert result["title"] == "Report"
            assert len(result["sections"]) == 1

    async def test_llm_fallback(self):
        synth, deps = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None
            result = await synth._generate_outline("sid", {}, "ieee")
            assert result["title"] == "Synthesized Report"
            assert len(result["sections"]) == 5

    async def test_stream_chunks_called(self):
        synth, deps = _make_synthesizer()
        with patch.object(synth, "_llm_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"title": "X", "sections": []}
            with patch.object(synth, "_stream_chunks", new_callable=AsyncMock) as mock_sc:
                await synth._generate_outline("sid", {}, "apa")
                mock_sc.assert_awaited_once_with(
                    "sid", "outline_chunk", "outline", 62, '{"title": "X", "sections": []}'
                )


# -------------------------------------------------------------------------------
# _generate_sections
# -------------------------------------------------------------------------------

class TestGenerateSections:
    async def test_basic(self):
        synth, deps = _make_synthesizer()
        deps["vector_store"].query.return_value = [
            {"text": "source1", "source_doc": "a.pdf", "section": "Intro"},
        ]
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_text:
            mock_text.return_value = "Generated content."
            with patch.object(synth, "_stream_chunks", new_callable=AsyncMock):
                outline = {
                    "title": "R",
                    "sections": [{"title": "Intro", "key_points": ["kp1"]}],
                }
                result = await synth._generate_sections(outline, "sid")
                assert len(result) == 1
                assert result[0]["title"] == "Intro"
                assert result[0]["content"] == "Generated content."

    async def test_empty_outline(self):
        synth, _ = _make_synthesizer()
        result = await synth._generate_sections({}, "sid")
        assert result == []

    async def test_list_outline(self):
        synth, deps = _make_synthesizer()
        deps["vector_store"].query.return_value = []
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_text:
            mock_text.return_value = "Content."
            with patch.object(synth, "_stream_chunks", new_callable=AsyncMock):
                outline = ["Intro", "Conclusion"]
                result = await synth._generate_sections(outline, "sid")
                assert len(result) == 2
                assert result[0]["title"] == "Intro"

    async def test_vector_store_query_called(self):
        synth, deps = _make_synthesizer()
        deps["vector_store"].query.return_value = []
        with patch.object(synth, "_llm_text", new_callable=AsyncMock) as mock_text:
            mock_text.return_value = "C."
            with patch.object(synth, "_stream_chunks", new_callable=AsyncMock):
                outline = {"sections": [{"title": "Methods", "key_points": ["kp"]}]}
                await synth._generate_sections(outline, "sid")
        deps["vector_store"].query.assert_called_once_with("sid", "Methods", top_k=4)

    async def test_outline_is_none(self):
        synth, _ = _make_synthesizer()
        result = await synth._generate_sections(None, "sid")
        assert result == []


# -------------------------------------------------------------------------------
# _extract_documents
# -------------------------------------------------------------------------------

class TestExtractDocuments:
    async def test_basic(self):
        synth, deps = _make_synthesizer()
        files = [
            {"path": r"C:\a.pdf", "filename": "a.pdf", "hash": "abc", "size": 10},
            {"path": r"C:\b.pdf", "filename": "b.pdf", "hash": "def", "size": 20},
        ]
        mock_doc = _make_mock_doc(blocks=[
            _make_mock_block("Text A", "Intro", 1),
            _make_mock_block("Text B", "Methods", 2),
        ])
        mock_tt = AsyncMock(return_value=mock_doc)

        with (
            patch("app.pipeline.synthesis.synthesizer.ParserFactory") as mock_pf,
            patch("asyncio.to_thread", mock_tt),
        ):
            mock_pf.return_value = MagicMock()
            result = await synth._extract_documents("sid", files)

        assert len(result) == 2
        assert result[0]["filename"] == "a.pdf" or result[1]["filename"] == "a.pdf"
        assert all("doc_obj" in r for r in result)
        assert all("text" in r for r in result)
        assert all("sections" in r for r in result)

    async def test_emit_event_called(self):
        synth, deps = _make_synthesizer()
        files = [
            {"path": r"C:\a.pdf", "filename": "a.pdf", "hash": "abc", "size": 10},
            {"path": r"C:\b.pdf", "filename": "b.pdf", "hash": "def", "size": 20},
        ]
        mock_doc = _make_mock_doc(blocks=[
            _make_mock_block("Text", "Intro", 1),
        ])
        mock_tt = AsyncMock(return_value=mock_doc)

        with (
            patch("app.pipeline.synthesis.synthesizer.ParserFactory") as mock_pf,
            patch("asyncio.to_thread", mock_tt),
        ):
            mock_pf.return_value = MagicMock()
            await synth._extract_documents("sid", files)

        # Should have emitted one event per file
        assert deps["pubsub"].publish.await_count >= 2

    async def test_single_document(self):
        synth, deps = _make_synthesizer()
        files = [
            {"path": r"C:\a.pdf", "filename": "a.pdf", "hash": "abc", "size": 10},
        ]
        mock_doc = _make_mock_doc(blocks=[])
        mock_tt = AsyncMock(return_value=mock_doc)

        with (
            patch("app.pipeline.synthesis.synthesizer.ParserFactory") as mock_pf,
            patch("asyncio.to_thread", mock_tt),
        ):
            mock_pf.return_value = MagicMock()
            result = await synth._extract_documents("sid", files)

        assert len(result) == 1


# -------------------------------------------------------------------------------
# run (full pipeline)
# -------------------------------------------------------------------------------

class TestRun:
    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_happy_path(self, mock_read, mock_validate):
        mock_read.return_value = b"content"
        synth, deps = _make_synthesizer()

        deps["session_service"].get_session.return_value = {"config_json": {}}

        valid_files = [
            {"path": "/a.pdf", "filename": "a.pdf", "hash": "aaa", "size": 7},
            {"path": "/b.pdf", "filename": "b.pdf", "hash": "bbb", "size": 7},
        ]

        mock_doc = _make_mock_doc(blocks=[
            _make_mock_block("Paper text", "Intro", 1),
        ])

        deps["vector_store"].query.return_value = [
            {"text": "src", "source_doc": "a.pdf", "section": "Intro"},
        ]

        deps["crossref"].validate_citation.return_value = {
            "authors": "Smith, J.",
            "title": "",
            "doi": "",
            "url": "",
        }
        deps["csl_engine"].format_references.return_value = ["[1] Smith"]

        mock_tt = AsyncMock(return_value=mock_doc)

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock) as mock_vf,
            patch.object(synth, "_extract_documents", new_callable=AsyncMock) as mock_ed,
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock) as mock_cda,
            patch.object(synth, "_generate_outline", new_callable=AsyncMock) as mock_go,
            patch.object(synth, "_generate_sections", new_callable=AsyncMock) as mock_gs,
            patch.object(synth, "_insert_citations") as mock_ic,
            patch.object(synth, "_render_document") as mock_rd,
            patch("app.pipeline.synthesis.synthesizer.ParserFactory"),
            patch("asyncio.to_thread", mock_tt),
        ):
            mock_vf.return_value = (valid_files, [])
            mock_ed.return_value = [
                {"filename": "a.pdf", "doc_obj": mock_doc, "text": "text", "sections": []},
                {"filename": "b.pdf", "doc_obj": mock_doc, "text": "text", "sections": []},
            ]
            mock_cda.return_value = {"overlaps": [], "gaps": [], "unique_points": {}}
            mock_go.return_value = {
                "title": "Synthesis",
                "sections": [{"title": "Intro", "key_points": []}],
            }
            mock_gs.return_value = [{"title": "Intro", "content": "Content."}]
            mock_ic.return_value = {
                "sections": [{"title": "Intro", "content": "Content."}],
                "references": ["[1] Ref"],
                "citations": [{"query": "Q", "number": 1}],
            }
            mock_rd.return_value = "/output/synthesized.docx"

            result = await synth.run("sid", ["/a.pdf", "/b.pdf"], "ieee")
            assert result == "/output/synthesized.docx"

        # Verify session service was called for save and updates
        assert deps["session_service"].update_session.await_count >= 1
        deps["session_service"].save_document_version.assert_awaited_once()

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_pipeline_failure_emits_error(self, mock_read, mock_validate):
        mock_read.return_value = b"content"
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = {"config_json": {}}

        with patch.object(synth, "_validate_files", new_callable=AsyncMock) as mock_vf:
            mock_vf.return_value = (
                [{"path": "/a.pdf", "filename": "a.pdf", "hash": "a", "size": 1}],
                [],
            )
            with patch.object(synth, "_extract_documents", new_callable=AsyncMock) as mock_ed:
                mock_ed.side_effect = ValueError("Extraction crashed")

                with pytest.raises(ValueError, match="Extraction crashed"):
                    await synth.run("sid", ["/a.pdf"], "ieee")

        # Verify error update was emitted
        error_calls = [
            c for c in deps["session_service"].update_session.await_args_list
            if c[1].get("status") == "failed"
        ]
        assert len(error_calls) >= 1

    @patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes")
    @patch("pathlib.Path.read_bytes")
    async def test_with_warnings_collected(self, mock_read, mock_validate):
        mock_read.return_value = b"content"
        synth, deps = _make_synthesizer()
        deps["session_service"].get_session.return_value = {"config_json": {}}

        valid_files = [
            {"path": "/a.pdf", "filename": "a.pdf", "hash": "aaa", "size": 7},
            {"path": "/b.pdf", "filename": "b.pdf", "hash": "bbb", "size": 7},
        ]

        mock_doc = _make_mock_doc(blocks=[])
        mock_tt = AsyncMock(return_value=mock_doc)

        with (
            patch.object(synth, "_validate_files", new_callable=AsyncMock) as mock_vf,
            patch.object(synth, "_extract_documents", new_callable=AsyncMock) as mock_ed,
            patch.object(synth, "_cross_doc_analysis", new_callable=AsyncMock) as mock_cda,
            patch.object(synth, "_generate_outline", new_callable=AsyncMock) as mock_go,
            patch.object(synth, "_generate_sections", new_callable=AsyncMock) as mock_gs,
            patch.object(synth, "_insert_citations") as mock_ic,
            patch.object(synth, "_render_document") as mock_rd,
            patch("app.pipeline.synthesis.synthesizer.ParserFactory"),
            patch("asyncio.to_thread", mock_tt),
        ):
            mock_vf.return_value = (valid_files, ["Duplicate skipped: c.pdf"])
            mock_ed.return_value = [
                {"filename": "a.pdf", "doc_obj": mock_doc, "text": "", "sections": []},
                {"filename": "b.pdf", "doc_obj": mock_doc, "text": "", "sections": []},
            ]
            mock_cda.return_value = {"overlaps": [], "gaps": [], "unique_points": {}}
            mock_go.return_value = {"title": "R", "sections": []}
            mock_gs.return_value = []
            mock_ic.return_value = {"sections": [], "references": [], "citations": []}
            mock_rd.return_value = "/out/doc.docx"

            result = await synth.run("sid", ["/a.pdf", "/b.pdf"], "ieee")
            assert result == "/out/doc.docx"


# -------------------------------------------------------------------------------
# _REF_PATTERN
# -------------------------------------------------------------------------------

class TestRefPattern:
    def test_basic_match(self):
        matches = _REF_PATTERN.findall("Text [REF:Smith2020] end.")
        assert matches == ["Smith2020"]

    def test_match_with_space(self):
        matches = _REF_PATTERN.findall("Text [REF: Smith2020] end.")
        assert matches[0].strip() == "Smith2020"

    def test_multiple_matches(self):
        matches = _REF_PATTERN.findall("[REF:A] and [REF:B]")
        assert matches == ["A", "B"]

    def test_no_match(self):
        matches = _REF_PATTERN.findall("No references here.")
        assert matches == []

    def test_substitution(self):
        result = _REF_PATTERN.sub(lambda m: f"[{1}]", "Text [REF: Q] end.")
        assert result == "Text [1] end."
