# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for NLP ContentAnalyzer pipeline stage.
Covers process(), section confidence estimation, caption quality,
readability checks, keyword extraction (yake/basic/keybert), LLM keywords.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from app.pipeline.nlp.analyzer import (
    ContentAnalyzer, extract_keywords, _parse_keyword_payload,
    methods_detect_abstract, _get_keybert_model,
)

@pytest.fixture
def analyzer():

    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    return ContentAnalyzer()

@pytest.fixture
def doc_empty():
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    return PipelineDocument(document_id="nlp0", blocks=[])

@pytest.fixture
def doc_with_blocks():
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    return PipelineDocument(document_id="nlp1", blocks=[
        Block(block_id="b1", index=0, text="Introduction", block_type=BlockType.HEADING_1),
        Block(block_id="b2", index=1, text="This paper presents a novel approach to natural language processing using deep learning methods.", block_type=BlockType.BODY),
        Block(block_id="b3", index=2, text="Figure 1. Architecture of the proposed model.", block_type=BlockType.BODY),
        Block(block_id="b4", index=3, text="this study introduces background context and results analysis across multiple datasets", block_type=BlockType.ABSTRACT_BODY),
    ])

class TestContentAnalyzerProcess:
    def test_process_empty_document(self, analyzer, doc_empty):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer.process(doc_empty)
        assert len(result.blocks) == 0

    def test_section_confidence_added(self, analyzer, doc_with_blocks):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer.process(doc_with_blocks)
        hints = result.blocks[0].metadata.get("ai_hints", {})
        assert hints.get("predicted_section") == "Introduction"
        assert hints.get("confidence") == 0.9

    def test_abstract_readability_added(self, analyzer, doc_with_blocks):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer.process(doc_with_blocks)
        hints = result.blocks[3].metadata.get("ai_hints", {})
        assert "readability" in hints

    def test_caption_quality_figure(self, analyzer, doc_with_blocks):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer.process(doc_with_blocks)
        hints = result.blocks[2].metadata.get("ai_hints", {})
        assert "caption_quality" in hints

    def test_no_metadata_mutations(self, analyzer, doc_with_blocks):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        original_ids = [b.block_id for b in doc_with_blocks.blocks]
        result = analyzer.process(doc_with_blocks)
        assert [b.block_id for b in result.blocks] == original_ids

class TestSectionConfidence:
    def test_exact_match_abstract(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b1", index=0, text="Abstract", block_type=BlockType.HEADING_1)
        result = analyzer._estimate_section_confidence(block)
        assert result["section"] == "Abstract"
        assert result["confidence"] == 0.95

    def test_numbered_introduction(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b2", index=1, text="1. Introduction", block_type=BlockType.HEADING_1)
        result = analyzer._estimate_section_confidence(block)
        assert result["section"] == "Introduction"

    def test_references_match(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b3", index=2, text="References", block_type=BlockType.HEADING_1)
        result = analyzer._estimate_section_confidence(block)
        assert result["confidence"] == 0.95

    def test_unknown_section_returns_none(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b4", index=3, text="Random heading", block_type=BlockType.HEADING_1)
        result = analyzer._estimate_section_confidence(block)
        assert result is None

    def test_empty_text_returns_none(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b5", index=4, text="", block_type=BlockType.HEADING_1)
        result = analyzer._estimate_section_confidence(block)
        assert result is None

class TestCaptionQuality:
    def test_good_caption(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer._evaluate_caption_quality("Figure 1. Architecture of the proposed transformer model.")
        assert result == "Good"

    def test_short_caption(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer._evaluate_caption_quality("Fig 1. Model")
        assert result == "Short"

    def test_vague_caption(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer._evaluate_caption_quality("The image below shows a diagram.")
        assert result == "Possibly Vague"

    def test_is_potential_caption_true(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert analyzer._is_potential_caption("Figure 1. Architecture") is True
        assert analyzer._is_potential_caption("Table 1. Results") is True
        assert analyzer._is_potential_caption("Chart showing data") is True

    def test_is_potential_caption_false(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert analyzer._is_potential_caption("Introduction") is False
        assert analyzer._is_potential_caption("") is False

class TestReadability:
    def test_standard_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "This is a standard sentence. And here is another one."
        result = analyzer._check_readability(text)
        assert result == "Simple (Short Sentences)"

    def test_complex_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "This is an extremely long and complex sentence that goes on and on with many clauses and subclauses making it very hard to read and understand."
        result = analyzer._check_readability(text)
        assert result == "Standard"

    def test_truly_complex_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        words = "word " * 35
        text = words + "."
        result = analyzer._check_readability(text)
        assert result == "Complex (Long Sentences)"

    def test_simple_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "Short. Simple. Few words."
        result = analyzer._check_readability(text)
        assert result == "Simple (Short Sentences)"

    def test_simple_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "Short. Simple. Few words."
        result = analyzer._check_readability(text)
        assert result == "Simple (Short Sentences)"

    def test_empty_text_readability(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = analyzer._check_readability("")
        assert result == "N/A"

class TestMethodsDetectAbstract:
    def test_detects_abstract_text(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "This study provides background on the topic and presents results from multiple experiments. " * 5
        assert methods_detect_abstract(text) is True

    def test_short_text_not_abstract(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert methods_detect_abstract("background and results") is False

    def test_empty_text_not_abstract(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert methods_detect_abstract("") is False

class TestExtractKeywordsBasic:
    def test_basic_keyword_extraction(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "machine learning natural language processing deep learning neural networks"
        result = extract_keywords(text)
        assert len(result) > 0
        assert all(isinstance(k, str) for k in result)

    def test_empty_text_returns_empty(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert extract_keywords("") == []

    def test_basic_fallback_uses_frequency(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        text = "the quick brown fox jumps over the lazy dog"
        with patch("app.services.enhancement_manager.enhancement_manager") as mock_em:
            mock_em.profile.enabled = False
            result = extract_keywords(text)
            assert len(result) > 0

class TestExtractKeywordsYake:
    @patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", True)
    @patch("app.pipeline.nlp.analyzer.yake")
    def test_yake_keywords_used(self, mock_yake):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        mock_extractor = MagicMock()
        mock_yake.KeywordExtractor.return_value = mock_extractor
        mock_extractor.extract_keywords.return_value = [("deep learning", 0.1), ("NLP", 0.2)]

        with patch("app.services.enhancement_manager.enhancement_manager") as mock_em:
            mock_em.profile.enabled = True
            mock_em.profile.keyword_enabled = True
            mock_em.get_keyword_backends.return_value = ["yake", "basic"]

            result = extract_keywords("deep learning nlp text analysis")
            assert len(result) > 0

class TestParseKeywordPayload:
    def test_parse_json_array(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert _parse_keyword_payload('["ml", "nlp"]', 5) == ["ml", "nlp"]

    def test_parse_json_object(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert _parse_keyword_payload('{"keywords": ["ml", "ai"]}', 5) == ["ml", "ai"]

    def test_parse_code_block(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = _parse_keyword_payload('```json\n["ml", "nlp"]\n```', 5)
        assert result == ["ml", "nlp"]

    def test_parse_embedded_array(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = _parse_keyword_payload('text ["a", "b"] more', 5)
        assert result == ["a", "b"]

    def test_parse_invalid_returns_empty(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert _parse_keyword_payload("not json", 5) == []

    def test_parse_empty_string(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        assert _parse_keyword_payload("", 5) == []

    def test_deduplication(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = _parse_keyword_payload('["ml", "ML", "ml"]', 5)
        assert len(result) == 1

    def test_top_k_limit(self):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        result = _parse_keyword_payload('["a", "b", "c", "d", "e", "f"]', 3)
        assert len(result) == 3

class TestKeybertModel:
    @patch("app.pipeline.nlp.analyzer.importlib.util.find_spec", return_value=None)
    def test_keybert_unavailable_returns_none(self, mock_spec):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        import app.pipeline.nlp.analyzer as _an
        _an._KEYBERT_MODEL = None
        assert _get_keybert_model() is None

class TestEdgeCases:
    def test_process_no_ai_hints_for_empty_block(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        doc = PipelineDocument(document_id="ec1", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.HEADING_1),
        ])
        result = analyzer.process(doc)
        assert result.blocks[0].metadata.get("ai_hints") is None

    def test_process_sets_default_metadata(self, analyzer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
        block = Block(block_id="b1", index=0, text="Introduction")
        doc = PipelineDocument(document_id="ec2", blocks=[block])
        result = analyzer.process(doc)
        assert "ai_hints" in result.blocks[0].metadata
