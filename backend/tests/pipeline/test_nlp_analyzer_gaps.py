# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Gap-filling tests for NLP ContentAnalyzer to reach 100% line coverage.
"""

from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
import importlib
import sys
import json
import builtins
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from app.pipeline.nlp.analyzer import (
    ContentAnalyzer,
    extract_keywords,
    _parse_keyword_payload,
    _extract_keywords_with_keyllm,
    methods_detect_abstract,
    _get_keybert_model,
    YAKE_AVAILABLE,
    yake,
)

from app.models import PipelineDocument as Document
def _doc(blocks=None) -> Document:
    from app.models import PipelineDocument as Document, Block, BlockType
    return Document(document_id="test-id", blocks=blocks or [])

def _block(text="Hello world", **kw) -> Block:
    from app.models import PipelineDocument as Document, Block, BlockType
    defaults = {"block_id": "b1", "index": 0, "text": text}
    defaults.update(kw)
    return Block(**defaults)

# ===================================================================
# Module-level import error paths (lines 22-24, 26-29, 32-33)
# ===================================================================

class TestModuleLevelImports:

    def test_yake_import_failure_path(self):
        """Force yake ImportError via module reload to cover lines 22-24."""
        from app.models import PipelineDocument as Document, Block, BlockType
        import app.pipeline.nlp.analyzer as mod
        saved = {}
        for key in list(sys.modules):
            if key == 'yake' or key.startswith('yake.'):
                saved[key] = sys.modules.pop(key)
        try:
            seen_yake = [False]
            orig_import = builtins.__import__
            def mock_import(name, *args, **kw):
                from app.models import PipelineDocument as Document, Block, BlockType
                if name == 'yake':
                    seen_yake[0] = True
                    raise ImportError("simulated yake missing")
                return orig_import(name, *args, **kw)
            with patch('builtins.__import__', mock_import):
                importlib.reload(mod)
                assert mod.YAKE_AVAILABLE is False
                assert mod.yake is None
                assert seen_yake[0] is True
        finally:
            for k, v in saved.items():
                sys.modules[k] = v
            importlib.reload(mod)

    def test_nlp_available_flag(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        from app.pipeline.nlp import analyzer as _an
        assert _an.NLP_AVAILABLE is not None

# ===================================================================
# ContentAnalyzer.__init__ (line 41)
# ===================================================================

class TestContentAnalyzerInit:

    def test_init_sets_nlp_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        ca = ContentAnalyzer()
        assert ca.nlp is None

    def test_init_and_process_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        ca = ContentAnalyzer()
        doc = _doc()
        result = ca.process(doc)
        assert result is doc

# ===================================================================
# process — exhaustive branch coverage (lines 50-79)
# ===================================================================

class TestProcessBranches:

    def setup_method(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        self.ca = ContentAnalyzer()

    def test_block_without_hints_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(text="Ordinary paragraph text without section keywords", block_type=BlockType.BODY)
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        assert "ai_hints" not in b.metadata

    def test_section_conf_only_no_other_hints(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(text="Methods", block_type=BlockType.HEADING_1)
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        hints = b.metadata.get("ai_hints", {})
        assert hints.get("predicted_section") == "Methods"
        assert "caption_quality" not in hints
        assert "readability" not in hints

    def test_caption_only_no_section_conf(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(text="Figure 1. Results", block_type=BlockType.BODY)
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        hints = b.metadata.get("ai_hints", {})
        assert "caption_quality" in hints
        assert "predicted_section" not in hints

    def test_readability_from_block_type(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(
            text="Background " * 50 + "results " * 50 + "study " * 20,
            block_type=BlockType.ABSTRACT_BODY,
        )
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        hints = b.metadata.get("ai_hints", {})
        assert "readability" in hints

    def test_readability_from_methods_detect(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(
            text="Background " * 50 + "results " * 50 + "study " * 20,
            block_type=BlockType.BODY,
        )
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        hints = b.metadata.get("ai_hints", {})
        assert "readability" in hints

    def test_no_hints_for_empty_text(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = _block(text="", block_type=BlockType.BODY)
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        assert not b.metadata.get("ai_hints", {})

    def test_metadata_already_exists_merged(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        b = Block(block_id="b1", index=0, text="Introduction", metadata={"existing": 1})
        doc = _doc(blocks=[b])
        self.ca.process(doc)
        assert b.metadata["existing"] == 1
        assert "ai_hints" in b.metadata

# ===================================================================
# _estimate_section_confidence (lines 83-109)
# ===================================================================

class TestEstimateSectionConfidenceGaps:

    def setup_method(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        self.ca = ContentAnalyzer()

    def test_empty_text_returns_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._estimate_section_confidence(_block(text="")) is None

    def test_whitespace_text_returns_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._estimate_section_confidence(_block(text="   ")) is None

    def test_known_header_exact(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        for header, conf in [
            ("abstract", 0.95), ("introduction", 0.9), ("methods", 0.8),
            ("methodology", 0.8), ("results", 0.8), ("discussion", 0.8),
            ("conclusion", 0.8), ("references", 0.95), ("bibliography", 0.95),
        ]:
            b = _block(text=header)
            result = self.ca._estimate_section_confidence(b)
            assert result["section"] == header.title()
            assert result["confidence"] == conf
            assert "notes" in result

    def test_numbered_header(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        result = self.ca._estimate_section_confidence(_block(text="1. Introduction"))
        assert result["section"] == "Introduction"

    def test_dotted_numbered_header(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        result = self.ca._estimate_section_confidence(_block(text="1.1. Methods"))
        assert result["section"] == "Methods"

    def test_unknown_header_returns_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._estimate_section_confidence(_block(text="Appendix A")) is None

# ===================================================================
# _is_potential_caption (line 112)
# ===================================================================

class TestIsPotentialCaptionGaps:

    def setup_method(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        self.ca = ContentAnalyzer()

    def test_fig_prefix(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._is_potential_caption("Figure 1. Results")

    def test_table_prefix(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._is_potential_caption("Table 2. Data")

    def test_chart_prefix(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._is_potential_caption("Chart A. Growth")

    def test_non_caption(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert not self.ca._is_potential_caption("Introduction")

    def test_case_insensitive(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._is_potential_caption("figure 1")
        assert self.ca._is_potential_caption("TABLE 1")

    def test_leading_spaces_ignored(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._is_potential_caption("  Figure 1.")

    def test_empty_text(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert not self.ca._is_potential_caption("")

# ===================================================================
# _evaluate_caption_quality (lines 116-124)
# ===================================================================

class TestEvaluateCaptionQualityGaps:

    def setup_method(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        self.ca = ContentAnalyzer()

    def test_short_caption_fewer_than_5_words(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._evaluate_caption_quality("Fig 1. Test") == "Short"

    def test_vague_caption_between_5_and_10_with_vague_word(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._evaluate_caption_quality("Figure showing image of data") == "Possibly Vague"

    def test_good_caption_10_or_more_words(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        text = "Figure 1. Experimental results showing significant improvement over baseline methods"
        assert self.ca._evaluate_caption_quality(text) == "Good"

    def test_long_with_vague_word_not_triggered(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        text = "Figure 1. The image below shows a complex diagram of the proposed architecture with multiple components"
        assert self.ca._evaluate_caption_quality(text) == "Good"

# ===================================================================
# _check_readability (lines 129-139)
# ===================================================================

class TestCheckReadabilityGaps:

    def setup_method(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        self.ca = ContentAnalyzer()

    def test_empty_text(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._check_readability("") == "N/A"

    def test_no_sentences(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._check_readability("...") == "N/A"

    def test_complex_long_sentences(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        long = "word " * 35 + "."
        assert self.ca._check_readability(long) == "Complex (Long Sentences)"

    def test_simple_short_sentences(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert self.ca._check_readability("Short.") == "Simple (Short Sentences)"

    def test_standard(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        text = "This is a normal sentence with enough words to test readability. It has moderate length overall for this analysis."
        assert self.ca._check_readability(text) == "Standard"

# ===================================================================
# methods_detect_abstract (line 144)
# ===================================================================

class TestMethodsDetectAbstractGaps:

    def test_matches_background_and_results_long(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        text = ("background " * 30 + "results " * 30)
        assert methods_detect_abstract(text) is True

    def test_only_background_not_enough(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert methods_detect_abstract("background " * 50) is False

    def test_only_results_not_enough(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert methods_detect_abstract("results " * 50) is False

    def test_too_short(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert methods_detect_abstract("background and results") is False

    def test_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert methods_detect_abstract("") is False

# ===================================================================
# _get_keybert_model (lines 149-164)
# ===================================================================

class TestGetKeybertModelGaps:

    def test_keybert_not_available_returns_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("importlib.util.find_spec", return_value=None):
            assert _get_keybert_model() is None

    def test_keybert_import_fails_returns_none(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("importlib.util.find_spec", return_value=True):
            with patch("app.pipeline.nlp.analyzer._KEYBERT_MODEL", None):
                orig_import = builtins.__import__
                def fake_import(name, *args, **kw):
                    from app.models import PipelineDocument as Document, Block, BlockType
                    if "keybert" in name:
                        raise ImportError("no keybert")
                    return orig_import(name, *args, **kw)
                with patch("builtins.__import__", fake_import):
                    assert _get_keybert_model() is None

    def test_keybert_success(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        fake_keybert = MagicMock()
        fake_keybert.KeyBERT.return_value = mock_model
        with patch.dict(sys.modules, {"keybert": fake_keybert}):
            with patch("importlib.util.find_spec", return_value=True):
                with patch("app.utils.singleton.get_or_create_safe", return_value=mock_model):
                    model = _get_keybert_model()
                    assert model is mock_model

    def test_keybert_cached(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        import app.pipeline.nlp.analyzer as _an
        _an._KEYBERT_MODEL = None
        mock_model = MagicMock()
        fake_keybert = MagicMock()
        fake_keybert.KeyBERT.return_value = mock_model
        with patch.dict(sys.modules, {"keybert": fake_keybert}):
            with patch("importlib.util.find_spec", return_value=True):
                with patch("app.utils.singleton.get_or_create_safe", return_value=mock_model):
                    first = _get_keybert_model()
                    second = _get_keybert_model()
                    assert first is second
        _an._KEYBERT_MODEL = None

    def test_keybert_other_exception_during_import(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("importlib.util.find_spec", return_value=True):
            with patch("app.pipeline.nlp.analyzer._KEYBERT_MODEL", None):
                orig_import = builtins.__import__
                def fake_import(name, *args, **kw):
                    from app.models import PipelineDocument as Document, Block, BlockType
                    if "keybert" in name:
                        raise RuntimeError("unexpected error")
                    return orig_import(name, *args, **kw)
                with patch("builtins.__import__", fake_import):
                    assert _get_keybert_model() is None

# ===================================================================
# extract_keywords — exhaustive branch coverage (lines 172-250)
# ===================================================================

ENH_PATH = "app.services.enhancement_manager.enhancement_manager"

class TestExtractKeywordsGaps:

    def test_empty_text_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert extract_keywords("") == []
        assert extract_keywords(None) == []
        assert extract_keywords("   ") == []

    def test_basic_fallback_direct(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = False
            result = extract_keywords("machine learning for text classification")
            assert len(result) > 0

    def test_basic_fallback_from_profile_disabled(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = False
            result = extract_keywords("machine learning for text classification")
            assert len(result) > 0

    def test_enhancement_manager_unavailable(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH, side_effect=Exception("no manager")):
            result = extract_keywords("machine learning for text")
            assert len(result) > 0

    def test_yake_backend_returns_results(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("keyword1", 0.5), ("keyword2", 0.3)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake"]
            with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                    result = extract_keywords("machine learning text analysis")
                    assert result == ["keyword1", "keyword2"]

    def test_yake_not_available_skips(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake", "basic"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_yake_extraction_fails_falls_through(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["yake", "basic"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", side_effect=Exception("yake crash")):
                    result = extract_keywords("machine learning text analysis")
                    assert len(result) > 0

    def test_keybert_backend_returns_results(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("kw1", 0.9), ("kw2", 0.8)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert result == ["kw1", "kw2"]

    def test_keybert_not_available_skips(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=None):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_keybert_extraction_fails(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.side_effect = Exception("keybert crash")
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_keybert_empty_keywords_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = []
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert len(result) > 0

    def test_keybert_none_in_result_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [None, ("valid", 0.5)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                result = extract_keywords("machine learning text analysis")
                assert "valid" in result

    def test_keybert_uses_yake_candidates_when_available(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("ml", 0.9)]
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("ml", 0.5), ("text", 0.3)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                    with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                        extract_keywords("machine learning text analysis")
                        args = mock_model.extract_keywords.call_args
                        assert args[1]["candidates"] == ["ml", "text"]

    def test_keybert_no_yake_candidates(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = [("ml", 0.9)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert", "basic"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False):
                    extract_keywords("machine learning text analysis")
                    args = mock_model.extract_keywords.call_args
                    assert args[1]["candidates"] is None

    def test_keyllm_backend_success(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keyllm", "basic"]
            with patch("app.pipeline.nlp.analyzer._extract_keywords_with_keyllm",
                       return_value=["llm_kw1", "llm_kw2"]):
                result = extract_keywords("machine learning text")
                assert result == ["llm_kw1", "llm_kw2"]

    def test_keyllm_returns_empty_list(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keyllm", "basic"]
            with patch("app.pipeline.nlp.analyzer._extract_keywords_with_keyllm",
                       return_value=[]):
                result = extract_keywords("machine learning text")
                assert len(result) > 0

    def test_keyllm_falls_through_on_failure(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keyllm", "basic"]
            with patch("app.pipeline.nlp.analyzer._extract_keywords_with_keyllm",
                       side_effect=Exception("llm crash")):
                result = extract_keywords("machine learning text")
                assert len(result) > 0

    def test_unknown_backend_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["unknown_backend", "basic"]
            result = extract_keywords("machine learning text")
            assert len(result) > 0

    def test_ultimate_safety_fallback_with_yake_candidates(self):
        """Safety fallback uses yake_candidates when keybert returns empty."""
        from app.models import PipelineDocument as Document, Block, BlockType
        mock_model = MagicMock()
        mock_model.extract_keywords.return_value = []
        mock_yake = MagicMock()
        mock_yake.extract_keywords.return_value = [("safety_kw", 0.5)]
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["keybert"]
            with patch("app.pipeline.nlp.analyzer._get_keybert_model", return_value=mock_model):
                with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True):
                    with patch("app.pipeline.nlp.analyzer.yake.KeywordExtractor", return_value=mock_yake):
                        result = extract_keywords("machine learning text")
                        assert "safety_kw" in result

    def test_ultimate_fallback_no_yake(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch(ENH_PATH) as m:
            m.profile.enabled = True
            m.profile.keyword_enabled = True
            m.get_keyword_backends.return_value = ["unknown_backend"]
            with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False):
                result = extract_keywords("machine learning text analysis for classification")
                assert len(result) > 0

# ===================================================================
# _parse_keyword_payload — exhaustive branch coverage (lines 254-290)
# ===================================================================

class TestParseKeywordPayloadGaps:

    def test_empty_string(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload("", 5) == []

    def test_valid_json_array(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('["kw1", "kw2", "kw3"]', 5) == ["kw1", "kw2", "kw3"]

    def test_json_object_with_keywords(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('{"keywords": ["a", "b"]}', 5) == ["a", "b"]

    def test_json_object_with_items(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('{"items": ["x", "y"]}', 5) == ["x", "y"]

    def test_code_block_format(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        raw = "```json\n[\"kw1\", \"kw2\"]\n```"
        assert _parse_keyword_payload(raw, 5) == ["kw1", "kw2"]

    def test_code_block_no_json_tag(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        raw = "```\n[\"kw1\"]\n```"
        assert _parse_keyword_payload(raw, 5) == ["kw1"]

    def test_bracket_fallback_extraction(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        raw = "Here are the keywords: [\"kw1\", \"kw2\"]"
        assert _parse_keyword_payload(raw, 5) == ["kw1", "kw2"]

    def test_no_brackets_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload("no brackets here", 5) == []

    def test_empty_brackets_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload("[]", 5) == []

    def test_not_a_list_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('{"keywords": "not a list"}', 5) == []

    def test_duplicates_removed(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        result = _parse_keyword_payload('["kw1", "kw1", "KW1", "kw2"]', 5)
        assert result == ["kw1", "kw2"]

    def test_respects_top_k(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        result = _parse_keyword_payload('["a", "b", "c", "d", "e", "f"]', 3)
        assert result == ["a", "b", "c"]

    def test_none_items_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('[null, "a"]', 5) == ["a"]

    def test_empty_strings_skipped(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        assert _parse_keyword_payload('["", "a"]', 5) == ["a"]

    def test_bracket_extraction_not_json(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        raw = 'not json [broken, still, not, json]'
        assert _parse_keyword_payload(raw, 5) == []

    def test_start_brace_no_end_brace(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        raw = 'prefix [not closed'
        assert _parse_keyword_payload(raw, 5) == []

# ===================================================================
# _extract_keywords_with_keyllm — exhaustive branch coverage (lines 294-307)
# ===================================================================

class TestExtractKeywordsWithKeyllmGaps:

    def test_successful_extraction(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": '["kw1", "kw2", "kw3"]'}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == ["kw1", "kw2", "kw3"]

    def test_none_result_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value=None):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_empty_text_result_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": ""}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_malformed_response_returns_empty(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": "bad response"}):
            result = _extract_keywords_with_keyllm("sample text", 3)
            assert result == []

    def test_prompt_truncated_to_3500(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        long_text = "word " * 5000
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": '["kw1"]'}) as m:
            _extract_keywords_with_keyllm(long_text, 3)
            call_arg = m.call_args[0][0]
            user_content = call_arg[1]["content"]
            assert len(user_content) < 4000

    def test_result_as_none_text_key(self):
        from app.models import PipelineDocument as Document, Block, BlockType
        with patch("app.pipeline.nlp.analyzer.generate_with_fallback",
                   return_value={"text": None}):
            result = _extract_keywords_with_keyllm("sample", 3)
            assert result == []
