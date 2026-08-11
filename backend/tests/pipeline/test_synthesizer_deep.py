# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for MultiDocSynthesizer pipeline stage.
Covers run() 8-stage pipeline, helper methods, LLM/CSL integration,
event publishing, error handling.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

@pytest.fixture(autouse=True)
def _patch_validation():
    with patch("app.pipeline.synthesis.synthesizer.ACCEPTED_EXTENSIONS", {'.pdf', '.docx', '.doc', '.md', '.html', '.txt', '.tex', '.odt', '.rtf'}), \
         patch("app.pipeline.synthesis.synthesizer._validate_magic_bytes", new_callable=AsyncMock):
        yield

OUTLINE = {"title": "Synthesis", "sections": [{"title": "Intro", "chunks": ["chunk1"]}]}
SECTIONS = [{"title": "Intro", "content": "Generated content.", "citations": []}]
REFERENCES = ["Author (2024). Title. Journal, 1(1), 1-10."]

@pytest.fixture
def mock_session_service():
    m = AsyncMock()
    m.get_session.return_value = {"config_json": {"style": "apa"}}
    m.update_session = AsyncMock()
    m.save_document_version = AsyncMock()
    return m

@pytest.fixture
def mock_vector_store():
    m = MagicMock()
    m.create_collection = MagicMock()
    m.add_chunks = MagicMock()
    return m

@pytest.fixture
def mock_llm():
    m = AsyncMock()
    m.generate = AsyncMock(return_value="LLM output")
    return m

@pytest.fixture
def mock_orchestrator():
    m = MagicMock()
    m._run_extraction_stage = MagicMock()
    return m

@pytest.fixture
def mock_pubsub():
    m = AsyncMock()
    m.publish = AsyncMock()
    return m

@pytest.fixture
def mock_crossref():
    m = AsyncMock()
    m.search.return_value = [{"DOI": "10.1000/test", "title": ["Test"]}]
    return m

@pytest.fixture
def synt(mock_session_service, mock_vector_store, mock_llm, mock_orchestrator, mock_pubsub):
    from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
    return MultiDocSynthesizer(
        session_service=mock_session_service,
        vector_store=mock_vector_store,
        llm_service=mock_llm,
        pipeline_orchestrator=mock_orchestrator,
        pubsub=mock_pubsub,
    )

class TestInit:
    def test_initializes(self, mock_session_service, mock_vector_store, mock_llm, mock_orchestrator, mock_pubsub):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        s = MultiDocSynthesizer(
            session_service=mock_session_service, vector_store=mock_vector_store,
            llm_service=mock_llm, pipeline_orchestrator=mock_orchestrator, pubsub=mock_pubsub,
        )
        assert s.session_service is mock_session_service
        assert s.vector_store is mock_vector_store
        assert s.llm_service is mock_llm
        assert s.pipeline_orchestrator is mock_orchestrator
        assert s.pubsub is mock_pubsub

class TestRun:
    @pytest.mark.asyncio
    async def test_run_full_pipeline(self, synt, mock_session_service, tmp_path):
        out_path = str(tmp_path / "out.docx")
        with (
            patch.object(synt, "_validate_files", new_callable=AsyncMock, return_value=([{"path": "a.docx", "filename": "a.docx"}], [])),
            patch.object(synt, "_extract_documents", new_callable=AsyncMock, return_value=[{"filename": "a.docx", "sections": ["Intro"]}]),
            patch.object(synt, "_build_chunks", return_value=[]),
            patch.object(synt, "_cross_doc_analysis", new_callable=AsyncMock, return_value={"topics": ["AI"]}),
            patch.object(synt, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synt, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synt, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synt, "_render_document", return_value=out_path),
        ):
            result = await synt.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path
            mock_session_service.save_document_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_no_session(self, synt):
        synt.session_service.get_session.return_value = None
        out_path = "/tmp/out.docx"
        with (
            patch.object(synt, "_validate_files", new_callable=AsyncMock, return_value=([{"path": "a.docx"}], [])),
            patch.object(synt, "_extract_documents", new_callable=AsyncMock, return_value=[{"filename": "a.docx", "sections": []}]),
            patch.object(synt, "_build_chunks", return_value=[]),
            patch.object(synt, "_cross_doc_analysis", new_callable=AsyncMock, return_value={}),
            patch.object(synt, "_generate_outline", new_callable=AsyncMock, return_value=OUTLINE),
            patch.object(synt, "_generate_sections", new_callable=AsyncMock, return_value=SECTIONS),
            patch.object(synt, "_insert_citations", return_value={"sections": SECTIONS, "references": REFERENCES, "citations": []}),
            patch.object(synt, "_render_document", return_value=out_path),
        ):
            result = await synt.run("session1", ["a.docx", "b.docx"], "default")
            assert result == out_path

    @pytest.mark.asyncio
    async def test_run_propagates_error(self, synt):
        with patch.object(synt, "_validate_files", new_callable=AsyncMock, side_effect=RuntimeError("pipeline failed")):
            with pytest.raises(RuntimeError):
                await synt.run("session1", ["a.docx", "b.docx"], "default")

class TestValidateFiles:
    @pytest.mark.asyncio
    async def test_validates_correctly(self, synt):
        contents = iter([b"content_a", b"content_b"])
        with (
            patch("pathlib.Path.read_bytes", side_effect=lambda: next(contents)),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result, warns = await synt._validate_files(["a.docx", "b.docx"])
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_too_few_files_raises(self, synt):
        with pytest.raises(Exception):
            await synt._validate_files(["a.docx"])

    @pytest.mark.asyncio
    async def test_too_many_files_raises(self, synt):
        with pytest.raises(Exception):
            await synt._validate_files([f"f{i}.docx" for i in range(8)])

    @pytest.mark.asyncio
    async def test_unsupported_ext_raises(self, synt):
        with pytest.raises(Exception):
            await synt._validate_files(["a.xyz", "b.docx"])

    @pytest.mark.asyncio
    async def test_duplicates_detected(self, synt):
        contents = iter([b"same", b"different", b"same"])
        with (
            patch("pathlib.Path.read_bytes", side_effect=lambda: next(contents)),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result, warns = await synt._validate_files(["a.docx", "b.docx", "c.docx"])
            assert len(warns) == 1
            assert "Duplicate" in warns[0]
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_less_than_two_unique_raises(self, synt):
        contents = iter([b"same", b"same"])
        with (
            patch("pathlib.Path.read_bytes", side_effect=lambda: next(contents)),
            patch("pathlib.Path.exists", return_value=True),pytest.raises(Exception, match="2 unique")
        ):
            await synt._validate_files(["a.docx", "b.docx"])

class TestExtractDocuments:
    @pytest.mark.asyncio
    async def test_extracts(self, synt):
        from app.models import Block, PipelineDocument
        doc = PipelineDocument(document_id="d1", blocks=[
            Block(block_id="b1", index=0, text="Content", section_name="Intro"),
        ])
        synt.pipeline_orchestrator._run_extraction_stage.return_value = doc
        result = await synt._extract_documents("s1", [{"path": "/tmp/a.docx", "filename": "a.docx"}])
        assert len(result) == 1
        assert result[0]["filename"] == "a.docx"
        assert "Content" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_extract_empty_blocks(self, synt):
        from app.models import PipelineDocument
        synt.pipeline_orchestrator._run_extraction_stage.return_value = PipelineDocument(document_id="d1")
        result = await synt._extract_documents("s1", [{"path": "/tmp/a.docx", "filename": "a.docx"}])
        assert result[0]["text"] == ""

class TestChunking:
    def test_chunk_text(self, synt):
        result = synt._chunk_text("Hello world", "a.docx", "Intro", None, chunk_size=100, overlap=0)
        assert len(result) == 1
        assert result[0]["text"] == "Hello world"

    def test_chunk_text_empty(self, synt):
        result = synt._chunk_text("", "a.docx", "Intro", None, chunk_size=100, overlap=0)
        assert result == []

    def test_chunk_text_long(self, synt):
        text = "word " * 500
        result = synt._chunk_text(text, "a.docx", "Intro", None, chunk_size=100, overlap=0)
        assert len(result) > 1

    def test_build_chunks(self, synt):
        from app.models import Block, BlockType, PipelineDocument
        doc = PipelineDocument(document_id="d1", blocks=[
            Block(block_id="b1", index=0, text="Hello world", block_type=BlockType.BODY, section_name="Intro"),
        ])
        docs = [{"text": "Hello world", "filename": "a.docx", "sections": ["Intro"], "doc_obj": doc}]
        result = synt._build_chunks(docs)
        assert len(result) >= 1

class TestCrossDocAnalysis:
    @pytest.mark.asyncio
    async def test_analysis_calls_llm(self, synt):
        with patch.object(synt, "_llm_json", new_callable=AsyncMock, return_value={"topics": ["AI"]}):
            result = await synt._cross_doc_analysis([{"text": "AI research", "sections": ["Intro"]}])
            assert "topics" in result

    @pytest.mark.asyncio
    async def test_analysis_empty_docs(self, synt):
        with patch.object(synt, "_llm_json", new_callable=AsyncMock, return_value={}):
            result = await synt._cross_doc_analysis([])
            assert isinstance(result, dict)

class TestGenerateOutline:
    @pytest.mark.asyncio
    async def test_outline_calls_llm(self, synt):
        with patch.object(synt, "_llm_json", new_callable=AsyncMock, return_value=OUTLINE):
            result = await synt._generate_outline("s1", {}, "default")
            assert result["title"] == "Synthesis"

    @pytest.mark.asyncio
    async def test_outline_with_analysis(self, synt):
        analysis = {"topics": ["AI"], "gaps": ["ethics"]}
        with patch.object(synt, "_llm_json", new_callable=AsyncMock, return_value=OUTLINE):
            result = await synt._generate_outline("s1", analysis, "default")
            assert result is not None

class TestGenerateSections:
    @pytest.mark.asyncio
    async def test_generates_sections(self, synt):
        with patch.object(synt, "_llm_text", new_callable=AsyncMock, return_value="Generated section content."):
            result = await synt._generate_sections(OUTLINE, "s1")
            assert len(result) == 1
            assert "content" in result[0]

    @pytest.mark.asyncio
    async def test_generates_empty_outline(self, synt):
        result = await synt._generate_sections({"sections": []}, "s1")
        assert result == []

class TestInsertCitations:
    def test_insert_citations(self, synt):
        result = synt._insert_citations(SECTIONS, "default")
        assert "sections" in result
        assert "references" in result

    def test_insert_citations_empty(self, synt):
        result = synt._insert_citations([], "default")
        assert result["sections"] == []

class TestLLMHelpers:
    @pytest.mark.asyncio
    async def test_llm_text(self, synt):
        with patch("app.pipeline.synthesis.synthesizer.generate_with_fallback") as mock_gen:
            mock_gen.return_value = {"text": "Generated"}
            result = await synt._llm_text("system prompt", "user prompt")
            assert result == "Generated"

    @pytest.mark.asyncio
    async def test_llm_json(self, synt):
        with patch.object(synt, "_llm_text", new_callable=AsyncMock, return_value='{"key": "value"}'):
            result = await synt._llm_json("system prompt", "user prompt")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_llm_json_fallback(self, synt):
        with patch.object(synt, "_llm_text", new_callable=AsyncMock, return_value="not json"):
            result = await synt._llm_json("system prompt", "user prompt")
            assert result is None

class TestExtractJson:
    def test_extract_json_valid(self, synt):
        assert synt._extract_json('{"a": 1}') == '{"a": 1}'

    def test_extract_json_code_block(self, synt):
        assert synt._extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_extract_json_invalid(self, synt):
        assert synt._extract_json("not json") is None

    def test_extract_json_empty(self, synt):
        assert synt._extract_json("") is None

class TestTemplateToCsl:
    def test_default_template(self, synt):
        result = synt._template_to_csl("default")
        assert result is not None

    def test_ieee_template(self, synt):
        result = synt._template_to_csl("ieee")
        assert result is not None

    def test_unknown_template(self, synt):
        result = synt._template_to_csl("unknown")
        assert result is not None

class TestEventPublishing:
    @pytest.mark.asyncio
    async def test_update_status(self, synt, mock_pubsub):
        await synt._update_status("s1", "processing", 50, "Working...", {})
        mock_pubsub.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_with_stage(self, synt, mock_pubsub):
        await synt._update_status("s1", "processing", 50, "Working...", {}, stage="writing")
        mock_pubsub.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event(self, synt, mock_pubsub):
        await synt._emit_event("s1", "stage_update", "writing", 75, "Writing...")
        mock_pubsub.publish.assert_called_once()

class TestRenderDocument:
    def test_render(self, synt, tmp_path):
        from app.pipeline.export.exporter import Exporter
        from app.pipeline.formatting.formatter import Formatter
        with patch.object(Formatter, "process") as mock_fmt:
            mock_fmt.return_value = MagicMock()
            with patch.object(Exporter, "process") as mock_exp:
                mock_exp.return_value = None
                result = synt._render_document("s1", "default", OUTLINE, SECTIONS, REFERENCES)
                assert result is not None

# Done
