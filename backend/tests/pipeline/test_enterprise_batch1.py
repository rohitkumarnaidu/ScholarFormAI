# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, ANY, AsyncMock
import pytest


# ─── StyleMapper ───────────────────────────────────────────────────────────────

class TestStyleMapper:
    def test_get_style_name_exact(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {"BLOCK_HEADING_1": "Heading 1"}}
        sm = StyleMapper(loader)
        b = MagicMock()
        b.block_type = "HEADING_1"
        assert sm.get_style_name(b, "ieee") == "Heading 1"

    def test_get_style_name_fallback(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {}}
        sm = StyleMapper(loader)
        b = MagicMock()
        b.block_type = "BODY"
        assert sm.get_style_name(b, "ieee") == "Normal"

    def test_get_style_name_prefixed(self):
        from app.pipeline.formatting.style_mapper import StyleMapper
        loader = MagicMock()
        loader.load.return_value = {"styles": {"BLOCK_BODY": "Body Text"}}
        sm = StyleMapper(loader)
        b = MagicMock()
        b.block_type = "BLOCK_BODY"
        assert sm.get_style_name(b, "ieee") == "Body Text"


# ─── SectionOrderValidator ────────────────────────────────────────────────────

class TestSectionOrderValidator:
    def test_no_violations(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": ["abstract", "introduction"], "required": ["abstract"]}}
        b = MagicMock()
        b.is_heading.return_value = True
        b.section_name = "Abstract"
        doc = MagicMock()
        doc.blocks = [b]
        sv = SectionOrderValidator(loader)
        assert sv.validate_order(doc, "ieee") == []

    def test_missing_required(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": [], "required": ["abstract"]}}
        b = MagicMock()
        b.is_heading.return_value = True
        b.section_name = "Introduction"
        doc = MagicMock()
        doc.blocks = [b]
        sv = SectionOrderValidator(loader)
        v = sv.validate_order(doc, "ieee")
        assert any("abstract" in vi.lower() for vi in v)

    def test_out_of_order(self):
        from app.pipeline.formatting.section_ordering import SectionOrderValidator
        loader = MagicMock()
        loader.load.return_value = {"sections": {"order": ["abstract", "introduction", "conclusion"], "required": []}}
        b1 = MagicMock(); b1.is_heading.return_value = True; b1.section_name = "Conclusion"
        b2 = MagicMock(); b2.is_heading.return_value = True; b2.section_name = "Introduction"
        doc = MagicMock()
        doc.blocks = [b1, b2]
        sv = SectionOrderValidator(loader)
        v = sv.validate_order(doc, "ieee")
        assert any("out of order" in vi.lower() for vi in v)


# ─── NumberingEngine ───────────────────────────────────────────────────────────

class TestNumberingEngine:
    def test_heading_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        b = MagicMock()
        b.is_heading.return_value = True
        b.level = 1
        b.text = "Introduction"
        b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        result = ne.apply_numbering(doc, "ieee")
        assert b.metadata["number_string"] == "1"
        assert b.text.startswith("1 ")

    def test_heading_idempotent(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        b = MagicMock()
        b.is_heading.return_value = True
        b.level = 1
        b.text = "1 Introduction"
        b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        doc.figures = []
        doc.tables = []
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert b.text == "1 Introduction"

    def test_figure_table_numbering(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {}}
        fig = MagicMock()
        tbl = MagicMock()
        doc = MagicMock()
        doc.blocks = []
        doc.figures = [fig]
        doc.tables = [tbl]
        doc.equations = []
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert fig.number == 1
        assert tbl.number == 1

    def test_equation_brackets(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}, "equations": {"scope": "global", "brackets": "[]"}}
        eq = MagicMock()
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        doc.equations = [eq]
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert eq.number == "[1]"

    def test_no_equation_rules(self):
        from app.pipeline.formatting.numbering import NumberingEngine
        loader = MagicMock()
        loader.load.return_value = {"numbering": {}}
        eq = MagicMock()
        sentinel = object()
        eq.number = sentinel
        doc = MagicMock()
        doc.blocks = []
        doc.figures = []
        doc.tables = []
        doc.equations = [eq]
        ne = NumberingEngine(loader)
        ne.apply_numbering(doc, "ieee")
        assert eq.number is sentinel


# ─── CrossReferenceEngine ──────────────────────────────────────────────────────

class TestCrossReferenceEngine:
    def test_no_violations(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        b = MagicMock()
        b.block_type = "body"
        b.block_id = "b1"
        b.text = "See Figure 1 and Table 1"
        b.section_name = None
        doc = MagicMock()
        doc.figures = [MagicMock()]
        doc.tables = [MagicMock()]
        doc.equations = []
        doc.blocks = [b]
        assert CrossReferenceEngine().validate_integrity(doc) == []

    def test_dangling_figure(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        b = MagicMock()
        b.block_type = "body"
        b.block_id = "b1"
        b.text = "See Figure 5"
        b.section_name = None
        doc = MagicMock()
        doc.figures = []
        doc.tables = []
        doc.equations = []
        doc.blocks = [b]
        v = CrossReferenceEngine().validate_integrity(doc)
        assert any("Figure 5" in vi for vi in v)

    def test_skips_non_body_blocks(self):
        from app.pipeline.integrity.cross_ref import CrossReferenceEngine
        b = MagicMock()
        b.block_type = "heading_1"
        b.text = "Figure 1"
        doc = MagicMock()
        doc.figures = []
        doc.tables = []
        doc.equations = []
        doc.blocks = [b]
        assert CrossReferenceEngine().validate_integrity(doc) == []


# ─── ContractLoader ────────────────────────────────────────────────────────────

class TestContractLoader:
    def test_load_cached(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        cl._cache["ieee"] = {"styles": {}}
        with patch("os.path.exists", return_value=True), patch("builtins.open"), patch("yaml.safe_load"):
            result = cl.load("IEEE")
            assert result == {"styles": {}}

    def test_load_not_found_fallback(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        with (
            patch("os.path.exists", side_effect=[False, True]),
            patch("builtins.open"),
            patch("yaml.safe_load", return_value={}),
        ):
            result = cl.load("unknown")
            assert "publisher" in result

    def test_load_fallback_not_found(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                cl.load("unknown")

    def test_load_yaml_error(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        with patch("os.path.exists", return_value=True), patch("builtins.open"), patch("yaml.safe_load", side_effect=Exception("yaml err")):
            with pytest.raises(RuntimeError):
                cl.load("ieee")

    def test_normalize_contract_none(self):
        from app.pipeline.contracts.loader import ContractLoader
        assert ContractLoader()._normalize_contract(None, "/tmp/c.yaml") == {}

    def test_normalize_contract_spacing(self):
        from app.pipeline.contracts.loader import ContractLoader
        c = {"layout": {"spacing": 1.5}}
        result = ContractLoader()._normalize_contract(c, "/tmp/ieee/c.yaml")
        assert result.get("spacing") == 1.5

    def test_normalize_contract_publisher(self):
        from app.pipeline.contracts.loader import ContractLoader
        c = {"spacing": 2}
        result = ContractLoader()._normalize_contract(c, "/tmp/ieee/c.yaml")
        assert result.get("publisher") == "ieee"

    def test_get_canonical_name(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        cl._cache["ieee"] = {"sections": {"canonical_names": {"intro": "introduction"}}}
        assert cl.get_canonical_name("ieee", "Intro") == "introduction"

    def test_is_required(self):
        from app.pipeline.contracts.loader import ContractLoader
        cl = ContractLoader()
        cl._cache["ieee"] = {"sections": {"required": ["Abstract", "Conclusion"]}}
        assert cl.is_required("ieee", "Abstract") is True
        assert cl.is_required("ieee", "Introduction") is False

    def test_load_contract_convenience(self):
        from app.pipeline.contracts.loader import load_contract
        from app.pipeline.contracts.loader import _default_pipeline_loader
        _default_pipeline_loader._cache["test"] = {"publisher": "test"}
        assert load_contract("test") == {"publisher": "test"}


# ─── retry_with_backoff / execute_with_retry ──────────────────────────────────

class TestRetryGuard:
    def _sync_fn(self, val):
        return val

    async def _async_fn(self, val):
        return val

    def test_sync_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        fn = MagicMock(return_value=42)
        decorated = retry_with_backoff(max_retries=2)(fn)
        assert decorated() == 42
        assert fn.call_count == 1

    def test_sync_retry_then_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        results = [ValueError("first"), 42]
        def fn():
            r = results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        decorated = retry_with_backoff(max_retries=2, backoff_factor=0.01)(fn)
        with patch("time.sleep"):
            assert decorated() == 42

    def test_sync_retry_exhausted(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        def fn():
            raise ValueError("always")
        decorated = retry_with_backoff(max_retries=1, backoff_factor=0.01)(fn)
        with patch("time.sleep"):
            with pytest.raises(ValueError):
                decorated()

    def test_async_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        fn = AsyncMock(return_value=42)
        decorated = retry_with_backoff(max_retries=2)(fn)
        import asyncio
        with patch("asyncio.sleep"):
            result = asyncio.run(decorated())
            assert result == 42
            assert fn.call_count == 1

    def test_async_retry_then_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        results = [ValueError("first"), 42]
        async def fn():
            r = results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        decorated = retry_with_backoff(max_retries=2, backoff_factor=0.01)(fn)
        import asyncio
        with patch("asyncio.sleep"):
            result = asyncio.run(decorated())
            assert result == 42

    def test_async_retry_exhausted(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        async def fn():
            raise ValueError("always")
        decorated = retry_with_backoff(max_retries=1, backoff_factor=0.01)(fn)
        import asyncio
        with patch("asyncio.sleep"):
            with pytest.raises(ValueError):
                asyncio.run(decorated())

    def test_execute_with_retry_success(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        def fn():
            return 99
        assert execute_with_retry(fn, max_retries=2) == 99

    def test_retry_guard_alias(self):
        from app.pipeline.safety.retry_guard import retry_guard
        assert callable(retry_guard)

    def test_base_delay_alias(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        def fn():
            return 1
        decorated = retry_with_backoff(max_retries=1, base_delay=0.5)(fn)
        assert decorated() == 1


# ─── safe_execution / safe_function / safe_async_function ─────────────────────

class TestSafeExecution:
    def test_safe_execution_success(self):
        from app.pipeline.safety.safe_execution import safe_execution
        with safe_execution("test"):
            result = 42
        assert result == 42

    def test_safe_execution_catches(self):
        from app.pipeline.safety.safe_execution import safe_execution
        marker = False
        with safe_execution("test"):
            raise ValueError("boom")
            marker = True
        assert marker is False

    def test_safe_function_success(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value=None)
        def do_thing():
            return "ok"
        assert do_thing() == "ok"

    def test_safe_function_fallback(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value="fallback")
        def do_thing():
            raise ValueError("boom")
        assert do_thing() == "fallback"

    def test_safe_async_function_success(self):
        from app.pipeline.safety.safe_execution import safe_async_function
        import asyncio
        @safe_async_function(fallback_value=None)
        async def do_thing():
            return "ok"
        result = asyncio.run(do_thing())
        assert result == "ok"

    def test_safe_async_function_fallback(self):
        from app.pipeline.safety.safe_execution import safe_async_function
        import asyncio
        @safe_async_function(fallback_value="fallback")
        async def do_thing():
            raise ValueError("boom")
        result = asyncio.run(do_thing())
        assert result == "fallback"


# ─── validate_output ──────────────────────────────────────────────────────────

class TestValidateOutput:
    def test_dict_schema_missing_keys(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema={"title": str, "body": str}, error_return_value={"fallback": True})
        def fn():
            return {"title": "hello"}
        result = fn()
        assert result == {"fallback": True}

    def test_dict_schema_all_keys(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema={"title": str})
        def fn():
            return {"title": "hello"}
        assert fn() == {"title": "hello"}

    def test_exception(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema={"t": str}, error_return_value={"fallback": True})
        def fn():
            raise ValueError("crash")
        assert fn() == {"fallback": True}


# ─── Reference Normalizer ──────────────────────────────────────────────────────

class TestReferenceNormalizer:
    def test_clean_author_name(self):
        from app.pipeline.references.normalizer import clean_author_name
        assert clean_author_name("  Smith, J.  ") == "Smith, J."

    def test_clean_author_name_quotes(self):
        from app.pipeline.references.normalizer import clean_author_name
        assert clean_author_name('"Smith, J."') == "Smith, J."

    def test_clean_title(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title('"A Great Paper"') == "A Great Paper"

    def test_clean_title_curly_quotes(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title("\u201cA Study\u201d") == "A Study"

    def test_clean_title_strips_trailing(self):
        from app.pipeline.references.normalizer import clean_title
        assert clean_title("Title,") == "Title"

    def test_normalize_page_range_none(self):
        from app.pipeline.references.normalizer import normalize_page_range
        assert normalize_page_range("") == ""

    def test_normalize_page_range(self):
        from app.pipeline.references.normalizer import normalize_page_range
        assert normalize_page_range("pp. 123-145") == "123-145"


# ─── Section Prompts ───────────────────────────────────────────────────────────

class TestSectionPrompts:
    def test_get_section_prompt_known(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        result = get_section_prompt("Abstract", {})
        assert "abstract" in result.lower()

    def test_get_section_prompt_unknown(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        result = get_section_prompt("UnknownSection", {})
        assert "formal tone" in result.lower()

    def test_get_section_prompt_with_previous(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        result = get_section_prompt("Introduction", {"previous_sections": {"Abstract": "short text"}})
        assert "Previous sections" in result

    def test_truncate(self):
        from app.pipeline.generation.section_prompts import _truncate
        assert _truncate("hello world", limit=5) == "hello..."
        assert _truncate("short", limit=100) == "short"
        assert _truncate("", limit=10) == ""


# ─── EquationStandardizer ──────────────────────────────────────────────────────

class TestEquationStandardizer:
    def test_init_xslt_not_found(self):
        with patch("os.path.exists", return_value=False):
            from app.pipeline.equations.standardizer import EquationStandardizer
            es = EquationStandardizer(xsl_path="/nonexistent.xsl")
            assert es._xslt is None

    def test_process_no_equations(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        doc = MagicMock()
        doc.equations = []
        result = EquationStandardizer().process(doc)
        assert result is doc

    def test_process_xslt_none(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer()
        es._xslt = None
        eq = MagicMock()
        eq.omml = "<math>...</math>"
        sentinel = object()
        eq.mathml = sentinel
        doc = MagicMock()
        doc.equations = [eq]
        es.process(doc)
        assert eq.mathml is sentinel

    def test_convert_omml_no_xslt(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer()
        es._xslt = None
        assert es._convert_omml_to_mathml("<omml>test</omml>") == ""

    def test_convert_omml_xml_error(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer()
        es._xslt = MagicMock()
        with patch("lxml.etree.fromstring", side_effect=Exception("parse error")):
            assert es._convert_omml_to_mathml("<bad>") == ""

    def test_process_exception_logged(self):
        from app.pipeline.equations.standardizer import EquationStandardizer
        es = EquationStandardizer()
        doc = MagicMock()
        doc.equations = MagicMock()
        doc.equations.__iter__.side_effect = RuntimeError("boom")
        result = es.process(doc)
        assert result is doc
        doc.add_processing_stage.assert_called_once_with(
            stage_name="equation_standardization",
            status="error",
            message=ANY
        )

    def test_get_equation_standardizer(self):
        from app.pipeline.equations.standardizer import get_equation_standardizer
        from app.pipeline.equations.standardizer import _standardizer
        _standardizer = None
        es = get_equation_standardizer()
        assert es is not None


# ─── ContentParser ─────────────────────────────────────────────────────────────

class TestContentParser:
    def test_parse_json_fence(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser().parse('```json\n[{"type": "BODY", "content": "Hello"}]\n```', "test")
        assert len(result) == 1
        assert result[0]["content"] == "Hello"

    def test_parse_plain_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser().parse('[{"type": "HEADING_1", "content": "Intro", "level": 1}]', "test")
        assert result[0]["type"] == "HEADING_1"

    def test_parse_code_fence_no_lang(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser().parse("```\n[{\"type\": \"BODY\", \"content\": \"Hi\"}]\n```", "test")
        assert len(result) == 1

    def test_parse_no_json_raises(self):
        from app.pipeline.generation.content_parser import ContentParser
        with pytest.raises(ValueError):
            ContentParser().parse("not json", "test")

    def test_parse_invalid_json(self):
        from app.pipeline.generation.content_parser import ContentParser
        with pytest.raises(ValueError):
            ContentParser().parse("[invalid]", "test")

    def test_extract_json_fallback(self):
        from app.pipeline.generation.content_parser import ContentParser
        text = "some prefix [{\"a\": 1}]"
        assert ContentParser._extract_json(text) == '[{"a": 1}]'

    def test_normalise_type_alias(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise({"type": "H1", "content": "Title"}, 0)
        assert result["type"] == "HEADING_1"

    def test_normalise_unknown_type(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise({"type": "WEIRD", "content": "X"}, 0)
        assert result["type"] == "BODY"

    def test_normalise_non_dict(self):
        from app.pipeline.generation.content_parser import ContentParser
        result = ContentParser._normalise("just a string", 0)
        assert result["type"] == "BODY"


# ─── QualityScorer ─────────────────────────────────────────────────────────────

class TestQualityScorer:
    def test_empty_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        result = QualityScorer().score({}, "ieee", {"sections": ["Abstract"]})
        assert result["template_compliance"] == 0.0

    def test_full_score(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        content = {"Abstract": "word " * 200}
        result = QualityScorer().score(content, "ieee", {"sections": ["Abstract"]})
        assert result["template_compliance"] == 100.0
        assert result["content_completeness"] == 100.0

    def test_citation_count(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        content = {"Body": "As shown in [1], and [2,3] see also (Smith 2020)"}
        result = QualityScorer().score(content, "ieee", {"sections": ["Body"]})
        assert result["citation_count"] >= 2

    def test_section_balance_perfect(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = {"A": "word " * 100, "B": "word " * 100}
        result = QualityScorer().score({"sections": [{"title": "A", "content": "word " * 100}, {"title": "B", "content": "word " * 100}]}, "ieee", {"sections": ["A", "B"]})
        assert result["section_balance"] > 90.0

    def test_word_count(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("one two three") == 3
        assert QualityScorer._word_count("") == 0

    def test_required_sections_fallback(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._required_sections({}, {"A": "text"}) == ["A"]

    def test_percentage(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._percentage(3, 4) == 75.0
        assert QualityScorer._percentage(0, 0) == 0.0


# ─── TaskParser ────────────────────────────────────────────────────────────────

class TestTaskParser:
    def test_validate_spec_defaults(self):
        from app.pipeline.generation.task_parser import TaskParser
        result = TaskParser()._validate_spec({}, "write a paper")
        assert result["doc_type"] == "research_paper"
        assert result["template"] == "IEEE"
        assert result["title"] == "Untitled Research Paper"
        assert "References" in result["sections"]

    def test_validate_spec_custom(self):
        from app.pipeline.generation.task_parser import TaskParser
        raw = {"doc_type": "review", "title": "My Review", "template": "ieee"}
        result = TaskParser()._validate_spec(raw, "prompt")
        assert result["doc_type"] == "review"
        assert result["title"] == "My Review"

    def test_validate_spec_citation_style(self):
        from app.pipeline.generation.task_parser import TaskParser
        result = TaskParser()._validate_spec({"citation_style": "vancouver"}, "")
        assert result["citation_style"] == "vancouver"

    def test_validate_spec_bad_doc_type(self):
        from app.pipeline.generation.task_parser import TaskParser
        result = TaskParser()._validate_spec({"doc_type": "invalid"}, "")
        assert result["doc_type"] == "research_paper"

    def test_extract_json(self):
        from app.pipeline.generation.task_parser import _extract_json
        assert _extract_json('{"a": 1}') == '{"a": 1}'
        assert _extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
        assert _extract_json("not json") is None
        assert _extract_json("") is None

    def test_keywords_from_prompt(self):
        from app.pipeline.generation.task_parser import _keywords_from_prompt
        result = _keywords_from_prompt("machine learning for natural language processing", limit=3)
        assert len(result) <= 3
        assert "machine" in result

    def test_parse(self):
        from app.pipeline.generation.task_parser import TaskParser
        tp = TaskParser()
        import asyncio
        with patch("app.pipeline.generation.task_parser.generate", return_value='{"doc_type": "essay", "title": "My Essay"}'):
            result = asyncio.run(tp.parse("write an essay about AI"))
            assert result["doc_type"] == "essay"
            assert result["title"] == "My Essay"

    def test_parse_fallback(self):
        from app.pipeline.generation.task_parser import TaskParser
        tp = TaskParser()
        import asyncio
        with patch("app.pipeline.generation.task_parser.generate", side_effect=Exception("LLM down")):
            result = asyncio.run(tp.parse("write about AI"))
            assert result["doc_type"] == "research_paper"

    def test_load_templates(self):
        from app.pipeline.generation.task_parser import _load_templates
        result = _load_templates()
        assert isinstance(result, dict)
