from unittest.mock import MagicMock

import pytest


class TestReviewManagerInit:
    def test_valid_thresholds(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(review_threshold=0.70, critical_threshold=0.45)
        assert rm.review_threshold == 0.70
        assert rm.critical_threshold == 0.45

    def test_critical_lt_review_required(self):
        from app.pipeline.validation.review_manager import ReviewManager

        with pytest.raises(ValueError):
            ReviewManager(review_threshold=0.45, critical_threshold=0.70)

    def test_thresholds_out_of_range(self):
        from app.pipeline.validation.review_manager import ReviewManager

        with pytest.raises(ValueError):
            ReviewManager(review_threshold=1.5, critical_threshold=0.5)

    def test_equal_thresholds_raises(self):
        from app.pipeline.validation.review_manager import ReviewManager

        with pytest.raises(ValueError):
            ReviewManager(review_threshold=0.7, critical_threshold=0.7)


class TestReviewManagerEvaluate:
    def test_all_high_confidence(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager()
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {"classification_confidence": 0.95}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "OK"

    def test_critical_confidence(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(critical_threshold=0.45)
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {"classification_confidence": 0.3}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "CRITICAL"

    def test_review_confidence(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(review_threshold=0.70, critical_threshold=0.45)
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {"classification_confidence": 0.60}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "REVIEW"

    def test_confidence_from_classification_confidence_fallback(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(critical_threshold=0.45)
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {}
        block.classification_confidence = 0.3
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "CRITICAL"

    def test_nlp_confidence_fallback(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(critical_threshold=0.45)
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {"nlp_confidence": 0.3}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "CRITICAL"

    def test_semantic_advice_triggers_review(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(review_threshold=0.70, critical_threshold=0.45)
        doc = MagicMock()
        doc.blocks = []
        doc.metadata.ai_hints = {"semantic_advice": {"confidence": 0.60}}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "REVIEW"

    def test_no_confidence_defaults_to_ok(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager()
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "OK"

    def test_flags_limited_to_five(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager(review_threshold=0.95, critical_threshold=0.90)
        doc = MagicMock()
        blocks = []
        for i in range(10):
            b = MagicMock()
            b.block_id = f"blk_{i:03d}"
            b.metadata = {"classification_confidence": 0.1}
            b.classification_confidence = None
            b.semantic_intent = None
            blocks.append(b)
        doc.blocks = blocks
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert len(result.review.flags) <= 5

    def test_invalid_confidence_clamped(self):
        from app.pipeline.validation.review_manager import ReviewManager

        rm = ReviewManager()
        doc = MagicMock()
        block = MagicMock()
        block.block_id = "blk_001"
        block.metadata = {"classification_confidence": 1.5}
        block.classification_confidence = None
        block.semantic_intent = None
        doc.blocks = [block]
        doc.metadata.ai_hints = {}
        doc.review = None

        result = rm.evaluate(doc)
        assert result.review.status == "OK"
