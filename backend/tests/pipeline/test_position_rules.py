# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.pipeline.structure_detection.position_rules import (
    analyze_position,
    boost_heading_confidence_by_position,
    count_empty_blocks_after,
    count_empty_blocks_before,
    get_block_position_ratio,
    is_first_non_empty_block,
    is_isolated_line,
)


def _b(text: str = "", index: int = 1, bid: str | None = None):

    from app.models import Block, BlockType

    return Block(block_id=bid or f"b{index}", text=text, index=index, block_type=BlockType.BODY)


def _empty(index: int):
    return _b("", index)


class TestIsFirstNonEmptyBlock:
    def test_true_when_first(self):
        blocks = [_b("Hello", 1), _b("World", 2)]
        assert is_first_non_empty_block(blocks[0], blocks) is True

    def test_false_when_not_first(self):
        blocks = [_b("First", 1), _b("Second", 2)]
        assert is_first_non_empty_block(blocks[1], blocks) is False

    def test_true_when_first_with_empty_before(self):
        blocks = [_empty(1), _b("First", 2)]
        assert is_first_non_empty_block(blocks[1], blocks) is True

    def test_false_with_earlier_non_empty(self):
        blocks = [_b("A", 1), _b("B", 2)]
        assert is_first_non_empty_block(blocks[1], blocks) is False

    def test_only_empty_blocks(self):
        blocks = [_empty(1), _empty(2)]
        assert is_first_non_empty_block(blocks[0], blocks) is False


class TestIsIsolatedLine:
    def test_isolated_with_empty_neighbors(self):
        blocks = [_empty(1), _b("Alone", 2), _empty(3)]
        assert is_isolated_line(blocks[1], blocks) is True

    def test_not_isolated_when_neighbors_have_text(self):
        blocks = [_b("A", 1), _b("B", 2), _b("C", 3)]
        assert is_isolated_line(blocks[1], blocks) is False

    def test_single_block_is_isolated(self):
        blocks = [_b("First", 1)]
        assert is_isolated_line(blocks[0], blocks) is True

    def test_last_block_isolated(self):
        blocks = [_empty(1), _b("Last", 2)]
        assert is_isolated_line(blocks[1], blocks) is True

    def test_block_not_in_list_returns_false(self):
        lone = _b("Orphan", 99, bid="orphan")
        assert is_isolated_line(lone, []) is False


class TestCountEmptyBlocksBefore:
    def test_none(self):
        blocks = [_b("A", 1)]
        assert count_empty_blocks_before(blocks[0], blocks) == 0

    def test_one_empty_before(self):
        blocks = [_empty(1), _b("A", 2)]
        assert count_empty_blocks_before(blocks[1], blocks) == 1

    def test_two_empties_before(self):
        blocks = [_empty(1), _empty(2), _b("A", 3)]
        assert count_empty_blocks_before(blocks[2], blocks) == 2

    def test_non_empty_before_stops_counting(self):
        blocks = [_b("X", 1), _empty(2), _b("A", 3)]
        assert count_empty_blocks_before(blocks[2], blocks) == 1

    def test_block_not_in_list_returns_zero(self):
        lone = _b("Orphan", 99, bid="orphan")
        assert count_empty_blocks_before(lone, []) == 0


class TestCountEmptyBlocksAfter:
    def test_none(self):
        blocks = [_b("A", 1)]
        assert count_empty_blocks_after(blocks[0], blocks) == 0

    def test_one_empty_after(self):
        blocks = [_b("A", 1), _empty(2)]
        assert count_empty_blocks_after(blocks[0], blocks) == 1

    def test_non_empty_after_stops(self):
        blocks = [_b("A", 1), _empty(2), _b("B", 3)]
        assert count_empty_blocks_after(blocks[0], blocks) == 1

    def test_block_not_in_list_returns_zero(self):
        lone = _b("Orphan", 99, bid="orphan")
        assert count_empty_blocks_after(lone, []) == 0

    def test_multiple_empties_after(self):
        blocks = [_b("A", 1), _empty(2), _empty(3)]
        assert count_empty_blocks_after(blocks[0], blocks) == 2


class TestGetBlockPositionRatio:
    def test_start(self):
        blocks = [_b("A", 1), _b("B", 2)]
        assert get_block_position_ratio(blocks[0], blocks) == 0.0

    def test_end(self):
        blocks = [_b("A", 1), _b("B", 2)]
        assert get_block_position_ratio(blocks[1], blocks) == 1.0

    def test_middle(self):
        blocks = [_b("A", 1), _b("B", 2), _b("C", 3)]
        assert get_block_position_ratio(blocks[1], blocks) == 0.5

    def test_empty_blocks_list_returns_zero(self):
        lone = _b("Solo", 1)
        assert get_block_position_ratio(lone, []) == 0.0

    def test_block_not_in_list_returns_zero(self):
        lone = _b("Orphan", 99, bid="orphan")
        blocks = [_b("A", 1)]
        assert get_block_position_ratio(lone, blocks) == 0.0


class TestAnalyzePosition:
    def test_first_block(self):
        blocks = [_b("Title", 1)]
        result = analyze_position(blocks[0], blocks)
        assert result["is_first"] is True

    def test_empty_before_ge2_adds_hint(self):
        blocks = [_empty(1), _empty(2), _b("Target", 3)]
        result = analyze_position(blocks[2], blocks)
        hints = result["position_hints"]
        assert any("blank lines before" in h for h in hints)

    def test_empty_after_ge1_adds_hint(self):
        blocks = [_b("Target", 1), _empty(2)]
        result = analyze_position(blocks[0], blocks)
        hints = result["position_hints"]
        assert any("blank line(s) after" in h for h in hints)

    def test_position_ratio_lt_0_1_adds_hint(self):
        blocks = [_b("A", 1), _b("B" * 50, 2)]
        result = analyze_position(blocks[0], blocks)
        hints = result["position_hints"]
        assert any("document start" in h for h in hints)

    def test_position_ratio_gt_0_9_adds_hint(self):
        blocks = [_b("A" * 50, 1), _b("Last", 2)]
        result = analyze_position(blocks[1], blocks)
        hints = result["position_hints"]
        assert any("document end" in h for h in hints)

    def test_isolated_block(self):
        blocks = [_empty(1), _b("Alone", 2), _empty(3)]
        result = analyze_position(blocks[1], blocks)
        assert result["is_isolated"] is True

    def test_returns_all_keys(self):
        blocks = [_b("A", 1), _b("B", 2)]
        result = analyze_position(blocks[0], blocks)
        assert "is_first" in result
        assert "is_isolated" in result
        assert "empty_before" in result
        assert "empty_after" in result
        assert "position_ratio" in result
        assert "position_hints" in result


class TestBoostHeadingConfidenceByPosition:
    def test_first_block_boost(self):
        pos_info = {"is_first": True, "is_isolated": False, "empty_before": 0}
        result = boost_heading_confidence_by_position(0.5, pos_info)
        assert result == pytest.approx(0.7)

    def test_isolated_boost(self):
        pos_info = {"is_first": False, "is_isolated": True, "empty_before": 0}
        result = boost_heading_confidence_by_position(0.5, pos_info)
        assert result == pytest.approx(0.65)

    def test_empty_before_boost(self):
        pos_info = {"is_first": False, "is_isolated": False, "empty_before": 2}
        result = boost_heading_confidence_by_position(0.5, pos_info)
        assert result == pytest.approx(0.6)

    def test_caps_at_one(self):
        pos_info = {"is_first": True, "is_isolated": False, "empty_before": 0}
        result = boost_heading_confidence_by_position(0.9, pos_info)
        assert result == 1.0

    def test_no_boost(self):
        pos_info = {"is_first": False, "is_isolated": False, "empty_before": 0}
        result = boost_heading_confidence_by_position(0.5, pos_info)
        assert result == 0.5
