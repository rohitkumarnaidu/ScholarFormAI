# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Unified AI quality evaluation suite.

Sections:
  1A — Response Quality Scoring  (~20 tests)
  1B — Output Quality Regression (~10 tests)
  1C — Confidence Calibration    (~ 8 tests)
"""

import pytest
import re


# ===================================================================
#  1A — Response Quality Scoring
# ===================================================================

class TestResponseQualityScoring:
    """Quality scoring using compute_quality_score and QualityScorer."""

    # ── compute_quality_score (quality_score_service) ──────────────

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_compute_quality_score_perfect(self):
        from app.services.quality_score_service import compute_quality_score

        data = {
            "metadata": {"abstract": "A novel approach to AI."},
            "references": [{"title": "Ref1"}, {"title": "Ref2"}, {"title": "Ref3"},
                           {"title": "Ref4"}, {"title": "Ref5"}],
            "headings": [{"text": "Introduction"}, {"text": "Methods"},
                         {"text": "Results"}, {"text": "Conclusion"}],
            "blocks": [
                {"block_type": "body", "section_name": "introduction",
                 "text": "Some intro text here."},
            ],
        }
        validation = {"errors": [], "warnings": [], "citation_target": 5}
        result = compute_quality_score(data, "ieee", validation)
        assert 0 <= result["overall_score"] <= 100
        assert result["template_compliance"] >= 50

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_compute_quality_score_empty(self):
        from app.services.quality_score_service import compute_quality_score
        result = compute_quality_score({}, "ieee", {})
        assert result["overall_score"] == 0
        assert result["template_compliance"] == 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_compute_quality_score_missing_sections_extracted(self):
        from app.services.quality_score_service import compute_quality_score
        data = {
            "metadata": {"abstract": "A."},
            "references": [],
            "headings": [],
            "blocks": [],
        }
        validation = {"errors": ["missing required section: introduction"]}
        result = compute_quality_score(data, "ieee", validation)
        assert "introduction" in str(result["missing_sections"]).lower()

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_compute_quality_score_citation_score(self):
        from app.services.quality_score_service import compute_quality_score
        data = {
            "metadata": {"abstract": "A."},
            "references": [{"title": "R1"}, {"title": "R2"}],
            "headings": [{"text": "Introduction"}],
            "blocks": [],
        }
        validation = {"errors": [], "citation_target": 4}
        result = compute_quality_score(data, "ieee", validation)
        assert result["citation_count"] == 2
        assert result["overall_score"] > 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_compute_quality_score_infer_provider(self):
        from app.services.quality_score_service import compute_quality_score
        data = {
            "metadata": {"abstract": "A."},
            "references": [],
            "headings": [{"text": "Introduction"}],
            "blocks": [],
        }
        validation = {"ai_semantic_audit": {"model": "gpt-4"}}
        result = compute_quality_score(data, "ieee", validation)
        assert result["llm_provider_used"] == "openai"

    # ── QualityScorer (quality_scorer.py) ──────────────────────────

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_empty_content(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        result = scorer.score({}, "ieee", {})
        assert result["overall_score"] == 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_word_count_zero(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("") == 0
        assert QualityScorer._word_count(None) == 0
        assert QualityScorer._word_count("   ") == 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_word_count_typical(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._word_count("hello world") == 2
        assert QualityScorer._word_count("a b c d e f") == 6

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_citation_count(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        text = "As shown in [1], [2, 3], and (Smith, 2023)..."
        assert QualityScorer._count_citations(text) >= 3

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_citation_count_empty(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._count_citations("") == 0
        assert QualityScorer._count_citations(None) == 0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_section_balance_equal(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = {"Intro": "word " * 100, "Methods": "word " * 100}
        balance = QualityScorer._section_balance(sections, ["Intro", "Methods"])
        assert balance >= 80.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_section_balance_unequal(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        sections = {"Intro": "x", "Methods": "y " * 500}
        balance = QualityScorer._section_balance(sections, ["Intro", "Methods"])
        assert balance < 80.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_percentage(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._percentage(3, 4) == 75.0
        assert QualityScorer._percentage(0, 5) == 0.0
        assert QualityScorer._percentage(5, 0) == 0.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_citation_score(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        assert QualityScorer._citation_score(5, 1) == 100.0
        assert QualityScorer._citation_score(0, 5) == 0.0
        assert QualityScorer._citation_score(0, 0) == 0.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_full_score_roundtrip(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {
            "sections": [
                {"title": "Intro", "content": "A " * 200},
                {"title": "Methods", "content": "B " * 200},
                {"title": "Results", "content": "C " * 200},
            ]
        }
        result = scorer.score(content, "ieee", {"sections": ["Intro", "Methods", "Results"]})
        assert result["template_compliance"] == 100.0
        assert result["content_completeness"] == 100.0
        assert result["section_balance"] >= 80.0
        assert 0 < result["overall_score"] <= 100

    # ── Edge cases ─────────────────────────────────────────────────

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_no_sections_input(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        result = scorer.score({"not_sections": "value"}, "ieee", {})
        assert isinstance(result["overall_score"], float)

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_quality_scorer_very_long_text(self):
        from app.pipeline.generation.quality_scorer import QualityScorer
        scorer = QualityScorer()
        content = {"sections": [{"title": "Intro", "content": "word " * 10000}]}
        result = scorer.score(content, "ieee", {"sections": ["Intro"]})
        assert result["word_count"] >= 9000


# ===================================================================
#  1B — Output Quality Regression Detection
# ===================================================================

GOLDEN_PROMPTS = [
    {
        "doc_type": "academic_paper",
        "metadata": {"title": "Test Paper", "authors": ["Alice"], "sections": [{"name": "Intro", "include": True}]},
        "options": {},
        "required_elements": ["Paper Details", "Instructions", "Return ONLY a valid JSON array",
                              "TITLE", "AUTHOR_INFO", "BODY"],
        "forbidden_elements": ["{unset_variable}", "self.", "__"],
    },
    {
        "doc_type": "resume",
        "metadata": {"name": "Bob", "skills": ["Python"], "education": [{"degree": "BSc", "institution": "MIT", "year": "2024"}]},
        "options": {},
        "required_elements": ["Candidate Details", "Return ONLY a valid JSON array",
                              "TITLE", "CONTACT_INFO", "SUMMARY"],
        "forbidden_elements": ["{unset_variable}", "self."],
    },
    {
        "doc_type": "report",
        "metadata": {"title": "Report", "authors": ["Charlie"], "sections": [{"name": "Exec Summary", "include": True}]},
        "options": {},
        "required_elements": ["Report Details", "Return ONLY a valid JSON array",
                              "TITLE", "AUTHOR_INFO", "ABSTRACT"],
        "forbidden_elements": ["{unset_variable}", "self."],
    },
]


class TestGoldenPromptVerification:
    """Golden prompt regression detection."""

    @pytest.mark.regression
    @pytest.mark.ai_quality
    @pytest.mark.parametrize("config", GOLDEN_PROMPTS, ids=[c["doc_type"] for c in GOLDEN_PROMPTS])
    def test_golden_prompt_has_required_elements(self, config):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build(config["doc_type"], config["metadata"], config["options"])
        for elem in config["required_elements"]:
            assert elem in prompt, f"Missing required element '{elem}' in {config['doc_type']}"

    @pytest.mark.regression
    @pytest.mark.ai_quality
    @pytest.mark.parametrize("config", GOLDEN_PROMPTS, ids=[c["doc_type"] for c in GOLDEN_PROMPTS])
    def test_golden_prompt_no_forbidden_elements(self, config):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build(config["doc_type"], config["metadata"], config["options"])
        for elem in config["forbidden_elements"]:
            assert elem not in prompt, f"Forbidden element '{elem}' found in {config['doc_type']}"

    @pytest.mark.regression
    @pytest.mark.ai_quality
    def test_golden_prompt_length_stable(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build("academic_paper", {"title": "Stable Test", "authors": ["A"]}, {})
        assert 500 < len(prompt) < 2000

    @pytest.mark.regression
    @pytest.mark.ai_quality
    def test_golden_section_prompt_consistent(self):
        from app.pipeline.generation.section_prompts import get_section_prompt
        ctx = {"task_spec": {"topic": "AI"}, "template_rules": [], "outline": []}
        p1 = get_section_prompt("Introduction", ctx)
        p2 = get_section_prompt("Introduction", ctx)
        assert p1 == p2

    @pytest.mark.regression
    @pytest.mark.ai_quality
    def test_golden_prompt_no_placeholder_bleed(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build("academic_paper", {"title": "Test"}, {})
        assert "%s" not in prompt
        assert "%(" not in prompt
        assert "{0}" not in prompt

    @pytest.mark.regression
    @pytest.mark.ai_quality
    def test_golden_output_has_no_contradictions(self):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        prompt = builder.build("academic_paper", {"title": "Test"}, {})
        sentences = re.split(r'(?<=[.!?])\s+', prompt)
        for s in sentences:
            lower = s.lower()
            assert not ("do not include" in lower and "include" in lower.replace("do not include", ""))


# ===================================================================
#  1C — Confidence Calibration
# ===================================================================

class TestConfidenceCalibration:
    """guard_llm_output confidence bounds and output quality."""

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_validator_guard_confidence_bound_low(self):
        from app.pipeline.safety.validator_guard import validate_output
        from pydantic import BaseModel, Field

        class ConfidenceSchema(BaseModel):
            score: float = Field(..., ge=0.0, le=1.0)

        decorated = validate_output(ConfidenceSchema)
        result = decorated(lambda: {"score": 0.2})()
        assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_validator_guard_confidence_bound_high(self):
        from app.pipeline.safety.validator_guard import validate_output
        from pydantic import BaseModel, Field

        class ConfidenceSchema(BaseModel):
            score: float = Field(..., ge=0.0, le=1.0)

        decorated = validate_output(ConfidenceSchema)
        result = decorated(lambda: {"score": 0.95})()
        assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_validator_guard_out_of_range_rejected(self):
        from app.pipeline.safety.validator_guard import validate_output
        from pydantic import BaseModel, Field

        class ConfidenceSchema(BaseModel):
            score: float = Field(..., ge=0.0, le=1.0)

        decorated = validate_output(ConfidenceSchema, error_return_value={"score": -1.0})
        result = decorated(lambda: {"score": 999.0})()
        assert result["score"] == -1.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_validator_guard_known_valid_high_confidence(self):
        from app.pipeline.safety.validator_guard import validate_output
        from pydantic import BaseModel, Field

        class OutputSchema(BaseModel):
            text: str = Field(..., min_length=1)
            quality: float = Field(..., ge=0.0, le=1.0)

        decorated = validate_output(OutputSchema)
        result = decorated(lambda: {"text": "Valid output", "quality": 0.85})()
        assert result["text"] == "Valid output"
        assert result["quality"] == 0.85

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_guard_llm_output_confidence_bounds(self):
        from app.pipeline.safety.llm_validator import guard_llm_output
        from pydantic import BaseModel, Field

        class OutSchema(BaseModel):
            value: float = Field(..., ge=0.0, le=1.0)

        @guard_llm_output(schema=OutSchema, error_return_value={"value": -1.0})
        def high_conf():
            return {"value": 0.99}

        @guard_llm_output(schema=OutSchema, error_return_value={"value": -1.0})
        def low_conf():
            return {"value": 0.01}

        assert high_conf()["value"] == 0.99
        assert 0.0 <= low_conf()["value"] <= 1.0

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_guard_llm_output_invalid_output_detected(self):
        from app.pipeline.safety.llm_validator import guard_llm_output
        from pydantic import BaseModel, Field

        class OutSchema(BaseModel):
            text: str = Field(..., min_length=1)

        @guard_llm_output(schema=OutSchema, error_return_value={"text": "FALLBACK"})
        def bad_output():
            return {"wrong_key": "injection"}

        result = bad_output()
        assert result["text"] == "FALLBACK"

    @pytest.mark.unit
    @pytest.mark.ai_quality
    def test_guard_llm_output_missing_required_field(self):
        from app.pipeline.safety.llm_validator import guard_llm_output
        from pydantic import BaseModel

        class RequiredSchema(BaseModel):
            required_field: str

        @guard_llm_output(schema=RequiredSchema, error_return_value={"required_field": "error"})
        def missing():
            return {"optional_field": "value"}

        result = missing()
        assert result["required_field"] == "error"
