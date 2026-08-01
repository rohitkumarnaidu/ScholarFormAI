# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest


@pytest.fixture
def scorer():
    from app.pipeline.generation.quality_scorer import QualityScorer
    return QualityScorer()


class TestNormalizeSections:
    def test_none(self, scorer):
        assert scorer._normalize_sections(None) == {}

    def test_empty(self, scorer):
        assert scorer._normalize_sections({}) == {}

    def test_sections_list(self, scorer):
        content = {"sections": [{"title": "Intro", "content": "Hello"}, {"title": "Methods", "content": "Steps"}]}
        result = scorer._normalize_sections(content)
        assert result == {"Intro": "Hello", "Methods": "Steps"}

    def test_sections_list_with_section_key(self, scorer):
        content = {"sections": [{"section": "Related Work", "content": "Survey"}]}
        result = scorer._normalize_sections(content)
        assert result == {"Related Work": "Survey"}

    def test_sections_list_empty_title_skipped(self, scorer):
        content = {"sections": [{"title": "", "content": "X"}, {"title": "Intro", "content": "Y"}]}
        result = scorer._normalize_sections(content)
        assert result == {"Intro": "Y"}

    def test_flat_dict(self, scorer):
        content = {"Intro": "Hello", "Methods": "Steps", "count": 5}
        result = scorer._normalize_sections(content)
        assert result == {"Intro": "Hello", "Methods": "Steps", "count": "5"}


class TestRequiredSections:
    def test_from_task_spec(self, scorer):
        result = scorer._required_sections({"sections": ["Intro", "Methods"]}, {})
        assert result == ["Intro", "Methods"]

    def test_fallback_to_map_keys(self, scorer):
        result = scorer._required_sections({}, {"Intro": "text", "Methods": "text"})
        assert result == ["Intro", "Methods"]

    def test_empty_sections_list(self, scorer):
        result = scorer._required_sections({"sections": []}, {})
        assert result == []

    def test_not_a_list(self, scorer):
        result = scorer._required_sections({"sections": "string"}, {"A": "text"})
        assert result == ["A"]

    def test_empty_map_and_no_spec(self, scorer):
        result = scorer._required_sections({}, {})
        assert result == []


class TestWordCount:
    def test_none(self, scorer):
        assert scorer._word_count(None) == 0

    def test_empty(self, scorer):
        assert scorer._word_count("") == 0

    def test_single(self, scorer):
        assert scorer._word_count("hello") == 1

    def test_multiple(self, scorer):
        assert scorer._word_count("a b c d") == 4


class TestCountCitations:
    def test_none(self, scorer):
        assert scorer._count_citations(None) == 0

    def test_empty(self, scorer):
        assert scorer._count_citations("") == 0

    def test_bracket_number(self, scorer):
        assert scorer._count_citations("text [1, 2] and [3]") == 2

    def test_parenthetical_author_year(self, scorer):
        assert scorer._count_citations("(Smith, 2020)") == 1

    def test_bracket_author_year(self, scorer):
        assert scorer._count_citations("[Smith, 2020]") == 1

    def test_no_match(self, scorer):
        assert scorer._count_citations("plain text") == 0


class TestPercentage:
    def test_normal(self, scorer):
        assert scorer._percentage(3, 4) == 75.0

    def test_whole_zero(self, scorer):
        assert scorer._percentage(3, 0) == 0.0

    def test_part_zero(self, scorer):
        assert scorer._percentage(0, 4) == 0.0


class TestSectionBalance:
    def test_multiple_sections(self, scorer):
        sections = {"Intro": "word " * 50, "Methods": "word " * 100, "Conclusion": "word " * 150}
        result = scorer._section_balance(sections, ["Intro", "Methods", "Conclusion"])
        assert 50.0 <= result <= 100.0

    def test_empty_counts(self, scorer):
        assert scorer._section_balance({}, []) == 0.0

    def test_single_section(self, scorer):
        assert scorer._section_balance({"Intro": "some text"}, ["Intro"]) == 100.0

    def test_mean_zero(self, scorer):
        assert scorer._section_balance({"A": "", "B": ""}, ["A", "B"]) == 0.0

    def test_perfect_balance(self, scorer):
        sections = {"A": "word " * 100, "B": "word " * 100}
        result = scorer._section_balance(sections, ["A", "B"])
        assert result == 100.0

    def test_high_variance(self, scorer):
        sections = {"A": "word", "B": "word " * 10000}
        result = scorer._section_balance(sections, ["A", "B"])
        assert result >= 0.0


class TestCitationScore:
    def test_normal(self, scorer):
        result = scorer._citation_score(5, 5)
        assert result == 100.0

    def test_section_count_zero(self, scorer):
        assert scorer._citation_score(5, 0) == 0.0

    def test_one_section(self, scorer):
        result = scorer._citation_score(2, 1)
        assert result == 100.0

    def test_no_citations(self, scorer):
        assert scorer._citation_score(0, 5) == 0.0


class TestScore:
    def test_full_score(self, scorer):
        content = {
            "sections": [
                {"title": "Intro", "content": "word " * 100},
                {"title": "Methods", "content": "word " * 100 + " [1]"},
            ]
        }
        result = scorer.score(content=content, template="ieee", task_spec={"sections": ["Intro", "Methods"]})
        assert "template_compliance" in result
        assert "content_completeness" in result
        assert "citation_count" in result
        assert "word_count" in result
        assert "section_balance" in result
        assert "overall_score" in result
        assert result["citation_count"] >= 1
        assert result["word_count"] > 0

    def test_empty_content_dict(self, scorer):
        result = scorer.score(content={}, template="ieee", task_spec={})
        assert result["overall_score"] == 0.0

    def test_no_required_sections(self, scorer):
        content = {"Intro": "word " * 100}
        result = scorer.score(content=content, template="ieee", task_spec={})
        assert result["overall_score"] > 0
