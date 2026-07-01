# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, PropertyMock
import pytest


class TestReviewManager:
    def _make_block(self, block_id="b1", confidence=None, semantic_intent="body", metadata=None):
        b = MagicMock()
        b.block_id = block_id
        if metadata is None:
            metadata = {}
        if confidence is not None:
            metadata["classification_confidence"] = confidence
        b.metadata = metadata
        b.semantic_intent = semantic_intent
        return b

    def _make_doc(self, blocks=None, metadata=None):
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.metadata = metadata or MagicMock()
        doc.metadata.ai_hints = {}
        doc.review = None
        return doc

    def test_init_validates_thresholds(self):
        from app.pipeline.validation.review_manager import ReviewManager
        with pytest.raises(ValueError, match="critical_threshold"):
            ReviewManager(review_threshold=0.5, critical_threshold=0.6)
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=1.5, critical_threshold=0.5)

    def test_ok_status(self):
        from app.pipeline.validation.review_manager import ReviewManager
        doc = self._make_doc(blocks=[self._make_block(confidence=0.95)])
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert result.review.status == "OK"

    def test_review_status(self):
        from app.pipeline.validation.review_manager import ReviewManager
        doc = self._make_doc(blocks=[self._make_block(confidence=0.6)])
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert "REVIEW" in str(result.review.status).upper()

    def test_critical_status(self):
        from app.pipeline.validation.review_manager import ReviewManager
        doc = self._make_doc(blocks=[self._make_block(confidence=0.3)])
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert "CRITICAL" in str(result.review.status).upper()

    def test_ai_hints_confidence(self):
        from app.pipeline.validation.review_manager import ReviewManager
        doc = self._make_doc(blocks=[self._make_block(confidence=0.95)])
        doc.metadata.ai_hints = {"semantic_advice": {"confidence": 0.5}}
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert "REVIEW" in str(result.review.status).upper()

    def test_confidence_from_nlp_fallback(self):
        from app.pipeline.validation.review_manager import ReviewManager
        b = self._make_block(block_id="b1")
        b.classification_confidence = None
        b.metadata = {"nlp_confidence": 0.3}
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert "CRITICAL" in str(result.review.status).upper()

    def test_confidence_from_attribute(self):
        from app.pipeline.validation.review_manager import ReviewManager
        b = MagicMock()
        b.block_id = "b1"
        b.metadata = {}
        b.classification_confidence = 0.2
        b.semantic_intent = "body"
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert "CRITICAL" in result.review.flags[0]

    def test_flags_limited_to_5(self):
        from app.pipeline.validation.review_manager import ReviewManager
        blocks = [self._make_block(block_id=f"b{i}", confidence=0.3) for i in range(10)]
        doc = self._make_doc(blocks=blocks)
        rm = ReviewManager(review_threshold=0.7, critical_threshold=0.45)
        result = rm.evaluate(doc)
        assert len(result.review.flags) <= 5
