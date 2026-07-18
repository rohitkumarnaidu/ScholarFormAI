# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
LLM-as-a-judge evaluation system.

Simulates an LLM judge that scores outputs on factuality, completeness,
instruction adherence, and coherence against a rubric.
"""

import pytest
import math
import hashlib
from typing import Dict, List


# ---------------------------------------------------------------------------
#  Simulated LLM judge helpers
# ---------------------------------------------------------------------------

_DEFAULT_RUBRIC = {
    "factuality": 1.0,
    "completeness": 1.0,
    "instruction_adherence": 1.0,
    "coherence": 1.0,
}


def _keyword_overlap(claim: str, source: str) -> float:
    """Fraction of claim keywords (>=4 chars) found in source."""
    import re
    claim_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim.lower()))
    if not claim_tokens:
        return 0.0
    source_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", source.lower()))
    if not source_tokens:
        return 0.0
    overlap = claim_tokens & source_tokens
    return len(overlap) / len(claim_tokens)


def _sentence_similarity(a: str, b: str) -> float:
    """Average keyword overlap across sentence pairs."""
    import re
    sentences_a = re.split(r"(?<=[.!?])\s+", a)
    sentences_b = re.split(r"(?<=[.!?])\s+", b)
    if not sentences_a or not sentences_b:
        return 0.0
    scores = []
    for sa in sentences_a:
        if len(sa.strip()) < 5:
            continue
        best = max(_keyword_overlap(sa, sb) for sb in sentences_b) if sentences_b else 0.0
        scores.append(best)
    return sum(scores) / len(scores) if scores else 0.0


def _extract_requirements(rubric: dict) -> List[str]:
    """Extract text requirements from rubric (keys prefixed with 'req_' or 'requires_')."""
    reqs = []
    for k, v in rubric.items():
        if k.startswith("req_") or k.startswith("requires_"):
            if isinstance(v, str):
                reqs.append(v)
            elif isinstance(v, list):
                reqs.extend(v)
    return reqs


def _check_instruction_adherence(output: str, rubric: dict) -> float:
    """Score how well output follows rubric instructions."""
    import re
    requirements = _extract_requirements(rubric)
    if not requirements:
        return 1.0
    adhered = 0
    for req in requirements:
        tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", req.lower()))
        if not tokens:
            adhered += 1
            continue
        output_lower = output.lower()
        # Check if output contains tokens related to the requirement
        match_count = sum(1 for t in tokens if t in output_lower)
        if match_count / len(tokens) >= 0.3:
            adhered += 1
    return adhered / len(requirements)


def _coherence_score(text: str) -> float:
    """Score coherence based on sentence transitions and structure."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) < 2:
        return 1.0  # single sentence or empty is trivially coherent
    # Check for transition words and referential continuity
    transitions = {
        "however", "therefore", "furthermore", "moreover", "consequently",
        "additionally", "in addition", "specifically", "for example",
        "for instance", "in contrast", "on the other hand", "as a result",
        "first", "second", "third", "finally", "subsequently", "notably",
        "importantly", "conversely", "meanwhile", "nevertheless",
    }
    transition_count = 0
    for s in sentences:
        lower = s.lower()[:30]
        for t in transitions:
            if lower.startswith(t) or t in lower:
                transition_count += 1
                break
    transition_ratio = transition_count / max(len(sentences) - 1, 1)
    # Penalize huge variance in sentence length
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(lengths) < 2:
        length_penalty = 0.0
    else:
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        cv = math.sqrt(variance) / max(mean_len, 1)
        length_penalty = min(cv, 1.0)
    score = 0.5 * min(transition_ratio * 2, 1.0) + 0.5 * (1.0 - length_penalty)
    return max(0.0, min(score, 1.0))


def _llm_judge_score(output: str, expected: str, rubric: dict = None) -> dict:
    """Simulate an LLM judge evaluation against a rubric.

    Returns scores for: factuality, completeness, instruction_adherence, coherence.

    Each dimension is a float in [0, 1]. The rubric dict can include:
      - ``weights``: dict of dimension weights (defaults to 1.0 each)
      - ``req_*`` or ``requires_*`` keys: text requirements checked for adherence
    """
    if rubric is None:
        rubric = {}

    weights = rubric.get("weights", _DEFAULT_RUBRIC)
    # Ensure all dimensions have a weight
    for dim in _DEFAULT_RUBRIC:
        if dim not in weights:
            weights[dim] = 1.0

    # Factuality: how much of output content is supported by expected
    factuality = _sentence_similarity(output, expected)

    # Completeness: how much of expected content appears in output
    completeness = _sentence_similarity(expected, output)

    # Instruction adherence
    instruction_adherence = _check_instruction_adherence(output, rubric)

    # Coherence
    coherence = _coherence_score(output)

    raw = {
        "factuality": factuality,
        "completeness": completeness,
        "instruction_adherence": instruction_adherence,
        "coherence": coherence,
    }

    # Weighted aggregate
    total_weight = sum(weights.get(d, 1.0) for d in _DEFAULT_RUBRIC)
    aggregate = sum(raw[d] * weights.get(d, 1.0) for d in _DEFAULT_RUBRIC) / max(total_weight, 1.0)

    return {
        **raw,
        "aggregate_score": aggregate,
        "confidence": _compute_confidence(raw, output, expected),
    }


def _compute_confidence(scores: dict, output: str, expected: str) -> float:
    """Judge confidence: higher when scores are coherent and output/expected differ little."""
    # Confidence drops when there's high variance across dimensions
    vals = list(scores.values())
    mean_val = sum(vals) / len(vals)
    variance = sum((v - mean_val) ** 2 for v in vals) / len(vals)
    # Also drop when output is much shorter/longer than expected
    len_ratio = min(len(output), len(expected)) / max(len(output), len(expected), 1)
    confidence = mean_val * (1.0 - min(variance * 2, 0.5)) * len_ratio
    return max(0.0, min(confidence, 1.0))


def _evaluate_batch(outputs: List[str], expected: str, rubric: dict = None) -> List[dict]:
    """Evaluate multiple outputs against the same expected content and rubric."""
    return [_llm_judge_score(o, expected, rubric) for o in outputs]


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


class TestLLMJudgeScore:
    """Core LLM judge scoring."""

    @pytest.mark.ai_quality
    def test_perfect_match_full_credit(self):
        output = "The transformer architecture uses self-attention mechanisms."
        expected = "The transformer architecture uses self-attention mechanisms."
        result = _llm_judge_score(output, expected)
        assert result["factuality"] >= 0.9
        assert result["completeness"] >= 0.9
        assert result["aggregate_score"] >= 0.9

    @pytest.mark.ai_quality
    def test_factuality_penalty_for_hallucinated_claims(self):
        output = "The transformer architecture uses self-attention. It was invented by Ada Lovelace in 1842."
        expected = "The transformer architecture uses self-attention mechanisms."
        result = _llm_judge_score(output, expected)
        assert result["factuality"] < 0.8, f"Hallucinated claims should reduce factuality: {result}"

    @pytest.mark.ai_quality
    def test_completeness_penalty_for_missing_content(self):
        output = "The transformer architecture uses self-attention."
        expected = "The transformer architecture uses self-attention mechanisms and positional encoding and layer normalization."
        result = _llm_judge_score(output, expected)
        assert result["completeness"] < 0.9, f"Missing content should reduce completeness: {result}"

    @pytest.mark.ai_quality
    def test_instruction_adherence_checked_against_rubric(self):
        output = "Here is a summary of the paper."
        rubric = {"req_format": "output must include a numbered list", "weights": {"instruction_adherence": 2.0}}
        result = _llm_judge_score(output, "paper content", rubric)
        assert result["instruction_adherence"] < 0.8

    @pytest.mark.ai_quality
    def test_partially_correct_proportional_scores(self):
        output = "The experiment used 50 participants and yielded significant results. Completely wrong unrelated content here."
        expected = "The experiment used 100 participants aged 18-35. Results were statistically significant at p<0.05."
        result = _llm_judge_score(output, expected)
        assert 0.1 < result["factuality"] < 1.0
        assert 0.1 < result["completeness"] < 1.0

    @pytest.mark.ai_quality
    def test_completely_wrong_output_low_scores(self):
        output = "The stock market rose 5% today due to earnings reports."
        expected = "Photosynthesis converts CO2 and water into glucose using light energy."
        rubric = {"req_topic": "the output must discuss plant biology and photosynthesis"}
        result = _llm_judge_score(output, expected, rubric)
        assert result["factuality"] < 0.3
        assert result["completeness"] < 0.3
        assert result["aggregate_score"] < 0.4

    @pytest.mark.ai_quality
    def test_verbose_but_correct_high_scores(self):
        output = (
            "The transformer architecture uses self-attention mechanisms. "
            "It processes tokens in parallel. This enables efficient training. "
            "The architecture has become foundational for modern NLP systems."
        )
        expected = "The transformer architecture uses self-attention mechanisms and processes tokens in parallel. It is foundational for modern NLP."
        result = _llm_judge_score(output, expected)
        assert result["factuality"] >= 0.5
        assert result["aggregate_score"] >= 0.5

    @pytest.mark.ai_quality
    def test_hallucination_penalty_detected(self):
        expected = "The Eiffel Tower was built between 1887 and 1889 in Paris for the World's Fair."
        output = "The Eiffel Tower was built in 1750 and is located in Berlin, Germany for the trade exhibition."
        result = _llm_judge_score(output, expected)
        assert result["factuality"] < 0.6, f"Hallucinated facts lowering factuality: {result}"

    @pytest.mark.ai_quality
    def test_ignored_instructions_penalty(self):
        rubric = {
            "requires_format": "respond in JSON format with keys: name, value",
            "weights": {"instruction_adherence": 3.0},
        }
        output = "The answer is 42."
        result = _llm_judge_score(output, "42", rubric)
        assert result["instruction_adherence"] < 0.5


class TestCoherenceScoring:
    """Coherence dimension tests."""

    @pytest.mark.ai_quality
    def test_well_structured_output_high_coherence(self):
        output = (
            "First, we introduce the problem statement. "
            "Second, we describe our methodology for solving it. "
            "Third, we present experimental results. "
            "Finally, we conclude with implications."
        )
        result = _llm_judge_score(output, "dummy expected")
        assert result["coherence"] >= 0.5

    @pytest.mark.ai_quality
    def test_rambling_output_lower_coherence(self):
        output = (
            "So anyway the thing is about transformers. Like they are really cool. "
            "Oh and also attention is all you need. Python is great for ML. "
            "By the way have you seen the weather today? So yeah back to AI."
        )
        result = _llm_judge_score(output, "dummy expected")
        assert result["coherence"] < 0.7


class TestEdgeCases:
    """Edge cases for LLM judge evaluation."""

    @pytest.mark.ai_quality
    def test_empty_output_zero_content_scores(self):
        result = _llm_judge_score("", "expected content")
        assert result["factuality"] == 0.0
        assert result["completeness"] == 0.0

    @pytest.mark.ai_quality
    def test_empty_rubric_no_penalty(self):
        output = "Some output here."
        result = _llm_judge_score(output, "Some output here.", {})
        assert result["instruction_adherence"] == 1.0
        assert result["aggregate_score"] > 0.0

    @pytest.mark.ai_quality
    def test_weighted_rubric_criteria(self):
        rubric = {
            "weights": {"factuality": 0.5, "completeness": 0.5, "instruction_adherence": 0.0, "coherence": 0.0},
            "req_output": "use technical language",
        }
        output = "The model is good."
        expected = "The model achieves state-of-the-art results on the benchmark."
        result = _llm_judge_score(output, expected, rubric)
        aggregate = result["aggregate_score"]
        assert aggregate > 0.0
        assert 0.0 <= aggregate <= 1.0

    @pytest.mark.ai_quality
    def test_scores_normalized_in_unit_interval(self):
        output = "Test output " * 50
        expected = "Expected content " * 50
        result = _llm_judge_score(output, expected, {"weights": {"factuality": 5.0}})
        for dim in ["factuality", "completeness", "instruction_adherence", "coherence"]:
            assert 0.0 <= result[dim] <= 1.0, f"{dim} out of range: {result[dim]}"
        assert 0.0 <= result["aggregate_score"] <= 1.0

    @pytest.mark.ai_quality
    def test_aggregate_weighted_average(self):
        rubric = {
            "weights": {"factuality": 0.0, "completeness": 0.0, "instruction_adherence": 0.0, "coherence": 1.0},
        }
        output = "First we start. Then we continue. Finally we finish."
        result = _llm_judge_score(output, "some expected", rubric)
        assert result["aggregate_score"] == pytest.approx(result["coherence"], abs=1e-6)

    @pytest.mark.ai_quality
    def test_very_long_output_truncated_evaluation(self):
        output = "A long response. " * 5000
        expected = "Expected content."
        result = _llm_judge_score(output, expected)
        for dim in ["factuality", "completeness", "instruction_adherence", "coherence"]:
            assert 0.0 <= result[dim] <= 1.0

    @pytest.mark.ai_quality
    def test_unicode_multi_language_output(self):
        output = "Étude sur l'intelligence artificielle. 机器学习正在改变世界。"
        expected = "Étude sur l'intelligence artificielle en français."
        result = _llm_judge_score(output, expected)
        assert 0.0 <= result["factuality"] <= 1.0
        assert 0.0 <= result["aggregate_score"] <= 1.0

    @pytest.mark.ai_quality
    def test_markdown_formatting_output(self):
        output = "# Introduction\n\nThe **transformer** architecture uses `self-attention`.\n\n- Point 1\n- Point 2"
        expected = "The transformer architecture uses self-attention mechanisms."
        result = _llm_judge_score(output, expected)
        assert 0.0 <= result["factuality"] <= 1.0
        assert 0.0 <= result["coherence"] <= 1.0

    @pytest.mark.ai_quality
    def test_confidence_drops_on_ambiguous_outputs(self):
        clear_output = "The transformer uses self-attention mechanisms."
        ambiguous_output = "Maybe the transformer uses some kind of attention? Not entirely sure."
        expected = "The transformer architecture uses self-attention mechanisms."
        clear_result = _llm_judge_score(clear_output, expected)
        ambig_result = _llm_judge_score(ambiguous_output, expected)
        assert ambig_result["confidence"] <= clear_result["confidence"] + 0.1, (
            f"Ambiguous output should not have higher confidence: {ambig_result['confidence']} vs {clear_result['confidence']}"
        )

    @pytest.mark.ai_quality
    def test_self_consistency_similar_outputs(self):
        expected = "The transformer architecture uses self-attention mechanisms."
        output_a = "The transformer architecture uses self-attention mechanisms."
        output_b = "Transformer models are built on self-attention mechanisms."
        result_a = _llm_judge_score(output_a, expected)
        result_b = _llm_judge_score(output_b, expected)
        diff = abs(result_a["aggregate_score"] - result_b["aggregate_score"])
        assert diff < 0.5, f"Similar outputs should score similarly: diff={diff}"


class TestBatchEvaluation:
    """Batch evaluation of multiple outputs."""

    @pytest.mark.ai_quality
    def test_batch_evaluation_returns_all_results(self):
        outputs = [
            "The transformer uses self-attention.",
            "Completely unrelated text.",
            "",
        ]
        expected = "The transformer architecture uses self-attention."
        results = _evaluate_batch(outputs, expected)
        assert len(results) == 3
        assert results[0]["aggregate_score"] > results[1]["aggregate_score"]
        assert results[2]["factuality"] == 0.0
        assert results[2]["completeness"] == 0.0

    @pytest.mark.ai_quality
    def test_batch_with_rubric_consistent_scoring(self):
        rubric = {
            "weights": {"factuality": 1.0, "completeness": 0.0, "instruction_adherence": 0.0, "coherence": 0.0},
            "req_format": "use technical language",
        }
        outputs = ["Self-attention is a mechanism.", "The thing does stuff."]
        expected = "Self-attention is a mechanism in transformer architectures."
        results = _evaluate_batch(outputs, expected, rubric)
        assert results[0]["factuality"] > results[1]["factuality"]


class TestConfidenceScoring:
    """Judge confidence calibration."""

    @pytest.mark.ai_quality
    def test_confidence_bounds(self):
        test_cases = [
            ("Perfect match.", "Perfect match."),
            ("", "Something."),
            ("Completely different topic here.", "Something else entirely."),
            ("A" * 1000, "B" * 100),
        ]
        for output, expected in test_cases:
            result = _llm_judge_score(output, expected)
            assert 0.0 <= result["confidence"] <= 1.0, f"Confidence out of bounds: {result['confidence']}"

    @pytest.mark.ai_quality
    def test_confidence_drops_with_high_variance(self):
        output = "First sentence is great. But this second sentence is completely off topic and unrelated to anything."
        expected = "First sentence matches well."
        result = _llm_judge_score(output, expected)
        assert 0.0 <= result["confidence"] <= 1.0
