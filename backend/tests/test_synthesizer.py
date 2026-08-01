import pytest
from unittest.mock import MagicMock


class TestTemplateToCsl:
    def test_ieee_style(self):
        synth = _make_synth()
        assert synth._template_to_csl("ieee") == "ieee"

    def test_apa_style(self):
        synth = _make_synth()
        assert synth._template_to_csl("apa") == "apa"

    def test_none_falls_to_ieee(self):
        synth = _make_synth()
        assert synth._template_to_csl("none") == "ieee"

    def test_empty_falls_to_ieee(self):
        synth = _make_synth()
        assert synth._template_to_csl("") == "ieee"


class TestExtractJson:
    def test_extracts_from_clean_json(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        assert MultiDocSynthesizer._extract_json('{"a":1}') == '{"a":1}'

    def test_extracts_from_fenced(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        assert MultiDocSynthesizer._extract_json('```json\n{"a":1}\n```') == '{"a":1}'

    def test_returns_none_when_no_braces(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        assert MultiDocSynthesizer._extract_json("no braces") is None


class TestChunkText:
    def test_single_chunk(self):
        synth = _make_synth()
        chunks = synth._chunk_text("Hello world", "doc1", "Intro", 1, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello world"
        assert chunks[0]["source_doc"] == "doc1"

    def test_multiple_chunks_with_overlap(self):
        synth = _make_synth()
        text = "Hello " * 500
        chunks = synth._chunk_text(text, "doc1", "Intro", None, chunk_size=200, overlap=50)
        assert len(chunks) >= 2

    def test_empty_text(self):
        synth = _make_synth()
        assert synth._chunk_text("", "doc1", "Intro", None) == []


class TestFakeUpload:
    def test_filename(self):
        from app.pipeline.synthesis.synthesizer import _FakeUpload
        f = _FakeUpload("test.pdf")
        assert f.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_read(self):
        from app.pipeline.synthesis.synthesizer import _FakeUpload
        f = _FakeUpload("test.pdf")
        data = await f.read()
        assert data == b""


def _make_synth():
    from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
    return MultiDocSynthesizer(
        session_service=MagicMock(),
        vector_store=MagicMock(),
        llm_service=MagicMock(),
        pipeline_orchestrator=MagicMock(),
        pubsub=MagicMock(),
    )
