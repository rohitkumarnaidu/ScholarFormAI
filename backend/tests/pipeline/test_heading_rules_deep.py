# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.models import Block, BlockType, TextStyle
from app.pipeline.structure_detection.heading_rules import (
    analyze_heading_candidate,
    detect_numbering_pattern,
    detect_title,
    get_capitalization_ratio,
    infer_heading_level,
    is_likely_heading_by_style,
    matches_section_keyword,
)


def _b(

    text: str,
    index: int = 1,
    font_size: float = 12.0,
    bold: bool = False,
    metadata: dict | None = None,
):
    style = TextStyle(font_size=font_size, bold=bold)
    return Block(
        block_id=f"b{index}",
        text=text,
        index=index,
        block_type=BlockType.BODY,
        style=style,
        metadata=metadata or {},
    )


class TestNumberingPatterns:
    """Cover detect_numbering_pattern edge cases."""

    def test_decimal_without_dot(self):
        result = detect_numbering_pattern("1 Introduction")
        assert result is not None
        assert result["pattern_type"] == "decimal"
        assert result["number"] == "1"
        assert result["level"] == 1

    def test_roman_II_introduction(self):
        result = detect_numbering_pattern("II. Background")
        assert result is not None
        assert result["pattern_type"] == "roman"
        assert result["number"] == "II"
        assert result["level"] == 1

    def test_roman_no_dot(self):
        result = detect_numbering_pattern("III Results")
        assert result is not None
        assert result["pattern_type"] == "roman"
        assert result["number"] == "III"

    def test_decimal_nested_deep(self):
        result = detect_numbering_pattern("1.2.3.4 Details")
        assert result is not None
        assert result["pattern_type"] == "decimal"
        assert result["level"] == 4
        assert result["number"] == "1.2.3.4"

    def test_decimal_uppercase_required(self):
        assert detect_numbering_pattern("1 introduction") is None

    def test_roman_uppercase_required(self):
        assert detect_numbering_pattern("i. introduction") is None


class TestDetectTitleEdgeCases:
    """Cover detect_title with header/footer blocks and numbered rejection."""

    def test_header_footer_skipped(self):
        hdr = _b("Header text", index=0, metadata={"is_header": True})
        title = _b("Real Title Here", index=1)
        blocks = [hdr, title]
        assert detect_title(title, blocks) is True

    def test_numbered_rejected(self):
        blocks = [_b("1. Introduction", index=0)]
        assert detect_title(blocks[0], blocks) is False

    def test_first_empty_then_valid(self):
        empty = _b("", index=0)
        title = _b("Valid Title", index=1)
        blocks = [empty, title]
        assert detect_title(title, blocks) is True

    def test_too_short_rejected(self):
        blocks = [_b("Hi", index=0)]
        assert detect_title(blocks[0], blocks) is False

    def test_footer_skipped_then_numbered_rejected(self):
        footer = _b("Page 1", index=0, metadata={"is_footer": True})
        numbered = _b("1. Results", index=1)
        blocks = [footer, numbered]
        assert detect_title(numbered, blocks) is False

    def test_all_blocks_are_headers_false(self):
        block = _b("Title", index=1, metadata={"is_header": True})
        hdr = _b("Header", index=0, metadata={"is_header": True})
        assert detect_title(block, [hdr, block]) is False


class TestMatchesSectionKeywordEdgeCases:
    """Cover prefix match and length guard branches."""

    def test_prefix_match_short(self):
        assert matches_section_keyword("Abstract - Summer 2023") is True

    def test_prefix_match_too_long(self):
        assert matches_section_keyword("Abstract - Summer 2023 Conference Proceedings") is False

    def test_exact_keyword_after_numbering(self):
        assert matches_section_keyword("1. Introduction") is True

    def test_prefix_with_numbering(self):
        assert matches_section_keyword("1.1 Abstract Details") is True

    def test_keyword_substring_not_match(self):
        assert matches_section_keyword("Abstract publishing requires many steps") is False

    def test_over_50_chars_rejected(self):
        assert matches_section_keyword("A" * 55) is False

    def test_roman_numbering_prefix_not_matched(self):
        assert matches_section_keyword("I. Introduction") is False

    def test_acknowledgements(self):
        assert matches_section_keyword("Acknowledgements") is True

    def test_competing_interests(self):
        assert matches_section_keyword("Competing Interests") is True


class TestStyleEdgeCases:
    """Cover length penalties, period penalty, font-size branches, uppercase."""

    def test_length_penalty_extreme(self):
        block = _b("Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident sunt.", index=0, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert score == -0.7  # -0.4(extreme) + -0.3(period)
        assert ok is False

    def test_length_penalty_very_long(self):
        block = _b("X" * 220, index=0, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert score == pytest.approx(-0.1)  # -0.3(>200) + 0.2(isupper) = -0.1
        assert ok is False

    def test_length_penalty_long(self):
        block = _b("X" * 130, index=0, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert score == 0.1  # -0.1(>120) + 0.2(isupper) = 0.1
        assert ok is False

    def test_ends_with_period(self):
        block = _b("A heading that ends.", index=0, bold=True, font_size=15.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        # 0.3(bold) + 0.5(font>1.2*avg) - 0.3(period) = 0.5
        assert score == 0.5
        assert ok is True

    def test_bold_alone_not_enough_no_avg(self):
        block = _b("Introduction", index=0, bold=True)
        ok, score = is_likely_heading_by_style(block)
        assert ok is False
        assert score == 0.3

    def test_font_size_above_avg_1_2(self):
        block = _b("Methods", index=0, font_size=18.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is True
        assert score == 0.5

    def test_font_size_above_avg_below_1_2(self):
        block = _b("Results", index=0, font_size=13.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is False
        assert score == 0.2

    def test_uppercase_text(self):
        block = _b("INTRODUCTION", index=0, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is False
        assert score == 0.2

    def test_short_text_lt_2(self):
        block = _b("X", index=0, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is False
        assert score == 0.0

    def test_no_penalty_font_size_and_bold_crosses_threshold(self):
        block = _b("Introduction", index=0, bold=True, font_size=15.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is True
        assert score == 0.8

    def test_uppercase_and_bold_font_size_below_threshold(self):
        block = _b("INTRODUCTION", index=0, bold=True, font_size=13.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        # 0.3(bold) + 0.2(font>avg) + 0.2(uppercase) = 0.7
        assert score == 0.7
        assert ok is True

    def test_bold_and_uppercase_alone(self):
        block = _b("INTRODUCTION", index=0, bold=True, font_size=12.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is True  # 0.5 >= HEADING_STYLE_THRESHOLD (0.5)
        assert score == 0.5  # 0.3(bold) + 0.2(isupper) = 0.5

    def test_font_above_avg_1_2_with_uppercase(self):
        block = _b("METHODS", index=0, font_size=18.0)
        ok, score = is_likely_heading_by_style(block, avg_font_size=12.0)
        assert ok is True
        assert score == 0.7  # 0.5(font>1.2*avg) + 0.2(isupper) = 0.7


class TestHardGuards:
    """Cover HARD GUARD 5 (figure/table captions), HARD GUARD 7 (numbered sentences)."""

    def test_figure_caption_rejected(self):
        blocks = [_b("Figure 1. This is a caption", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_fig_abbreviation_rejected(self):
        blocks = [_b("Fig. 2. Results over time", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_table_caption_rejected(self):
        blocks = [_b("Table 1. Experimental data", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_tab_abbreviation_rejected(self):
        blocks = [_b("Tab. 3. Summary statistics", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_box_caption_rejected(self):
        blocks = [_b("Box 1. Key equations", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_numbered_sentence_with_comma_rejected(self):
        text = "1. Smith, J. This is a reference entry that is long enough to trigger the guard."
        blocks = [_b(text, index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_numbered_sentence_with_et_al_rejected(self):
        text = "2. Smith et al. This is a reference with multiple authors long enough."
        blocks = [_b(text, index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_numbered_not_sentence_allowed(self):
        blocks = [_b("1. Introduction", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is not None
        assert result["is_heading"] is True

    def test_numbered_short_remainder_not_rejected(self):
        text = "1. Smith, J."
        blocks = [_b(text, index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is not None

    def test_sentence_punctuation_without_numbering_rejected(self):
        blocks = [_b("This is a long sentence that ends with a period.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_multiple_sentences_rejected(self):
        blocks = [_b("First sentence. Second sentence here", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_pronoun_starter_rejected(self):
        blocks = [_b("We propose a new method for classification.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_this_paper_starter_rejected(self):
        blocks = [_b("This paper presents a novel approach.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_in_this_starter_rejected(self):
        blocks = [_b("In this section we describe the method.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_short_sentence_punctuation_allowed(self):
        # "References." (keyword + period, <=4 words) passes HARD GUARD 2
        blocks = [_b("References.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is not None

    def test_caption_starter_figure_rejected(self):
        blocks = [_b("Figure 1. Results.", index=0)]
        assert analyze_heading_candidate(blocks[0], blocks, 0) is None

    def test_caption_starter_fig_rejected(self):
        blocks = [_b("Fig. 2. Data.", index=0)]
        assert analyze_heading_candidate(blocks[0], blocks, 0) is None

    def test_caption_starter_table_rejected(self):
        blocks = [_b("Table 3. Comparison.", index=0)]
        assert analyze_heading_candidate(blocks[0], blocks, 0) is None

    def test_caption_starter_tab_rejected(self):
        blocks = [_b("Tab. 4. Metrics.", index=0)]
        assert analyze_heading_candidate(blocks[0], blocks, 0) is None

    def test_caption_starter_box_rejected(self):
        blocks = [_b("Box 1. Algorithm.", index=0)]
        assert analyze_heading_candidate(blocks[0], blocks, 0) is None

    def test_hard_guard_7_numbered_sentence_with_comma_rejected(self):
        # "1. Smith, J. Title of paper." — looks like reference entry
        blocks = [_b("1. Smith, J. A very long title that goes on and on.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_hard_guard_7_numbered_sentence_with_et_al_rejected(self):
        blocks = [_b("1. Smith et al. A very long title that goes on and on.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is None

    def test_numbered_sentence_short_allowed(self):
        # Short remainder even with comma passes (len <= 20)
        blocks = [_b("1. Q. A.", index=0)]
        result = analyze_heading_candidate(blocks[0], blocks, 0)
        assert result is not None


class TestAbstractSafetyGuard:
    """Cover abstract safety guard: recent abstract rejects non-keyword/non-numbered."""

    def test_recent_abstract_rejects_non_keyword(self):
        abstract = _b("Abstract", index=0, bold=True, font_size=14.0)
        body = _b("This is content after abstract that should not be a heading", index=1)
        blocks = [abstract, body]
        result = analyze_heading_candidate(body, blocks, 1)
        assert result is None

    def test_recent_abstract_allows_numbered(self):
        abstract = _b("Abstract", index=0, bold=True, font_size=14.0)
        numbered = _b("1. Introduction", index=1)
        blocks = [abstract, numbered]
        result = analyze_heading_candidate(numbered, blocks, 1)
        assert result is not None
        assert result["is_heading"] is True

    def test_recent_abstract_allows_keyword(self):
        abstract = _b("Abstract", index=0, bold=True, font_size=14.0)
        intro = _b("Introduction", index=1)
        blocks = [abstract, intro]
        result = analyze_heading_candidate(intro, blocks, 1)
        assert result is not None
        assert result["is_heading"] is True

    def test_other_keyword_breaks_abstract_loop(self):
        intro = _b("Introduction", index=0)
        body = _b("Some body text after introduction", index=1)
        blocks = [intro, body]
        result = analyze_heading_candidate(body, blocks, 1)
        assert result is None

    def test_numbered_block_breaks_abstract_loop(self):
        numbered = _b("1. Introduction", index=0)
        body = _b("Body text after numbered heading", index=1)
        blocks = [numbered, body]
        result = analyze_heading_candidate(body, blocks, 1)
        assert result is None


def _pad_blocks(block: Block, index: int) -> list:
    """Return a block list large enough to avoid IndexError in abstract lookback."""
    if index == 0:
        return [block]
    return [_b("", i, font_size=12.0) for i in range(index)] + [block]



class TestParserHints:
    """Cover parser_heading_hint branch in analyze_heading_candidate."""

    def test_potential_heading_hint_adds_confidence(self):
        style = TextStyle(font_size=14.0)
        block = Block(
            block_id="b0",
            text="SOME SECTION",
            index=0,
            block_type=BlockType.BODY,
            style=style,
            metadata={"potential_heading": True, "heading_level": 3},
        )
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0, avg_font_size=12.0)
        assert result is not None
        assert result["is_heading"] is True
        assert "Parser Heading Signal" in result["reasons"]
        assert result["level"] == 1

    def test_parser_heading_level_far_from_start(self):
        style = TextStyle(font_size=14.0, bold=True)
        block = Block(
            block_id="b5",
            text="Introduction",
            index=5,
            block_type=BlockType.BODY,
            style=style,
            metadata={"potential_heading": True, "heading_level": 3},
        )
        blocks = _pad_blocks(block, 5)
        result = analyze_heading_candidate(block, blocks, 5, avg_font_size=12.0)
        assert result is not None
        # keyword match, so level 2 override not applied. parser_level (3) used
        assert result["level"] == 3

    def test_no_metadata_no_crash(self):
        block = Block(
            block_id="b0",
            text="SOME SECTION",
            index=0,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=18.0, bold=True),
        )
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0, avg_font_size=12.0)
        assert result is not None
        assert result["is_heading"] is True

    def test_potential_heading_with_numbering(self):
        style = TextStyle(font_size=14.0)
        block = Block(
            block_id="b0",
            text="1.1 Results Overview",
            index=0,
            block_type=BlockType.BODY,
            style=style,
            metadata={"potential_heading": True, "heading_level": 2},
        )
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is not None
        assert result["level"] == 2  # from numbering, parser level not used
        assert "Parser Heading Signal" in result["reasons"]

    def test_metadata_not_dict_does_not_crash(self):
        block = Block(
            block_id="b0",
            text="Introduction",
            index=0,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=14.0),
        )
        block.metadata = "not_a_dict"  # type: ignore[assignment]
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is not None  # still works, parser hint just not added


class TestFallbackLogic:
    """Cover fallback logic: is_isolated is always False, so fallback never triggers."""

    def test_fallback_never_triggers_returns_none(self):
        block = _b("Short Title Case Text", index=0)
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is None  # style_score=0, confidence=0

    def test_fallback_bypassed_by_numbering(self):
        block = _b("1. Introduction", index=0)
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is not None
        assert result["has_numbering"] is True

    def test_fallback_isolated_title_case_triggers(self):
        empty = _b("", index=0)
        block = _b("Short Title Case", index=1)
        empty2 = _b("", index=2)
        blocks = [empty, block, empty2]
        result = analyze_heading_candidate(block, blocks, 1)
        assert result is not None
        assert "Fallback: Short, Isolated, Title Case" in result["reasons"]
        assert result["confidence"] > 0


class TestLevelInference:
    """Cover infer_heading_level and the extra level logic in analyze_heading_candidate."""

    def test_infer_level_keyword(self):
        assert infer_heading_level(_b("Introduction")) == 1

    def test_infer_level_numbering(self):
        assert infer_heading_level(_b("1.1 Background"), {"level": 2}) == 2

    def test_infer_level_numbering_capped_at_4(self):
        assert infer_heading_level(_b("1.2.3.4.5 Deep"), {"level": 5}) == 4

    def test_infer_level_default(self):
        assert infer_heading_level(_b("Custom Section")) == 1

    def test_infer_level_keyword_with_numbering_prefix(self):
        assert infer_heading_level(_b("1. Introduction")) == 1

    def test_default_level_2_for_unknown(self):
        block = _b("Custom Section", index=5, bold=True, font_size=12.0)
        result = analyze_heading_candidate(block, _pad_blocks(block, 5), 5)
        assert result is None  # 0.3(bold) < 0.5 threshold, no keyword/num/hint

    def test_near_start_promoted_to_level_1(self):
        block = Block(
            block_id="b3",
            text="MY CUSTOM SECTION",
            index=3,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=18.0, bold=True),
            metadata={"potential_heading": True, "heading_level": 2},
        )
        blocks = _pad_blocks(block, 3)
        result = analyze_heading_candidate(block, blocks, 3, avg_font_size=12.0)
        assert result is not None
        assert result["level"] == 1  # Promoted because block_index < 5

    def test_large_font_promoted_to_level_1(self):
        block = Block(
            block_id="b5",
            text="CUSTOM SECTION FAR",
            index=5,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=18.0, bold=True),
            metadata={"potential_heading": True, "heading_level": 2},
        )
        blocks = _pad_blocks(block, 5)
        result = analyze_heading_candidate(block, blocks, 5, avg_font_size=12.0)
        assert result is not None
        assert result["level"] == 1  # Promoted because style_score > 0.4 and font > avg

    def test_not_near_start_small_font_stays_level_2(self):
        block = Block(
            block_id="b5",
            text="SECTION",
            index=5,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=12.0, bold=True),
            metadata={"potential_heading": True, "heading_level": 2},
        )
        blocks = _pad_blocks(block, 5)
        result = analyze_heading_candidate(block, blocks, 5, avg_font_size=12.0)
        assert result is not None
        # style_score=0.3(bold) + 0.2(isupper) = 0.5, style_likely=True
        # confidence=0.45(parser)+0.5*0.4=0.65 >= 0.5, passes
        # font_size=12 NOT > avg=12, block_index=5>=5, so no promotion. Stays at 2
        assert result["level"] == 2

    def test_numbered_stays_at_numbering_level(self):
        nb = _b("1.1 Some custom sub-section", index=5)
        nr = analyze_heading_candidate(nb, _pad_blocks(nb, 5), 5)
        assert nr is not None
        assert nr["level"] == 2  # from numbering level

    def test_parser_heading_level_not_overridden_when_numbered(self):
        block = Block(
            block_id="b0",
            text="1.1 Sub Section",
            index=0,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=14.0),
            metadata={"potential_heading": True, "heading_level": 3},
        )
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is not None
        assert result["level"] == 2

    def test_parser_heading_level_not_overridden_when_keyword(self):
        block = Block(
            block_id="b0",
            text="Introduction",
            index=0,
            block_type=BlockType.BODY,
            style=TextStyle(font_size=14.0),
            metadata={"potential_heading": True, "heading_level": 2},
        )
        blocks = [block]
        result = analyze_heading_candidate(block, blocks, 0)
        assert result is not None
        # parser overrides infer (infer=1 -> parser=2), keyword prevents lv2 fallback
        assert result["level"] == 2


class TestGetCapitalizationRatioEdgeCases:
    """Cover remaining branches in get_capitalization_ratio."""

    def test_all_small_words(self):
        assert get_capitalization_ratio("a an the") == 1.0

    def test_mixed_capitalization(self):
        ratio = get_capitalization_ratio("Introduction Methods Results")
        assert ratio == 1.0

    def test_some_lowercase(self):
        ratio = get_capitalization_ratio("Introduction methods Results")
        assert ratio == 2.0 / 3.0

    def test_single_word(self):
        assert get_capitalization_ratio("Introduction") == 1.0
