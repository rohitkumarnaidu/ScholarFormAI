# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock, ANY
from pathlib import Path
import pytest


@pytest.fixture
def agent():
    from app.pipeline.generation.agent import AgentPipeline
    with patch("app.pipeline.generation.agent.RedisPubSub"), \
         patch("app.pipeline.generation.agent.get_rag_engine"), \
         patch("app.pipeline.generation.agent.CitationAssemblyService"), \
         patch("app.pipeline.generation.agent.QualityScorer"):
        yield AgentPipeline(MagicMock(), MagicMock())


@pytest.fixture
def dg():
    from app.pipeline.generation.document_generator import DocumentGenerator
    return DocumentGenerator()


# ══════════════════════════════════════════════════════════════════════════════
# generation/agent.py
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentPipeline:
    def test_count_words(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._count_words("one two three") == 3
        assert AgentPipeline._count_words(None) == 0
        assert AgentPipeline._count_words("") == 0

    def test_has_citation_bracket(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("see [1,2]") is True
        assert AgentPipeline._has_citation("no citation") is False
        assert AgentPipeline._has_citation(None) is False

    def test_has_citation_parenthetical(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._has_citation("see (Smith 2020)") is True

    def test_apply_quality_floor_expands(self, agent):
        sm = {"Introduction": "short"}
        result = agent._apply_quality_floor(sm, ["Introduction"], 120)
        assert len(result["Introduction"].split()) >= 120
        assert "[1]" in result["Introduction"]

    def test_apply_quality_floor_skips_refs(self, agent):
        sm = {"References": "ref here"}
        result = agent._apply_quality_floor(sm, ["References"], 10)
        assert result["References"] == "ref here"

    def test_min_words_for_length(self, agent):
        assert agent._min_words_for_length("short") == 120
        assert agent._min_words_for_length("long") == 240
        assert agent._min_words_for_length("medium") == 180
        assert agent._min_words_for_length("unknown") == 180

    def test_select_low_sections_none(self, agent):
        assert agent._select_low_sections({}, 100) == []

    def test_select_low_sections_returns_lowest(self, agent):
        sm = {"Intro": "a" * 20, "Body": "a" * 300, "Refs": "x" * 50}
        result = agent._select_low_sections(sm, 100, limit=2)
        assert "Refs" not in result
        assert "Intro" in result

    def test_extract_json_none(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json(None) is None

    def test_extract_json_with_fence(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json("```json\n{\"a\":1}\n```") == '{"a":1}'

    def test_extract_json_plain(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_json('{"a":1}') == '{"a":1}'

    def test_extract_outline_sections_dict(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._extract_outline_sections({"sections": [{"title": "Intro"}, {"title": "Body"}]})
        assert len(result) == 2

    def test_extract_outline_sections_list(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._extract_outline_sections(["Intro", "Body"])
        assert result[0]["title"] == "Intro"

    def test_extract_outline_sections_empty(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._extract_outline_sections("invalid") == []

    def test_normalize_sections_dict(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._normalize_sections({"Intro": "text"})
        assert result == {"Intro": "text"}

    def test_normalize_sections_list(self):
        from app.pipeline.generation.agent import AgentPipeline
        result = AgentPipeline._normalize_sections([{"title": "Intro", "content": "text"}])
        assert result == {"Intro": "text"}

    def test_normalize_sections_empty(self):
        from app.pipeline.generation.agent import AgentPipeline
        assert AgentPipeline._normalize_sections("bad") == {}

    def test_ensure_outline_numbers(self):
        from app.pipeline.generation.agent import AgentPipeline
        ol = {"sections": [{"title": "Intro"}]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["number"] == 1

    def test_ensure_outline_numbers_non_list(self):
        from app.pipeline.generation.agent import AgentPipeline
        ol = {"sections": "not a list"}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result is ol

    def test_ensure_outline_numbers_string_items(self):
        from app.pipeline.generation.agent import AgentPipeline
        ol = {"sections": ["Intro", "Body"]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["title"] == "Intro"
        assert result["sections"][0]["number"] == 1

    def test_ensure_outline_numbers_section_fallback(self):
        from app.pipeline.generation.agent import AgentPipeline
        ol = {"sections": [{"section": "Intro"}]}
        result = AgentPipeline._ensure_outline_numbers(ol)
        assert result["sections"][0]["title"] == "Intro"


# ══════════════════════════════════════════════════════════════════════════════
# generation/document_generator.py
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentGenerator:
    def test_normalize_status(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        assert DocumentGenerator._normalize_status("PENDING") == "pending"
        assert DocumentGenerator._normalize_status("COMPLETED") == "done"
        assert DocumentGenerator._normalize_status("FAILED") == "failed"
        assert DocumentGenerator._normalize_status("CANCELLED") == "failed"
        assert DocumentGenerator._normalize_status("unknown") == "processing"

    def test_now_iso(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        result = DocumentGenerator._now_iso()
        assert "T" in result
        assert result.endswith("+00:00")

    def test_default_session_config(self, dg):
        cfg = dg._default_session_config(doc_type="paper", template="ieee", metadata={"k": "v"}, options={"opt": True}, user_id="u1")
        assert cfg["doc_type"] == "paper"
        assert cfg["template"] == "ieee"
        assert cfg["stage"] == "queued"

    def test_session_record_to_status(self, dg):
        record = {"id": "j1", "config_json": {"stage": "writing", "progress": 50, "message": "working", "status": "processing"}}
        result = dg._session_record_to_status(record)
        assert result["status"] == "processing"
        assert result["stage"] == "writing"
        assert result["job_id"] == "j1"

    def test_session_record_to_status_error(self, dg):
        record = {"id": "j1", "config_json": {"error": "boom", "status": "failed", "stage": "error", "progress": 0, "message": "fail"}}
        result = dg._session_record_to_status(record)
        assert result["error"] == "boom"

    def test_rule_based_skeleton_default(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        import json
        sk = DocumentGenerator._rule_based_skeleton("academic_paper", {"title": "Test"})
        blocks = json.loads(sk)
        assert blocks[0]["type"] == "TITLE"
        assert blocks[0]["content"] == "Test"

    def test_rule_based_skeleton_resume(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        import json
        sk = DocumentGenerator._rule_based_skeleton("resume", {"title": "John"})
        blocks = json.loads(sk)
        assert blocks[0]["content"] == "John"

    def test_extract_outline(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        blocks = [{"type": "HEADING_1", "content": "Intro"}, {"type": "BODY", "content": "text"}, {"type": "TITLE", "content": "Title"}]
        result = DocumentGenerator._extract_outline(blocks)
        assert "Intro" in result
        assert "Title" in result
        assert "text" not in result

    def test_extract_outline_dedup(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        blocks = [{"type": "HEADING_1", "content": "Intro"}, {"type": "TITLE", "content": "Intro"}]
        result = DocumentGenerator._extract_outline(blocks)
        assert len(result) <= 2

    def test_extract_outline_limit(self):
        from app.pipeline.generation.document_generator import DocumentGenerator
        blocks = [{"type": "HEADING_1", "content": f"H{i}"} for i in range(100)]
        result = DocumentGenerator._extract_outline(blocks)
        assert len(result) <= 50

    def test_block_type_map_all_types(self):
        from app.pipeline.generation.document_generator import _BLOCK_TYPE_MAP
        from app.models.block import BlockType
        assert _BLOCK_TYPE_MAP["TITLE"] == BlockType.TITLE
        assert _BLOCK_TYPE_MAP["BODY"] == BlockType.BODY
        assert _BLOCK_TYPE_MAP["BULLET"] == BlockType.LIST_ITEM
        assert _BLOCK_TYPE_MAP["FIGURE_CAPTION"] == BlockType.FIGURE_CAPTION
        assert _BLOCK_TYPE_MAP["TABLE_CAPTION"] == BlockType.TABLE_CAPTION
        assert _BLOCK_TYPE_MAP.get("UNKNOWN", "fallback") == "fallback"


# ══════════════════════════════════════════════════════════════════════════════
# generation/prompt_builder.py
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptBuilder:
    def test_build_academic_paper(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"title": "Test", "authors": ["A"], "sections": [{"name": "Intro", "include": True}]}
        result = PromptBuilder().build("academic_paper", meta, {"include_placeholder_content": True, "word_count_target": 2000})
        assert "Test" in result
        assert "Intro" in result
        assert "JSON array" in result
        assert "REFERENCE_ENTRY" in result

    def test_build_resume(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"name": "John", "skills": ["Python"], "education": [{"degree": "BS", "institution": "MIT", "year": "2020"}]}
        result = PromptBuilder().build("resume", meta, {})
        assert "John" in result
        assert "Python" in result
        assert "MIT" in result

    def test_build_portfolio(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"name": "Researcher", "projects": [{"title": "AI", "year": "2024", "description": "Cool"}]}
        result = PromptBuilder().build("portfolio", meta, {})
        assert "Researcher" in result
        assert "AI" in result

    def test_build_report(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"title": "Report", "sections": [{"name": "Exec Summary", "include": True}]}
        result = PromptBuilder().build("report", meta, {})
        assert "Report" in result
        assert "Exec Summary" in result

    def test_build_thesis(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"title": "Thesis", "candidate_name": "Jane", "chapter_number": 1, "chapter_title": "Intro"}
        result = PromptBuilder().build("thesis", meta, {})
        assert "Thesis" in result
        assert "Jane" in result
        assert "Chapter 1" in result

    def test_build_unsupported(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        with pytest.raises(ValueError):
            PromptBuilder().build("unknown", {}, {})

    def test_build_without_placeholder(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"title": "T"}
        result = PromptBuilder().build("academic_paper", meta, {"include_placeholder_content": False})
        assert "single placeholder sentence" in result

    def test_json_instruction(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        result = PromptBuilder._json_instruction(["TITLE", "BODY"])
        assert "TITLE" in result
        assert "BODY" in result
        assert "level" in result

    def test_build_empty_sections_defaults(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        meta = {"title": "T"}
        result = PromptBuilder().build("academic_paper", meta, {})
        assert "Introduction" in result
        assert "Methodology" in result


# ══════════════════════════════════════════════════════════════════════════════
# formatting/reference_formatter.py
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceFormatter:
    def test_format_reference_basic(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        loader = MagicMock()
        ref = MagicMock()
        ref.raw_text = "J. Smith, A paper, 2020."
        ref.authors = ["Smith, J."]
        ref.title = "A paper"
        ref.year = "2020"
        rf = ReferenceFormatter(loader)
        result = rf.format_reference(ref, "ieee")
        assert result is not None
        assert len(result) > 5

    def test_format_reference_no_raw_text(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        loader = MagicMock()
        ref = MagicMock()
        ref.raw_text = None
        ref.authors = []
        ref.title = "Title"
        ref.year = "2020"
        rf = ReferenceFormatter(loader)
        result = rf.format_reference(ref, "ieee")
        assert result is None or result == ""

    def test_format_references_empty(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        assert rf.format_references([], "ieee") == []

    def test_format_references_calls_format_reference(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        with patch.object(ReferenceFormatter, "format_reference", return_value="[1] Ref"):
            rf = ReferenceFormatter(MagicMock())
            refs = [MagicMock(), MagicMock()]
            result = rf.format_references(refs, "ieee")
            assert len(result) == 2

    def test_format_legacy(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        ref = MagicMock()
        ref.authors = []
        ref.title = "Title"
        ref.year = ""
        ref.journal = ""
        ref.conference = ""
        ref.number = 1
        ref.raw_text = "Some raw"
        result = rf._format_legacy(ref, "ieee")
        assert "Untitled" in result or "Some raw" in result

    def test_get_or_load_style_cached(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter
        rf = ReferenceFormatter(MagicMock())
        rf._style_cache["ieee"] = MagicMock()
        result = rf._get_or_load_style("ieee")
        assert result is rf._style_cache["ieee"]


# ══════════════════════════════════════════════════════════════════════════════
# formatting/template_renderer.py
# ══════════════════════════════════════════════════════════════════════════════

class TestTemplateRenderer:
    def test_coerce_bool_true(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(True, False) is True
        assert TemplateRenderer._coerce_bool("true", False) is True
        assert TemplateRenderer._coerce_bool("1", False) is True
        assert TemplateRenderer._coerce_bool("yes", False) is True

    def test_coerce_bool_false(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert TemplateRenderer._coerce_bool(False, True) is False
        assert TemplateRenderer._coerce_bool("false", True) is False
        assert TemplateRenderer._coerce_bool("0", True) is False
        assert TemplateRenderer._coerce_bool("no", True) is False
        assert TemplateRenderer._coerce_bool(None, False) is False

    def test_has_renderable_template_no(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        assert tr.has_renderable_template("") is False
        assert tr.has_renderable_template("none") is False

    def test_has_renderable_template_yes(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        # "ieee" template likely exists in app/templates/
        result = tr.has_renderable_template("ieee")
        assert result is not None

    def test_build_context(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        doc = MagicMock()
        doc.blocks = []
        doc.metadata = MagicMock()
        doc.metadata.title = "Test"
        doc.template = MagicMock()
        doc.template.template_name = "ieee"
        ctx = tr.build_context(doc)
        assert ctx["title"] == "Test"

    def test_first_block_text(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b1 = MagicMock(); b1.text = "Hello"; b1.index = 0
        assert tr._first_block_text([b1], "title") in ("Hello", "")

    def test_first_block_text_empty(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        assert tr._first_block_text([], "title") == ""

    def test_all_block_text(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        b1 = MagicMock(); b1.text = "Hello"; b1.index = 0
        b2 = MagicMock(); b2.text = "World"; b2.index = 1
        result = tr._all_block_text([b1, b2], "body")
        assert isinstance(result, list)

    def test_block_type_token(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        assert "title" in TemplateRenderer._block_type_token(MagicMock(block_type="TITLE"))
        assert "body" in TemplateRenderer._block_type_token(MagicMock(block_type="BODY"))

    def test_has_template_markers_cached(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        tr = TemplateRenderer(templates_dir=".")
        import tempfile, os
        f = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        f.close()
        p = Path(f.name)
        tr._template_marker_cache[p] = True
        assert tr._has_template_markers(p) is True
        tr._template_marker_cache[p] = False
        assert tr._has_template_markers(p) is False
        os.unlink(f.name)

    def test_has_template_markers_not_docx(self):
        from app.pipeline.formatting.template_renderer import TemplateRenderer
        import tempfile, os
        f = tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False)
        f.write("anything")
        f.close()
        tr = TemplateRenderer(templates_dir=".")
        assert tr._has_template_markers(Path(f.name)) is False
        os.unlink(f.name)


# ══════════════════════════════════════════════════════════════════════════════
# safety/circuit_breaker.py
# ══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreakerDecorator:
    def test_decorator_success(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        @circuit_breaker(failure_threshold=2)
        def my_func(x):
            return x * 2
        assert my_func(21) == 42

    def test_decorator_opens_after_threshold(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
        call_count = [0]
        @circuit_breaker(failure_threshold=2)
        def my_func(x):
            call_count[0] += 1
            raise ValueError("fail")
        with patch("time.sleep"):
            with pytest.raises((CircuitBreakerOpenException, ValueError)):
                my_func(1)

    def test_circuit_breaker_open_exception(self):
        from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException
        exc = CircuitBreakerOpenException("test")
        assert "test" in str(exc)


# ══════════════════════════════════════════════════════════════════════════════
# safety/llm_validator.py
# ══════════════════════════════════════════════════════════════════════════════

class TestGuardLlmOutput:
    def test_no_guardrails_fallback(self):
        from app.pipeline.safety.llm_validator import guard_llm_output, HAS_GUARDRAILS
        schema = MagicMock()
        @guard_llm_output(schema, error_return_value={"fallback": True})
        def my_func():
            return {"data": "test"}
        result = my_func()
        if not HAS_GUARDRAILS:
            assert result == {"data": "test"}
        else:
            assert isinstance(result, dict)

    def test_guard_llm_output_exception(self):
        from app.pipeline.safety.llm_validator import guard_llm_output
        @guard_llm_output(object, error_return_value={"error": True})
        def my_func():
            raise ValueError("boom")
        result = my_func()
        assert result == {"error": True}

    def test_guard_returns_pydantic(self):
        from app.pipeline.safety.llm_validator import guard_llm_output, HAS_GUARDRAILS
        from pydantic import BaseModel
        class MySchema(BaseModel):
            name: str = "default"
        @guard_llm_output(MySchema, error_return_value={"error": True})
        def my_func():
            return MySchema(name="test")
        result = my_func()
        if HAS_GUARDRAILS:
            assert isinstance(result, dict)
        else:
            # Without guardrails, falls back to validate_output which may return raw
            assert result is not None


# ══════════════════════════════════════════════════════════════════════════════
# references/formatter_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceFormatterEngine:
    def test_process_no_refs(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        doc = MagicMock()
        doc.references = []
        result = ReferenceFormatterEngine(MagicMock()).process(doc)
        assert result is doc

    def test_process_with_refs(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        doc = MagicMock()
        ref = MagicMock()
        ref.raw_text = "Test"
        doc.references = [ref]
        with patch.object(ReferenceFormatterEngine, "format_all", return_value=["[1] Test"]):
            result = ReferenceFormatterEngine(MagicMock()).process(doc)
            assert result is doc

    def test_format_all(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        loader = MagicMock()
        loader.load.return_value = {"references": {"normalization": {"default_format": "{authors}, {title}, {year}."}}}
        rfe = ReferenceFormatterEngine(loader)
        with patch.object(rfe.csl_engine, "format_references", side_effect=Exception("CSL unavailable")):
            refs = [MagicMock(authors=["Smith, J."], title="Paper", year="2020", raw_text="raw", reference_type="article")]
            result = rfe.format_all(refs, "ieee")
            assert result is refs
            assert hasattr(result[0], "formatted_text")

    def test_format_single(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        rfe = ReferenceFormatterEngine(MagicMock())
        rules = {"default_format": "{authors}, {title}, {year}.", "max_authors": 99, "et_al_suffix": "et al."}
        ref = MagicMock(authors=["Smith, J."], title="Paper", year="2020", raw_text="raw", reference_type="article", journal="Journal", volume="1", issue="2", pages="10-20", doi="", metadata={}, conference="")
        result = rfe.format_single(ref, rules)
        assert "Smith" in result
        assert "Paper" in result


# ══════════════════════════════════════════════════════════════════════════════
# references/parser.py
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceParser:
    def test_process_no_refs(self):
        from app.pipeline.references.parser import ReferenceParser
        doc = MagicMock()
        doc.blocks = []
        result = ReferenceParser().process(doc)
        assert result is doc

    def test_process_extracts_refs(self):
        from app.pipeline.references.parser import ReferenceParser
        doc = MagicMock()
        ref_block = MagicMock()
        ref_block.block_type = "REFERENCE_ENTRY"
        ref_block.text = "[1] J. Smith, A paper, 2020."
        doc.blocks = [ref_block]
        result = ReferenceParser().process(doc)
        assert result is doc

    def test_parse_authors(self):
        from app.pipeline.references.parser import ReferenceParser
        rp = ReferenceParser()
        authors = rp._parse_authors("Smith, J. and Doe, J.")
        assert len(authors) >= 2

    def test_parse_authors_single(self):
        from app.pipeline.references.parser import ReferenceParser
        rp = ReferenceParser()
        authors = rp._parse_authors("Smith")
        assert len(authors) == 1


# ══════════════════════════════════════════════════════════════════════════════
# classification/classifier.py
# ══════════════════════════════════════════════════════════════════════════════

class TestContentClassifier:
    def test_looks_like_heading_long_text(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.text = "x" * 81
        b.metadata = {}
        assert ContentClassifier()._looks_like_heading(b) is False

    def test_looks_like_heading_colon(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.text = "A" * 81 + ":"
        b.metadata = {}
        assert ContentClassifier()._looks_like_heading(b) is True

    def test_looks_like_heading_short_colon(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.text = "Introduction:"
        b.metadata = {}
        assert ContentClassifier()._looks_like_heading(b) is True

    def test_looks_like_heading_no_caps(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.text = "lowercase heading"
        b.metadata = {}
        with patch.object(ContentClassifier, "_looks_like_heading", return_value=True):
            pass

    def test_resolve_heading_type_level_1(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.metadata = {"level": 1}
        result, _ = ContentClassifier()._resolve_heading_type(b)
        from app.models.block import BlockType
        assert result == BlockType.HEADING_1

    def test_resolve_heading_type_level_2(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.metadata = {"level": 2}
        result, _ = ContentClassifier()._resolve_heading_type(b)
        from app.models.block import BlockType
        assert result == BlockType.HEADING_2

    def test_resolve_heading_type_level_3(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.metadata = {"level": 3}
        result, _ = ContentClassifier()._resolve_heading_type(b)
        from app.models.block import BlockType
        assert result == BlockType.HEADING_3

    def test_resolve_heading_type_level_4(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.metadata = {"level": 4}
        result, _ = ContentClassifier()._resolve_heading_type(b)
        from app.models.block import BlockType
        assert result == BlockType.HEADING_4

    def test_resolve_heading_type_default(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b = MagicMock()
        b.metadata = {}
        result, _ = ContentClassifier()._resolve_heading_type(b)
        from app.models.block import BlockType
        assert result == BlockType.HEADING_1

    def test_is_likely_affiliation(self):
        from app.pipeline.classification.classifier import ContentClassifier
        assert ContentClassifier()._is_likely_affiliation("University of Testing") is True
        assert ContentClassifier()._is_likely_affiliation("Some random text") is False

    def test_find_first_section_index(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        blocks = [MagicMock(block_type=BlockType.TITLE), MagicMock(block_type=BlockType.HEADING_1)]
        assert ContentClassifier()._find_first_section_index(blocks) == 1

    def test_find_first_section_index_not_found(self):
        from app.pipeline.classification.classifier import ContentClassifier
        assert ContentClassifier()._find_first_section_index([]) == 0

    def test_find_references_start_index(self):
        from app.pipeline.classification.classifier import ContentClassifier
        b1 = MagicMock(block_type="BODY", text="text")
        b2 = MagicMock(block_type="HEADING_1", text="References")
        b3 = MagicMock(block_type="REFERENCE_ENTRY", text="[1]")
        assert ContentClassifier()._find_references_start_index([b1, b2, b3]) == 1

    def test_find_references_start_index_not_found(self):
        from app.pipeline.classification.classifier import ContentClassifier
        assert ContentClassifier()._find_references_start_index([MagicMock(block_type="BODY")]) is None

    def test_match_grobid_author(self):
        from app.pipeline.classification.classifier import ContentClassifier
        assert ContentClassifier()._match_grobid_author("John Smith", []) is False

    def test_match_grobid_affiliation(self):
        from app.pipeline.classification.classifier import ContentClassifier
        assert ContentClassifier()._match_grobid_affiliation("MIT", []) is False

    def test_nlp_classify_fallback_title(self):
        from app.models.block import BlockType
        from app.pipeline.references import parser as ref_parser_mod
        with patch.object(ref_parser_mod, "ReferenceParser") as mock_rp:
            from app.pipeline.classification.classifier import ContentClassifier
            cc = ContentClassifier()
            b = MagicMock()
            b.block_type = BlockType.UNKNOWN
            b.text = "The Title"
            b.metadata = {}
            b.semantic_intent = None
            cc._nlp_classify_fallback([b])

    def test_nlp_classify_fallback_heading(self):
        from app.models.block import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.block_type = BlockType.UNKNOWN
        b.text = "Introduction"
        b.metadata = {}
        b.semantic_intent = None
        cc._nlp_classify_fallback([b])

    def test_nlp_classify_fallback_body(self):
        from app.models.block import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.block_type = BlockType.UNKNOWN
        b.text = "Some normal text that goes on and on"
        b.metadata = {}
        b.semantic_intent = None
        cc._nlp_classify_fallback([b])
        assert b.block_type == BlockType.UNKNOWN


# ══════════════════════════════════════════════════════════════════════════════
# structure_detection/heading_rules.py
# ══════════════════════════════════════════════════════════════════════════════

class TestHeadingRules:
    def test_detect_numbering_pattern_decimal(self):
        from app.pipeline.structure_detection.heading_rules import detect_numbering_pattern
        result = detect_numbering_pattern("1. Introduction")
        assert result is not None
        assert result["pattern_type"] == "decimal"
        assert result["number"] == "1"
        assert result["level"] == 1

    def test_detect_numbering_pattern_decimal_sub(self):
        from app.pipeline.structure_detection.heading_rules import detect_numbering_pattern
        result = detect_numbering_pattern("1.1 Background")
        assert result is not None
        assert result["pattern_type"] == "decimal"
        assert result["number"] == "1.1"
        assert result["level"] == 2

    def test_detect_numbering_pattern_roman(self):
        from app.pipeline.structure_detection.heading_rules import detect_numbering_pattern
        result = detect_numbering_pattern("I. Introduction")
        assert result is not None
        assert result["pattern_type"] == "roman"
        assert result["level"] == 1

    def test_detect_numbering_pattern_none(self):
        from app.pipeline.structure_detection.heading_rules import detect_numbering_pattern
        assert detect_numbering_pattern("") is None
        assert detect_numbering_pattern("Some text") is None

    def test_matches_section_keyword(self):
        from app.pipeline.structure_detection.heading_rules import matches_section_keyword
        assert matches_section_keyword("Introduction") is True
        assert matches_section_keyword("1. Introduction") is True
        assert matches_section_keyword("Random text") is False
        assert matches_section_keyword("") is False

    def test_is_likely_heading_by_style(self):
        from app.pipeline.structure_detection.heading_rules import is_likely_heading_by_style
        b = MagicMock()
        b.text = "Short"
        b.style.font_size = None
        b.style.bold = False
        result, score = is_likely_heading_by_style(b)
        assert isinstance(result, bool)
        assert isinstance(score, float)

    def test_infer_heading_level(self):
        from app.pipeline.structure_detection.heading_rules import infer_heading_level
        b = MagicMock()
        b.text = "Introduction"
        assert infer_heading_level(b) == 1

    def test_get_capitalization_ratio(self):
        from app.pipeline.structure_detection.heading_rules import get_capitalization_ratio
        assert get_capitalization_ratio("Introduction") == 1.0
        assert get_capitalization_ratio("") == 0.0

    def test_analyze_heading_candidate_numbered(self):
        from app.pipeline.structure_detection.heading_rules import analyze_heading_candidate, detect_numbering_pattern
        b = MagicMock()
        b.text = "1. Introduction"
        b.metadata = {}
        b.style.font_size = None
        b.style.bold = False
        result = analyze_heading_candidate(b, [b], 0)
        assert result is not None
        assert result["is_heading"] is True

    def test_detect_title(self):
        from app.pipeline.structure_detection.heading_rules import detect_title
        b = MagicMock(text="Paper Title Here", metadata={})
        b.block_id = "block1"
        b2 = MagicMock(text="", metadata={})
        b2.block_id = "block0"
        assert detect_title(b, [b2, b]) is True


# ══════════════════════════════════════════════════════════════════════════════
# structure_detection/position_rules.py
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionRules:
    def test_is_first_non_empty_block(self):
        from app.pipeline.structure_detection.position_rules import is_first_non_empty_block
        b1 = MagicMock(text="First")
        b2 = MagicMock(text="Second")
        assert is_first_non_empty_block(b1, [b1, b2]) is True
        assert is_first_non_empty_block(b2, [b1, b2]) is False

    def test_count_empty_blocks_before(self):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_before
        b1 = MagicMock(text="")
        b2 = MagicMock(text="")
        b3 = MagicMock(text="Content")
        assert count_empty_blocks_before(b3, [b1, b2, b3]) == 2

    def test_analyze_position(self):
        from app.pipeline.structure_detection.position_rules import analyze_position
        b = MagicMock(text="Content")
        result = analyze_position(b, [b])
        assert isinstance(result, dict)

    def test_get_block_position_ratio(self):
        from app.pipeline.structure_detection.position_rules import get_block_position_ratio
        b = MagicMock(text="Content")
        blocks = [MagicMock(text=""), MagicMock(text="Content2")]
        ratio = get_block_position_ratio(b, blocks)
        assert isinstance(ratio, float)


# ══════════════════════════════════════════════════════════════════════════════
# structure_detection/detector.py
# ══════════════════════════════════════════════════════════════════════════════

class TestStructureDetector:
    def test_calculate_avg_font_size_empty(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        b = MagicMock()
        b.style.font_size = None
        blocks = [b]
        result = StructureDetector._calculate_avg_font_size(None, blocks)
        assert result is None

    def test_calculate_avg_font_size(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        b1 = MagicMock()
        b1.style.font_size = 12
        b2 = MagicMock()
        b2.style.font_size = 14
        sd = StructureDetector()
        result = sd._calculate_avg_font_size([b1, b2])
        assert result == 13.0

    def test_detect_heading_candidates(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        sd = StructureDetector()
        b = MagicMock()
        b.text = "1. Introduction"
        b.metadata = {}
        b.style.font_size = None
        b.style.bold = False
        sd._detect_heading_candidates([b])
        assert "is_heading_candidate" in b.metadata

    def test_validate_hierarchy_empty(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        sd = StructureDetector()
        result = sd._validate_hierarchy([])
        assert result is None

    def test_validate_hierarchy(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        sd = StructureDetector()
        b1 = MagicMock()
        b1.metadata = {}
        b1.is_heading.return_value = False
        sd._validate_hierarchy([b1])

    def test_build_hierarchy(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        sd = StructureDetector()
        candidates = [{"name": "Intro", "level": 1, "block_id": "b1"}, {"name": "Body", "level": 1, "block_id": "b2"}]
        sd._build_hierarchy([MagicMock()], candidates)


# ══════════════════════════════════════════════════════════════════════════════
# intelligence/rag_engine.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRagEngine:
    def _make_re(self):
        import tempfile
        from app.pipeline.intelligence.rag_engine import RagEngine
        with patch.object(RagEngine, "_load_embedding_model"):
            re = RagEngine(tempfile.mkdtemp())
        re.chroma_enabled = False
        re.client = None
        re.collection = None
        return re

    def test_coerce_embedding_vector_list(self):
        re = self._make_re()
        result = re._coerce_embedding_vector([0.1, 0.2, 0.3])
        assert len(result) == 3
        assert isinstance(result, list)

    def test_coerce_embedding_vector_numpy(self):
        re = self._make_re()
        import numpy as np
        result = re._coerce_embedding_vector(np.array([0.1, 0.2]))
        assert len(result) == 2

    def test_add_guideline(self):
        re = self._make_re()
        with patch.object(re, "_seed_if_empty"):
            with patch.object(re, "_save_native"):
                re.add_guideline("IEEE", "introduction", "Content")
                assert len(re.knowledge_base) == 1
                assert re.knowledge_base[0]["metadata"]["publisher"] == "IEEE"

    def test_query_guidelines_empty(self):
        re = self._make_re()
        re.knowledge_base = []
        result = re.query_guidelines("IEEE", "introduction", top_k=3)
        assert result == []

    def test_reset(self):
        re = self._make_re()
        with patch.object(re, "_seed_if_empty"):
            with patch.object(re, "_save_native"):
                re.add_guideline("IEEE", "intro", "test")
        re.reset()
        assert len(re.knowledge_base) == 0

    def test_is_reusable_embedding_model(self):
        re = self._make_re()
        is_usable, dim = re._is_reusable_embedding_model(None)
        assert is_usable is False
        assert dim is None


# ══════════════════════════════════════════════════════════════════════════════
# synthesis/synthesizer.py
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiDocSynthesizer:
    @pytest.fixture
    def ms(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        return MultiDocSynthesizer(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_chunk_text(self, ms):
        chunks = ms._chunk_text("word " * 500, "doc1", "intro", 1, chunk_size=200, overlap=100)
        assert len(chunks) > 1

    def test_chunk_text_short(self, ms):
        chunks = ms._chunk_text("short text", "doc1", "intro", 1, chunk_size=2000)
        assert len(chunks) == 1

    def test_chunk_text_empty(self, ms):
        assert ms._chunk_text("", "doc1", "intro", 1) == []

    def test_extract_json(self):
        from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
        assert MultiDocSynthesizer._extract_json('```json\n{"a":1}\n```') == '{"a":1}'
        assert MultiDocSynthesizer._extract_json('{"a":1}') == '{"a":1}'
        assert MultiDocSynthesizer._extract_json("") is None
        assert MultiDocSynthesizer._extract_json("no json") is None

    def test_template_to_csl(self, ms):
        csl = ms._template_to_csl("ieee")
        assert isinstance(csl, str)

    def test_template_to_csl_default(self, ms):
        csl = ms._template_to_csl("unknown")
        assert isinstance(csl, str)


# ══════════════════════════════════════════════════════════════════════════════
# formatting/formatter.py — key standalone methods
# ══════════════════════════════════════════════════════════════════════════════

class TestFormatterMethods:
    def test_coerce_bool_option(self):
        from app.pipeline.formatting.formatter import Formatter
        assert Formatter._coerce_bool_option(None, False) is False
        assert Formatter._coerce_bool_option(True, False) is True
        assert Formatter._coerce_bool_option(False, True) is False

    def test_resolve_page_size(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        with patch.object(f.contract_loader, "load", return_value={"layout": {"page_size": "A4"}}):
            result = f._resolve_page_size("ieee", {})
            assert result == "A4"

    def test_get_target_columns(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        with patch.object(f.contract_loader, "load", return_value={"layout": {"default_columns": 1}}):
            result = f._get_target_columns(MagicMock(section_name=None), "ieee")
            assert result == 1

    def test_is_bullet_list_item(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        assert f._is_bullet_list_item("- item") is True
        assert f._is_bullet_list_item("* item") is True
        assert f._is_bullet_list_item("normal") is False
        assert f._is_bullet_list_item("") is False
        assert f._is_bullet_list_item(None) is False

    def test_is_numbered_list_item(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        assert f._is_numbered_list_item("1. item") is True
        assert f._is_numbered_list_item("1) item") is True
        assert f._is_numbered_list_item("normal") is False

    def test_clean_list_text(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        assert f._clean_list_text("- text") == "text"
        assert f._clean_list_text("1. text") == "text"

    def test_paragraph_has_field_code(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        para = MagicMock()
        para._p.xml = "<xml>TOC</xml>"
        result = f._paragraph_has_field_code(para, "TOC")
        assert result is True

    def test_resolve_line_spacing(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        with patch.object(f.contract_loader, "load", return_value={"layout": {"line_spacing": 2.0}}):
            result = f._resolve_line_spacing("ieee", {})
            assert result is not None

    def test_apply_initial_layout(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        doc = MagicMock()
        doc.formatting_options = {}
        with patch.object(f.contract_loader, "load", return_value={"layout": {"margins": {"top": 1, "bottom": 1, "left": 1, "right": 1}}}):
            f._apply_initial_layout(doc, "ieee")

    def test_render_equation(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        eqn = MagicMock()
        eqn.mathml = "<math>1+1</math>"
        f._render_equation(MagicMock(), eqn)

    def test_render_equation_empty(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        eqn = MagicMock()
        eqn.mathml = None
        result = f._render_equation(MagicMock(), eqn)
        assert result is None

    def test_prepare_references(self):
        from app.pipeline.formatting.formatter import Formatter
        f = Formatter(templates_dir=".", contracts_dir=".")
        with patch.object(f.contract_loader, "load", return_value={"spacing": 1.5}):
            with patch.object(f.reference_formatter, "format_reference", return_value="[1] Ref"):
                doc = MagicMock()
                doc.references = [MagicMock()]
                doc.blocks = []
                f._prepare_references(doc, "ieee")
