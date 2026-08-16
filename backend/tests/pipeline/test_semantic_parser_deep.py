# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep coverage tests for SemanticParser — targets remaining uncovered lines/branches.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestHeuristicClassifyEdgeCases:
    """Additional edge-case coverage for _heuristic_classify."""

    def test_none_text(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        r = p._heuristic_classify(None)
        assert r["type"] == "BODY"

    def test_short_lowercase_heading_candidate(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        r = p._heuristic_classify("Related Work")
        assert r["type"] == "HEADING"
        assert r["confidence"] == 0.6


class TestClassifyBlockEdgeCases:
    """Additional edge-case coverage for classify_block."""

    def test_use_transformer_true_scibert_disabled(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_llm_classification", return_value=False),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}) as mock_heur,
        ):
            r = p.classify_block("text", use_transformer=True)
            mock_heur.assert_called_once_with("text")
            assert r["type"] == "BODY"


class TestRepairFragmentedHeadingsEdgeCases:
    """Additional edge-case coverage for _repair_fragmented_headings."""

    def test_number_with_space_before_lowercase(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="42"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="is the answer"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 1
        assert result[0].text == "42. is the answer"

    def test_consecutive_numbers_merged(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="1"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="introduction"),
            Block(block_id="b3", index=2, block_type=BlockType.BODY, text="2"),
            Block(block_id="b4", index=3, block_type=BlockType.BODY, text="methods"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2
        assert result[0].text == "1. introduction"
        assert result[1].text == "2. methods"

    def test_number_at_end(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="Some text"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="5"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2


