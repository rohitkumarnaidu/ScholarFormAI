# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from app.pipeline.structure_detection.heading_rules import (
    detect_numbering_pattern,
    detect_title,
    matches_section_keyword,
    is_likely_heading_by_style,
    infer_heading_level,
    get_capitalization_ratio,
    analyze_heading_candidate,
)


def _b(text: str, index: int = 1, font_size: float = 12.0, bold: bool = False):
    from app.models.block import TextStyle
    from app.models import Block, BlockType

    style = TextStyle(font_size=font_size, bold=bold)
    return Block(block_id=f"b{index}", text=text, index=index, block_type=BlockType.BODY, style=style)


class TestDetectNumberingPattern:
    def test_decimal_single(self):
        result = detect_numbering_pattern("1. Introduction")
        assert result is not None
        assert result["pattern_type"] == "decimal"
        assert result["number"] == "1"
        assert result["level"] == 1

    def test_decimal_nested(self):
        result = detect_numbering_pattern("1.2.3 Details")
        assert result is not None
        assert result["level"] == 3

    def test_roman_upper(self):
        result = detect_numbering_pattern("I. Introduction")
        assert result is not None
        assert result["pattern_type"] == "roman"

    def test_no_pattern(self):
        result = detect_numbering_pattern("Introduction")
        assert result is None

    def test_empty_text(self):
        assert detect_numbering_pattern("") is None


class TestDetectTitle:
    def test_first_block_is_title(self):
        blocks = [_b("My Paper Title", 1)]
        assert detect_title(blocks[0], blocks) is True

    def test_not_first_block(self):
        blocks = [_b("First", 1), _b("Second", 2)]
        assert detect_title(blocks[1], blocks) is False

    def test_too_long(self):
        blocks = [_b("A" * 201, 1)]
        assert detect_title(blocks[0], blocks) is False

    def test_numbered_not_title(self):
        blocks = [_b("1. Introduction", 1)]
        assert detect_title(blocks[0], blocks) is False

    def test_empty_not_title(self):
        blocks = [_b("", 1)]
        assert detect_title(blocks[0], blocks) is False


class TestMatchesSectionKeyword:
    def test_abstract(self):
        assert matches_section_keyword("Abstract") is True

    def test_introduction(self):
        assert matches_section_keyword("Introduction") is True

    def test_references(self):
        assert matches_section_keyword("References") is True

    def test_not_a_keyword(self):
        assert matches_section_keyword("My Custom Section") is False

    def test_too_long(self):
        assert matches_section_keyword("A" * 60) is False

    def test_case_insensitive(self):
        assert matches_section_keyword("ABSTRACT") is True


class TestIsLikelyHeadingByStyle:
    def test_bold_heading(self):
        block = _b("Introduction", bold=True, font_size=14.0)
        result, confidence = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert result is True
        assert confidence == 0.5

    def test_large_font(self):
        block = _b("Introduction", font_size=18.0)
        result, confidence = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert result is True

    def test_all_caps_alone_below_threshold(self):
        block = _b("INTRODUCTION", font_size=12.0)
        result, confidence = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert result is False
        assert confidence == 0.2

    def test_not_heading(self):
        block = _b("Some regular body text that is not a heading.", font_size=12.0)
        result, confidence = is_likely_heading_by_style(block, avg_font_size=12.0)
        if result:
            assert confidence < 0.5

    def test_no_avg_font_size_bold_not_enough(self):
        block = _b("Introduction", bold=True)
        result, confidence = is_likely_heading_by_style(block)
        assert result is False
        assert confidence == 0.3


class TestInferHeadingLevel:
    def test_level_1_from_keyword(self):
        block = _b("Introduction", 1)
        assert infer_heading_level(block) == 1

    def test_level_2_from_numbering(self):
        info = {"level": 2}
        block = _b("1.1 Background", 1)
        assert infer_heading_level(block, numbering_info=info) == 2

    def test_default_level(self):
        block = _b("Custom Section", 1)
        level = infer_heading_level(block)
        assert 1 <= level <= 4


class TestGetCapitalizationRatio:
    def test_all_capitalized(self):
        ratio = get_capitalization_ratio("Introduction Methods Results")
        assert ratio > 0.8

    def test_lowercase(self):
        ratio = get_capitalization_ratio("some random words here")
        assert ratio < 0.3

    def test_empty_string(self):
        assert get_capitalization_ratio("") == 0.0


class TestAnalyzeHeadingCandidate:
    def test_heading_candidate_found(self):
        blocks = [_b("Introduction", 1)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is not None
        assert result["is_heading"] is True

    def test_not_heading(self):
        blocks = [_b("a small line of regular text", 1)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        if result:
            assert result["confidence"] < 0.5

    def test_empty_block(self):
        blocks = [_b("", 1)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        if result:
            assert result["is_heading"] is False
