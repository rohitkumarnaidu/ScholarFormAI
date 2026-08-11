
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from unittest.mock import MagicMock, patch

from app.models import Block, BlockType
from app.models import PipelineDocument as Document
from app.pipeline.nlp.analyzer import (
    ContentAnalyzer,
    _extract_keywords_with_keyllm,
    _get_keybert_model,
    _parse_keyword_payload,
    extract_keywords,
    methods_detect_abstract,
)
from app.pipeline.nlp.analyzer import (
    ContentAnalyzer as _ca,
)


def _doc(blocks=None) -> Document:

    return Document(document_id="test-id", blocks=blocks or [])


def _block(text="Hello world", **kw) -> Block:
    defaults = {"block_id": "b1", "index": 0, "text": text}
    defaults.update(kw)
    return Block(**defaults)


# ===================================================================
# ContentAnalyzer — process
# ===================================================================

class TestContentAnalyzerProcess:
    def test_empty_document(self):
        doc = _doc()
        result = ContentAnalyzer().process(doc)
        assert result is doc
        assert result.blocks == []

    def test_block_without_hints_unchanged(self):
        b = _block()
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert b.metadata == {}

    def test_section_confidence_adds_hints(self):
        b = _block(text="Introduction")
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert "ai_hints" in b.metadata
        assert b.metadata["ai_hints"]["predicted_section"] == "Introduction"

    def test_caption_quality_added(self):
        b = _block(text="Figure 1. Test results show significant improvement")
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert "caption_quality" in b.metadata.get("ai_hints", {})

    def test_readability_for_abstract_body(self):
        b = _block(text="Background and results are both present in this sufficiently long text", block_type=BlockType.ABSTRACT_BODY)
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert "readability" in b.metadata.get("ai_hints", {})

    def test_readability_via_methods_detect_abstract(self):
        long = "Background " * 50 + "results " * 50
        b = _block(text=long, block_type=BlockType.PARAGRAPH)
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert "readability" in b.metadata.get("ai_hints", {})

    def test_metadata_no_ai_hints_key_added(self):
        b = Block(block_id="b1", index=0, text="Introduction",
                  metadata={"existing": "value"})
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert "existing" in b.metadata
        assert "ai_hints" in b.metadata

    def test_multiple_blocks_all_analyzed(self):
        b1 = _block(text="Introduction", block_id="b1")
        b2 = _block(text="Methods", block_id="b2")
        doc = _doc(blocks=[b1, b2])
        ContentAnalyzer().process(doc)
        assert "ai_hints" in b1.metadata
        assert "ai_hints" in b2.metadata

    def test_empty_text_no_crash(self):
        b = _block(text="")
        doc = _doc(blocks=[b])
        ContentAnalyzer().process(doc)
        assert not b.metadata.get("ai_hints", {})


# ===================================================================
# _estimate_section_confidence
# ===================================================================

class TestEstimateSectionConfidence:
    def test_empty_text_returns_none(self):
        b = _block(text="")
        assert _ca()._estimate_section_confidence(b) is None

    def test_whitespace_text_returns_none(self):
        b = _block(text="   ")
        assert _ca()._estimate_section_confidence(b) is None

    def test_known_header_returned(self):
        for header, conf in [
            ("abstract", 0.95), ("introduction", 0.9), ("methods", 0.8),
            ("methodology", 0.8), ("results", 0.8), ("discussion", 0.8),
            ("conclusion", 0.8), ("references", 0.95), ("bibliography", 0.95),
        ]:
            b = _block(text=header)
            result = _ca()._estimate_section_confidence(b)
            assert result["section"] == header.title()
            assert result["confidence"] == conf

    def test_numbered_header_parsed(self):
        b = _block(text="1. Introduction")
        result = _ca()._estimate_section_confidence(b)
        assert result["section"] == "Introduction"

    def test_unknown_header_returns_none(self):
        b = _block(text="Appendix")
        assert _ca()._estimate_section_confidence(b) is None


# ===================================================================
# _is_potential_caption
# ===================================================================

class TestIsPotentialCaption:
    def test_fig_prefix(self):
        assert _ca()._is_potential_caption("Figure 1. Results")

    def test_table_prefix(self):
        assert _ca()._is_potential_caption("Table 2. Data")

    def test_chart_prefix(self):
        assert _ca()._is_potential_caption("Chart A. Growth")

    def test_non_caption(self):
        assert not _ca()._is_potential_caption("Introduction")

    def test_case_insensitive(self):
        assert _ca()._is_potential_caption("figure 1")
        assert _ca()._is_potential_caption("TABLE 1")

    def test_leading_spaces_ignored(self):
        assert _ca()._is_potential_caption("  Figure 1.")


# ===================================================================
# _evaluate_caption_quality
# ===================================================================

class TestEvaluateCaptionQuality:
    def test_short_caption(self):
        result = _ca()._evaluate_caption_quality("Figure 1")
        assert result == "Short"

    def test_vague_caption(self):
        result = _ca()._evaluate_caption_quality("Figure showing image of data")
        assert result == "Possibly Vague"

    def test_good_caption(self):
        result = _ca()._evaluate_caption_quality(
            "Figure 1. Experimental results showing significant improvement in accuracy")
        assert result == "Good"

    def test_vague_word_short_caption(self):
        result = _ca()._evaluate_caption_quality("image chart diagram")
        assert result == "Short"

    def test_vague_word_long_enough(self):
        result = _ca()._evaluate_caption_quality("The image below shows the results")
        assert result == "Possibly Vague"


# ===================================================================
# _check_readability
# ===================================================================

class TestCheckReadability:
    def test_empty_text(self):
        result = _ca()._check_readability("")
        assert result == "N/A"

    def test_no_sentences(self):
        result = _ca()._check_readability("...")
        assert result == "N/A"

    def test_complex(self):
        long = "This is a very long sentence with many words that makes the average sentence length exceed thirty words quite easily indeed because it just keeps going and going with no end in sight."
        result = _ca()._check_readability(long)
        assert "Complex" in result

    def test_simple(self):
        result = _ca()._check_readability("Short.")
        assert "Simple" in result

    def test_standard(self):
        text = "This is a normal sentence with enough words to pass the threshold. It has moderate length overall."
        result = _ca()._check_readability(text)
        assert result == "Standard"


# ===================================================================
# methods_detect_abstract
# ===================================================================

class TestMethodsDetectAbstract:
    def test_matches(self):
        text = "Background info about the study and results from the experiment " * 10
        assert methods_detect_abstract(text) is True

    def test_too_short(self):
        assert methods_detect_abstract("background and results") is False

    def test_no_keywords(self):
        assert methods_detect_abstract("hello world") is False


# ===================================================================
# _get_keybert_model
# ===================================================================

class TestGetKeybertModel:
    def test_keybert_not_available_returns_none(self):
        with patch("importlib.util.find_spec", return_value=None):
            assert _get_keybert_model() is None

    def test_keybert_import_fails_returns_none(self):
        with patch("importlib.util.find_spec", return_value=True):
            with patch("app.pipeline.nlp.analyzer._KEYBERT_MODEL", None):
                # Trigger ImportError during KeyBERT import
                import builtins
                original_import = builtins.__import__
                def fake_import(name, *args, **kw):
                    if "keybert" in name:
                        raise ImportError("no module")
                    return original_import(name, *args, **kw)
                with patch("builtins.__import__", fake_import):
                    assert _get_keybert_model() is None

    def test_keybert_success(self):
        import sys
        mock_model = MagicMock()
        fake_keybert = MagicMock()
        fake_keybert.KeyBERT.return_value = mock_model
        with patch.dict(sys.modules, {"keybert": fake_keybert}):
            with patch("importlib.util.find_spec", return_value=True):
                with patch("app.utils.singleton.get_or_create_safe", return_value=mock_model):
                    model = _get_keybert_model()
                    assert model is mock_model

    def test_keybert_cached(self):
        import sys
        mock_model = MagicMock()
        fake_keybert = MagicMock()
        from app.pipeline.nlp import analyzer as _m
        _m._KEYBERT_MODEL = None
        with patch.dict(sys.modules, {"keybert": fake_keybert}):
            with patch("importlib.util.find_spec", return_value=True):
                with patch("app.utils.singleton.get_or_create_safe", return_value=mock_model):
                    first = _get_keybert_model()
                    second = _get_keybert_model()
                    assert first is second
        _m._KEYBERT_MODEL = None


# ===================================================================
# extract_keywords
# ===================================================================

ENH_PATH = "app.services.enhancement_manager.enhancement_manager"

class TestExtractKeywords:
    def test_empty_text_returns_empty(self):
        assert extract_keywords("") == []
        assert extract_keywords(None) == []
        assert extract_keywords("   ") == []

    def test_basic_fallback(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["basic"]
            result = extract_keywords("machine learning for text classification")
            assert len(result) > 0

    def test_enhancement_disabled_uses_basic(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = False
            result = extract_keywords("machine learning for text")
            assert len(result) > 0

    def test_enhancement_manager_unavailable(self):
        with patch(ENH_PATH, side_effect=Exception("no manager")):
            result = extract_keywords("machine learning for text")
            assert len(result) > 0

    def test_yake_backend(self):
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("keyword1", 0.5), ("keyword2", 0.3)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake"]
            with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                    result = extract_keywords("machine learning text analysis")
                    assert len(result) == 2
                    assert result[0] == "keyword1"

    def test_yake_not_available_skips(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake", "basic"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_yake_extraction_fails_falls_through(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake", "basic"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", side_effect=Exception("yake crash")):
                    result = extract_keywords("machine learning text analysis")
                    assert len(result) > 0

    def test_keybert_backend(self):
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("kw1", 0.9), ("kw2", 0.8)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert len(result) == 2

    def test_keybert_not_available_skips(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=None):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_keybert_extraction_fails(self):
        mock_model = MagicMock()
        mock_model.extract_keywords.side_effect = Exception("keybert crash")
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_keybert_uses_yake_candidates_when_available(self):
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("ml", 0.5), ("text", 0.3)]
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("ml", 0.9)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                    with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                        extract_keywords("machine learning text analysis")
                        mock_model.extract_keywords.assert_called_once()
                        args = mock_model.extract_keywords.call_args
                        assert args[1]["candidates"] == ["ml", "text"]

    def test_keyllm_backend_success(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keyllm", "basic"]
            with patch("app.pipeline.nlp.analyzer._extract_keywords_with_keyllm",
                       return_value=["kw1", "kw2", "kw3"]):
                result = extract_keywords("machine learning text analysis")
                assert result == ["kw1", "kw2", "kw3"]

    def test_keyllm_falls_through_on_failure(self):
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keyllm", "basic"]
            with patch("app.pipeline.nlp.analyzer._extract_keywords_with_keyllm",
                       side_effect=Exception("llm crash")):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_ultimate_safety_fallback_with_yake_candidates(self):
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("safety-kw", 0.5)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                    with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=MagicMock()):
                        result = extract_keywords("a")
                        # yake returned candidates but keybert not queried;
                        # yake already returned them in the yake backend step


# ===================================================================
# _parse_keyword_payload
# ===================================================================

class TestParseKeywordPayload:
    def test_empty(self):
        assert _parse_keyword_payload("", 5) == []

    def test_valid_json_array(self):
        result = _parse_keyword_payload('["kw1", "kw2", "kw3"]', 5)
        assert result == ["kw1", "kw2", "kw3"]

    def test_json_array_with_dict(self):
        result = _parse_keyword_payload('{"keywords": ["a", "b"]}', 5)
        assert result == ["a", "b"]

    def test_items_fallback(self):
        result = _parse_keyword_payload('{"items": ["x", "y"]}', 5)
        assert result == ["x", "y"]

    def test_jagged_json_extracted_from_markdown_block(self):
        raw = """```json
["kw1", "kw2"]
```"""
        result = _parse_keyword_payload(raw, 5)
        assert result == ["kw1", "kw2"]

    def test_bracket_extraction_fallback(self):
        raw = "Here are the keywords: [\"kw1\", \"kw2\"]"
        result = _parse_keyword_payload(raw, 5)
        assert result == ["kw1", "kw2"]

    def test_no_brackets_returns_empty(self):
        result = _parse_keyword_payload("no brackets here", 5)
        assert result == []

    def test_empty_brackets_returns_empty(self):
        result = _parse_keyword_payload("[]", 5)
        assert result == []

    def test_not_a_list_returns_empty(self):
        result = _parse_keyword_payload('{"keywords": "not a list"}', 5)
        assert result == []

    def test_duplicates_removed(self):
        result = _parse_keyword_payload('["kw1", "kw1", "KW1", "kw2"]', 5)
        assert result == ["kw1", "kw2"]

    def test_respects_top_k(self):
        result = _parse_keyword_payload('["a", "b", "c", "d", "e", "f"]', 3)
        assert result == ["a", "b", "c"]

    def test_none_items_skipped(self):
        result = _parse_keyword_payload('[null, "a"]', 5)
        assert result == ["a"]

    def test_empty_strings_skipped(self):
        result = _parse_keyword_payload('["", "a"]', 5)
        assert result == ["a"]


# ===================================================================
# _extract_keywords_with_keyllm
# ===================================================================

class TestExtractKeywordsWithKeyllm:
    def test_success(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": '["kw1", "kw2", "kw3"]'}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == ["kw1", "kw2", "kw3"]

    def test_none_result(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value=None):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_empty_text_result(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": ""}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_malformed_response(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": "bad response"}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_prompt_truncated_to_3500(self):
        long_text = "word " * 5000
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": '["kw1"]'}) as m:
            _extract_keywords_with_keyllm(long_text, 3)
            call_arg = m.call_args[0][0]
            user_content = call_arg[1]["content"]
            assert len(user_content) < 4000
