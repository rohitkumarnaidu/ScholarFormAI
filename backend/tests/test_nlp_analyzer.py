from unittest.mock import MagicMock, patch

from app.models.block import Block, BlockType


class TestEstimateSectionConfidence:
    def test_exact_match(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        block = Block(block_id="b1", text="Introduction", index=0)
        result = analyzer._estimate_section_confidence(block)
        assert result["section"] == "Introduction"
        assert result["confidence"] == 0.9

    def test_numbered_heading(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        block = Block(block_id="b1", text="1. Introduction", index=0)
        result = analyzer._estimate_section_confidence(block)
        assert result["section"] == "Introduction"
        assert result["confidence"] == 0.9

    def test_references_match(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        block = Block(block_id="b1", text="References", index=0)
        result = analyzer._estimate_section_confidence(block)
        assert result["confidence"] == 0.95

    def test_no_match(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        block = Block(block_id="b1", text="Random text", index=0)
        assert analyzer._estimate_section_confidence(block) is None

    def test_empty_text(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        block = Block(block_id="b1", text="", index=0)
        assert analyzer._estimate_section_confidence(block) is None


class TestIsPotentialCaption:
    def test_figure_start(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        assert analyzer._is_potential_caption("Figure 1: Results")

    def test_table_start(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        assert analyzer._is_potential_caption("Table 2: Data")

    def test_chart_start(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        assert analyzer._is_potential_caption("Chart A: Growth")

    def test_not_caption(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        assert not analyzer._is_potential_caption("This is a paragraph")


class TestEvaluateCaptionQuality:
    def test_good_caption(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._evaluate_caption_quality(
            "Figure 1: The experimental results show significant improvement"
        )
        assert result == "Good"

    def test_short_caption(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._evaluate_caption_quality("Fig 1: Data")
        assert result == "Short"

    def test_vague_caption(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._evaluate_caption_quality("Fig 1: image diagram below")
        assert result == "Possibly Vague"


class TestCheckReadability:
    def test_standard(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._check_readability(
            "This is a standard length sentence with enough words. "
            "So is this nice paragraph of average length."
        )
        assert result == "Standard"

    def test_complex(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        long = " ".join(["word"] * 35) + ". " + " ".join(["word"] * 35) + "."
        result = analyzer._check_readability(long)
        assert result == "Complex (Long Sentences)"

    def test_simple(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._check_readability("Hi. There. Bye.")
        assert result == "Simple (Short Sentences)"

    def test_empty(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        result = analyzer._check_readability("")
        assert result == "N/A"


class TestMethodsDetectAbstract:
    def test_matches(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        text = "Background of study " * 20 + "Results show " * 20
        assert methods_detect_abstract(text)

    def test_too_short(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        assert not methods_detect_abstract("background and results")

    def test_no_keywords(self):
        from app.pipeline.nlp.analyzer import methods_detect_abstract
        assert not methods_detect_abstract("nothing relevant here " * 50)


class TestParseKeywordPayload:
    def test_json_array(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('["ml", "nlp", "ai"]', top_k=5)
        assert result == ["ml", "nlp", "ai"]

    def test_json_object(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('{"keywords": ["ml", "nlp"]}', top_k=5)
        assert result == ["ml", "nlp"]

    def test_with_code_fence(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('```json\n["ml"]\n```', top_k=5)
        assert result == ["ml"]

    def test_empty(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        assert _parse_keyword_payload("", top_k=5) == []

    def test_dedupes(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('["ml", "ML", "ml"]', top_k=5)
        assert result == ["ml"]

    def test_respects_top_k(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('["a", "b", "c", "d"]', top_k=2)
        assert len(result) == 2

    def test_invalid_json(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        assert _parse_keyword_payload("not json at all", top_k=5) == []

    def test_items_fallback(self):
        from app.pipeline.nlp.analyzer import _parse_keyword_payload
        result = _parse_keyword_payload('{"items": ["a", "b"]}', top_k=5)
        assert result == ["a", "b"]


class TestProcess:
    def test_adds_hints_to_section_block(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="Introduction", index=0, block_type=BlockType.BODY),
        ]
        result = analyzer.process(doc)
        assert result.blocks[0].metadata["ai_hints"]["predicted_section"] == "Introduction"

    def test_skips_unknown_blocks(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="Random stuff", index=0, block_type=BlockType.BODY),
        ]
        result = analyzer.process(doc)
        assert "ai_hints" not in result.blocks[0].metadata

    def test_caption_quality_added(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="Figure 1: Results", index=0, block_type=BlockType.FIGURE_CAPTION),
        ]
        result = analyzer.process(doc)
        assert result.blocks[0].metadata["ai_hints"]["caption_quality"] == "Short"

    def test_readability_check_on_abstract(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        doc = MagicMock()
        doc.blocks = [
            Block(block_id="b1", text="This paper background and results show clear evidence",
                  index=0, block_type=BlockType.ABSTRACT_BODY),
        ]
        result = analyzer.process(doc)
        assert "readability" in result.blocks[0].metadata["ai_hints"]

    def test_no_blocks(self):
        from app.pipeline.nlp.analyzer import ContentAnalyzer
        analyzer = ContentAnalyzer()
        doc = MagicMock()
        doc.blocks = []
        result = analyzer.process(doc)
        assert result is doc


class TestExtractKeywords:
    @patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False)
    @patch("app.pipeline.nlp.analyzer.KEYBERT_AVAILABLE", False)
    def test_basic_fallback(self):
        from app.pipeline.nlp.analyzer import extract_keywords
        result = extract_keywords("machine learning and natural language processing are key areas")
        assert "machine" in result
        assert len(result) >= 2

    def test_empty_text(self):
        from app.pipeline.nlp.analyzer import extract_keywords
        assert extract_keywords("") == []

    def test_safety_fallback_no_libs(self):
        from app.pipeline.nlp.analyzer import extract_keywords

        with patch("app.pipeline.nlp.analyzer.YAKE_AVAILABLE", False):
            with patch("app.pipeline.nlp.analyzer.KEYBERT_AVAILABLE", False):
                with patch("app.services.enhancement_manager.enhancement_manager") as mock_em:
                    mock_em.profile.enabled = False
                    result = extract_keywords("deep learning for image recognition when tested")
                assert len(result) > 0

    def test_enforces_top_k(self):
        from app.pipeline.nlp.analyzer import extract_keywords
        result = extract_keywords("a b c d e f g h i j", top_k=3)
        assert len(result) <= 3
