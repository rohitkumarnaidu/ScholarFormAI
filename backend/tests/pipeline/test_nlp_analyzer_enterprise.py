# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, ANY
import pytest


# ─── ContentAnalyzer ───────────────────────────────────────────────────────────

class TestContentAnalyzer:
    def test_init(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        ca = ContentAnalyzer()
        assert ca.nlp is None

    def test_estimate_section_confidence_empty(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        b = MagicMock()
        b.text = ""
        assert ContentAnalyzer()._estimate_section_confidence(b) is None

    def test_estimate_section_confidence_exact(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        b = MagicMock()
        b.text = "Introduction"
        result = ContentAnalyzer()._estimate_section_confidence(b)
        assert result["section"] == "Introduction"
        assert result["confidence"] == 0.9

    def test_estimate_section_confidence_numbered(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        b = MagicMock()
        b.text = "1. Introduction"
        result = ContentAnalyzer()._estimate_section_confidence(b)
        assert result["section"] == "Introduction"

    def test_estimate_section_confidence_no_match(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        b = MagicMock()
        b.text = "Random Header"
        assert ContentAnalyzer()._estimate_section_confidence(b) is None

    def test_estimate_section_confidence_abstract(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        b = MagicMock()
        b.text = "Abstract"
        result = ContentAnalyzer()._estimate_section_confidence(b)
        assert result["confidence"] == 0.95

    def test_is_potential_caption_true(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert ContentAnalyzer()._is_potential_caption("Figure 1: Results")
        assert ContentAnalyzer()._is_potential_caption("Table 1: Data")
        assert ContentAnalyzer()._is_potential_caption("Chart 1")

    def test_is_potential_caption_false(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert not ContentAnalyzer()._is_potential_caption("Some text")
        assert not ContentAnalyzer()._is_potential_caption("")

    def test_evaluate_caption_quality_short(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert ContentAnalyzer()._evaluate_caption_quality("Fig 1") == "Short"

    def test_evaluate_caption_quality_vague(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert ContentAnalyzer()._evaluate_caption_quality("The image below shows a test") == "Possibly Vague"

    def test_evaluate_caption_quality_good(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert ContentAnalyzer()._evaluate_caption_quality("A very detailed description of the results shown") == "Good"

    def test_check_readability_empty(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert ContentAnalyzer()._check_readability("") == "N/A"

    def test_check_readability_complex(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        t = "This is a very long sentence with many words that makes it complex to read and understand " * 3
        assert "Complex" in ContentAnalyzer()._check_readability(t)

    def test_check_readability_simple(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        assert "Simple" in ContentAnalyzer()._check_readability("Hi. Bye.")

    def test_check_readability_standard(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        t = "This is a normal sentence with more words. It has reasonable length for standard text. Each sentence here is fairly average in its word count."
        assert ContentAnalyzer()._check_readability(t) == "Standard"

    def test_process_adds_hints(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        ca = ContentAnalyzer()
        b = MagicMock()
        b.text = "Introduction"
        b.block_type = "BODY"
        b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        result = ca.process(doc)
        assert result is doc
        assert b.metadata["ai_hints"]["predicted_section"] == "Introduction"

    def test_process_caption_and_abstract(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        ca = ContentAnalyzer()
        b = MagicMock()
        b.text = "Figure 1: A very detailed and complete description " + ("background " * 50) + (" results " * 50)
        b.block_type = "BODY"
        b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        result = ca.process(doc)
        assert result is doc
        hints = b.metadata["ai_hints"]
        assert "caption_quality" in hints
        assert "readability" in hints

    def test_process_no_hints(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        ca = ContentAnalyzer()
        b = MagicMock()
        b.text = "short"
        b.block_type = "BODY"
        b.metadata = {}
        doc = MagicMock()
        doc.blocks = [b]
        ca.process(doc)
        assert b.metadata == {}


# ─── Module-level helpers ──────────────────────────────────────────────────────

class TestMethodsDetectAbstract:
    def test_empty(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        assert methods_detect_abstract("") is False

    def test_short_text(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        assert methods_detect_abstract("background and results") is False

    def test_matches(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        t = ("background " * 50) + (" results " * 50)
        assert methods_detect_abstract(t) is True


class TestGetKeybertModel:
    def test_no_keybert_spec(self):
        from app.pipeline.nlp.analyzer import _get_keybert_model
        with patch("importlib.util.find_spec", return_value=None):
            assert _get_keybert_model() is None

    def test_import_fails(self):
        from app.pipeline.nlp.analyzer import _get_keybert_model
        with (
            patch("importlib.util.find_spec", return_value=True),
            patch("app.pipeline.nlp.analyzer.logger") as mock_logger,
        ):
            with patch("builtins.__import__", side_effect=ImportError("no keybert")):
                result = _get_keybert_model()
            assert result is None
            mock_logger.warning.assert_called_once()

    def test_success(self):
        mock_model = MagicMock()
        from app.pipeline.nlp.analyzer import _get_keybert_model
        with (
            patch("importlib.util.find_spec", return_value=True),
        ):
            with patch("builtins.__import__", return_value=MagicMock(KeyBERT=lambda **kw: mock_model)):
                with patch("app.pipeline.nlp.analyzer.get_or_create_safe", return_value=mock_model):
                    result = _get_keybert_model()
        assert result is mock_model


class TestParseKeywordPayload:
    def test_empty(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        assert _parse_keyword_payload("", 5) == []

    def test_valid_json_array(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        assert _parse_keyword_payload('["AI", "ML"]', 5) == ["AI", "ML"]

    def test_valid_json_dict(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        r = _parse_keyword_payload('{"keywords": ["AI", "ML"]}', 5)
        assert r == ["AI", "ML"]

    def test_code_fence(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        r = _parse_keyword_payload('```json\n["AI", "ML"]\n```', 5)
        assert r == ["AI", "ML"]

    def test_fallback_extract_brackets(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        r = _parse_keyword_payload('some text ["AI", "ML"] more text', 5)
        assert r == ["AI", "ML"]

    def test_no_brackets(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        assert _parse_keyword_payload("just text", 5) == []

    def test_removes_duplicates(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        r = _parse_keyword_payload('["AI", "ML", "AI"]', 5)
        assert r == ["AI", "ML"]

    def test_respects_top_k(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        r = _parse_keyword_payload('["A", "B", "C", "D"]', 2)
        assert len(r) == 2


class TestExtractKeywordsWithKeyllm:
    def test_success(self):
        mock_result = {"text": '["AI", "ML"]'}
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback", return_value=mock_result):
            from app.pipeline.nlp.analyzer import _extract_keywords_with_keyllm
            assert _extract_keywords_with_keyllm("some text", 5) == ["AI", "ML"]

    def test_empty_response(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback", return_value={}):
            from app.pipeline.nlp.analyzer import _extract_keywords_with_keyllm
            assert _extract_keywords_with_keyllm("text", 5) == []

    def test_none_response(self):
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback", return_value=None):
            from app.pipeline.nlp.analyzer import _extract_keywords_with_keyllm
            assert _extract_keywords_with_keyllm("text", 5) == []


class TestExtractKeywords:
    def test_empty_text(self):
        from app.pipeline.nlp.analyzer import extract_keywords
        assert extract_keywords("") == []

    def test_basic_fallback(self):
        with patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr:
            mock_mgr.profile.enabled = False
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning is great for data science", 3)
            assert len(result) > 0

    def test_yake_backend(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["yake"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning and deep learning techniques", 3)
            assert len(result) > 0

    def test_yake_unavailable(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["yake"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning techniques", 3)
            assert isinstance(result, list)

    def test_keybert_backend(self):
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("AI", 0.9), ("ML", 0.8)]
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False),
            patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["keybert"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("AI and ML techniques in research", 3)
            assert result == ["AI", "ML"]

    def test_keybert_unavailable_falls_to_basic(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False),
            patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=None),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["keybert"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning data science", 3)
            assert len(result) > 0

    def test_keyllm_backend(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.generate_with_fallback", return_value={"text": '["AI"]'}),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["keyllm"]
            from app.pipeline.nlp.analyzer import extract_keywords
            assert extract_keywords("AI research", 5) == ["AI"]

    def test_keyllm_fails_falls_to_yake(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True),
            patch("app.pipeline.nlp.analyzer.generate_with_fallback", side_effect=Exception("LLM down")),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["keyllm", "yake"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning natural language processing", 3)
            assert len(result) > 0

    def test_all_backends_fail_safety_fallback(self):
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_mgr,
            patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False),
            patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=None),
        ):
            mock_mgr.profile.enabled = True
            mock_mgr.profile.keyword_enabled = True
            mock_mgr.get_keyword_backends.return_value = ["keybert"]
            from app.pipeline.nlp.analyzer import extract_keywords
            result = extract_keywords("machine learning data science research", 3)
            assert len(result) > 0

    def test_enhancement_manager_unavailable(self):
        from app.pipeline.nlp.analyzer import extract_keywords
        result = extract_keywords("some text here for keywords", 3)
        assert isinstance(result, list)
