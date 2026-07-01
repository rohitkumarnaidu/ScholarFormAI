import pytest


class TestQualityScorerScore:
    def test_basic_score(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {
            "sections": [
                {"title": "Introduction", "content": "word " * 150},
                {"title": "Methods", "content": "word " * 150},
            ]
        }
        result = scorer.score(content, "ieee", {"sections": ["Introduction", "Methods"]})
        assert result["template_compliance"] == 100.0
        assert result["content_completeness"] == 100.0
        assert result["word_count"] > 0
        assert 0 <= result["overall_score"] <= 100

    def test_empty_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        result = scorer.score({}, "ieee", {})
        assert result["overall_score"] == 0.0
        assert result["template_compliance"] == 0.0

    def test_partial_sections(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {"sections": [{"title": "Intro", "content": "A" * 100}]}
        result = scorer.score(content, "ieee", {"sections": ["Intro", "Missing"]})
        assert result["template_compliance"] == 50.0

    def test_citations_counted(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {
            "sections": [
                {"title": "Intro", "content": "Prior work [1], [2] and (Smith, 2020) show..."}
            ]
        }
        result = scorer.score(content, "ieee", {"sections": ["Intro"]})
        assert result["citation_count"] >= 2


class TestNormalizeSections:
    def test_empty(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._normalize_sections({}) == {}

    def test_sections_list(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        result = QualityScorer._normalize_sections({
            "sections": [
                {"title": "Intro", "content": "Hello"},
                {"section": "Methods", "content": "World"},
                {"title": "", "content": "Empty"},
            ]
        })
        assert result == {"Intro": "Hello", "Methods": "World"}

    def test_dict_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        result = QualityScorer._normalize_sections({"Intro": "Hello", "Methods": "World"})
        assert result == {"Intro": "Hello", "Methods": "World"}

    def test_non_string_values(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        result = QualityScorer._normalize_sections({"Intro": 123})
        assert result == {"Intro": "123"}


class TestRequiredSections:
    def test_from_task_spec(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = QualityScorer._required_sections({"sections": ["A", "B"]}, {"A": ""})
        assert sections == ["A", "B"]

    def test_fallback_to_sections_map(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = QualityScorer._required_sections({}, {"A": "", "B": ""})
        assert sections == ["A", "B"]

    def test_empty(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = QualityScorer._required_sections({}, {})
        assert sections == []


class TestWordCount:
    def test_basic(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("one two three") == 3

    def test_empty(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("") == 0

    def test_none(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("   ") == 0


class TestCountCitations:
    def test_bracket_pattern(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._count_citations("See [1], [2, 3]") == 2

    def test_parenthetical_pattern(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._count_citations("(Smith, 2020)") == 1

    def test_mixed(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        text = "[1] and (Doe, 2019) and [Smith, 2020]"
        assert QualityScorer._count_citations(text) >= 2

    def test_no_citations(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._count_citations("Plain text without references") == 0


class TestSectionBalance:
    def test_balanced(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        balance = QualityScorer._section_balance({"A": "x " * 50, "B": "y " * 50}, ["A", "B"])
        assert balance == 100.0

    def test_imbalanced(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        balance = QualityScorer._section_balance({"A": "x", "B": "y " * 200}, ["A", "B"])
        assert balance < 100.0

    def test_single_section(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        balance = QualityScorer._section_balance({"A": "text"}, ["A"])
        assert balance == 100.0

    def test_empty(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._section_balance({}, []) == 0.0


class TestCitationScore:
    def test_two_per_section(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._citation_score(4, 2) == 100.0

    def test_no_citations(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._citation_score(0, 5) == 0.0

    def test_no_sections(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._citation_score(5, 0) == 0.0


class TestPercentage:
    def test_half(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._percentage(3, 6) == 50.0

    def test_zero_whole(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._percentage(5, 0) == 0.0
