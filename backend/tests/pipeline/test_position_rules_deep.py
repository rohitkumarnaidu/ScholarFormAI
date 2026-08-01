# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep coverage extensions for position_rules.py.
Adds gap coverage for functions with all imports inside function bodies.
"""

from __future__ import annotations
import pytest
pytestmark = [pytest.mark.pipeline]


def _b(text: str = "", index: int = 1, bid: str | None = None):
    from app.models import Block, BlockType
    return Block(block_id=bid or f"b{index}", text=text, index=index, block_type=BlockType.BODY)


def _empty(index: int):
    return _b("", index)


class TestIsFirstNonEmptyBlock:
    def test_true_when_first(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_first_non_empty_block
        blocks = [_b("Hello", 1), _b("World", 2)]
        assert is_first_non_empty_block(blocks[0], blocks) is True

    def test_false_when_not_first(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_first_non_empty_block
        blocks = [_b("First", 1), _b("Second", 2)]
        assert is_first_non_empty_block(blocks[1], blocks) is False

    def test_all_empty_returns_false(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_first_non_empty_block
        blocks = [_empty(0), _empty(1)]
        assert is_first_non_empty_block(blocks[0], blocks) is False

    def test_first_with_empties_before(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_first_non_empty_block
        blocks = [_empty(0), _b("First", 1)]
        assert is_first_non_empty_block(blocks[1], blocks) is True


class TestIsIsolatedLine:
    def test_first_block_no_next(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_isolated_line
        blocks = [_b("Only", 1)]
        assert is_isolated_line(blocks[0], blocks) is True

    def test_not_in_blocks(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_isolated_line
        lone = _b("Orphan", 9, bid="orphan")
        assert is_isolated_line(lone, []) is False

    def test_first_of_many_isolated(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_isolated_line
        blocks = [_b("First", 1), _empty(2)]
        assert is_isolated_line(blocks[0], blocks) is True

    def test_last_of_many_with_empty_before(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_isolated_line
        blocks = [_empty(0), _b("Last", 1)]
        assert is_isolated_line(blocks[1], blocks) is True

    def test_middle_with_text_on_both_sides(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import is_isolated_line
        blocks = [_b("A", 0), _b("B", 1), _b("C", 2)]
        assert is_isolated_line(blocks[1], blocks) is False


class TestCountEmptyBlocksBefore:
    def test_block_not_found(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_before
        lone = _b("Orphan", 9, bid="orphan")
        assert count_empty_blocks_before(lone, []) == 0

    def test_empty_chain_stops_at_non_empty(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_before
        blocks = [_b("A", 0), _empty(1), _empty(2), _b("B", 3)]
        assert count_empty_blocks_before(blocks[3], blocks) == 2

    def test_at_start_no_parent(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_before
        blocks = [_b("A", 0)]
        assert count_empty_blocks_before(blocks[0], blocks) == 0


class TestCountEmptyBlocksAfter:
    def test_block_not_found(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_after
        lone = _b("Orphan", 9, bid="orphan")
        assert count_empty_blocks_after(lone, []) == 0

    def test_empty_chain_stops_at_non_empty(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import count_empty_blocks_after
        blocks = [_b("A", 0), _empty(1), _empty(2), _b("B", 3)]
        assert count_empty_blocks_after(blocks[0], blocks) == 2


class TestGetBlockPositionRatio:
    def test_single_block(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import get_block_position_ratio
        blocks = [_b("Only", 0)]
        assert get_block_position_ratio(blocks[0], blocks) == 0.0

    def test_not_found(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import get_block_position_ratio
        lone = _b("Orphan", 9, bid="orphan")
        assert get_block_position_ratio(lone, []) == 0.0

    def test_middle_position(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import get_block_position_ratio
        blocks = [_b("A", 0), _b("B", 1), _b("C", 2)]
        assert get_block_position_ratio(blocks[1], blocks) == 0.5


class TestAnalyzePosition:
    def test_not_first_isolated_with_empties(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import analyze_position
        blocks = [_b("Lead", 0), _empty(1), _empty(2), _b("Target", 3), _empty(4)]
        result = analyze_position(blocks[3], blocks)
        assert result["is_first"] is False
        assert result["is_isolated"] is True
        assert result["empty_before"] >= 2
        assert result["empty_after"] >= 1

    def test_near_end_position(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import analyze_position
        many = [_b(f"B{i}", i) for i in range(10)]
        result = analyze_position(many[9], many)
        assert any("document end" in h for h in result["position_hints"])

    def test_middle_no_special_hints(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import analyze_position
        blocks = [_b("A", 0), _b("B", 1), _b("C", 2)]
        result = analyze_position(blocks[1], blocks)
        assert len(result["position_hints"]) == 0


class TestBoostHeadingConfidenceByPosition:
    def test_all_boosts_combined(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import boost_heading_confidence_by_position
        pos_info = {"is_first": True, "is_isolated": True, "empty_before": 2}
        result = boost_heading_confidence_by_position(0.3, pos_info)
        assert result == pytest.approx(0.75)

    def test_caps_at_one(self, monkeypatch):
        from app.pipeline.structure_detection.position_rules import boost_heading_confidence_by_position
        pos_info = {"is_first": True, "is_isolated": True, "empty_before": 2}
        result = boost_heading_confidence_by_position(0.9, pos_info)
        assert result == 1.0
