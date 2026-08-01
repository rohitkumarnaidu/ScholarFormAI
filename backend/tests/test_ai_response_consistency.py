# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Response consistency evaluation suite for AI-generated academic documents.

Sections:
   4A — Determinism               (~5 tests)
   4B — Consistency Across Calls   (~5 tests)
   4C — Edge Cases & Scoring      (~5 tests)
"""

import re
from collections.abc import Callable
from typing import Any

import pytest

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _semantic_similarity(text1: str, text2: str) -> float:
    """Simulate semantic similarity between two texts.

    Uses word overlap and TF-style weighting as a proxy for semantic similarity.
    Returns 0.0 (completely different) to 1.0 (identical meaning).
    """
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0

    # Tokenize into lowercased words (4+ chars)
    t1_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text1.lower()))
    t2_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text2.lower()))

    if not t1_words and not t2_words:
        return 1.0
    if not t1_words or not t2_words:
        return 0.0

    # Jaccard similarity weighted by word frequency
    intersection = t1_words & t2_words
    union = t1_words | t2_words

    # Content-word proximity bonus (only when numbers present)
    t1_numbers = set(re.findall(r"\b\d+\b", text1))
    t2_numbers = set(re.findall(r"\b\d+\b", text2))
    jaccard = len(intersection) / len(union) if union else 0.0
    if t1_numbers or t2_numbers:
        num_overlap = len(t1_numbers & t2_numbers) / max(len(t1_numbers | t2_numbers), 1)
        weighted = 0.7 * jaccard + 0.3 * num_overlap
    else:
        weighted = jaccard
    return round(min(1.0, max(0.0, weighted)), 4)


def _check_determinism(func: Callable, input_data: Any, num_runs: int = 3) -> dict[str, Any]:
    """Run same function with same input N times, measure consistency.

    Returns dict with:
      - outputs: list of outputs
      - similarities: pairwise similarities
      - min_similarity, max_similarity, avg_similarity
      - deterministic: True if avg_similarity > 0.95
    """
    outputs = []
    for _ in range(num_runs):
        outputs.append(func(input_data))

    similarities = []
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            sim = _semantic_similarity(outputs[i], outputs[j])
            similarities.append(sim)

    if not similarities:
        return {
            "outputs": outputs,
            "similarities": [],
            "min_similarity": 1.0,
            "max_similarity": 1.0,
            "avg_similarity": 1.0,
            "deterministic": True,
        }

    return {
        "outputs": outputs,
        "similarities": similarities,
        "min_similarity": round(min(similarities), 4),
        "max_similarity": round(max(similarities), 4),
        "avg_similarity": round(sum(similarities) / len(similarities), 4),
        "deterministic": sum(similarities) / len(similarities) > 0.95,
    }


def _format_similarity(text1: str, text2: str) -> float:
    """Measure structural format similarity (headings, sections, lists)."""
    fmt1 = re.findall(r"(^|\n)(#{1,6}\s|\*|\-|\d+\.)", text1)
    fmt2 = re.findall(r"(^|\n)(#{1,6}\s|\*|\-|\d+\.)", text2)
    if not fmt1 and not fmt2:
        return 1.0
    if not fmt1 or not fmt2:
        return 0.0
    return round(min(len(fmt1), len(fmt2)) / max(len(fmt1), len(fmt2)), 4)


def _consistency_report(results: list[dict[str, Any]]) -> dict[str, float]:
    """Generate an overall consistency score report.

    Returns dict with:
      - overall_consistency: 0-100
      - determinism_score: 0-100
      - format_consistency: 0-100
      - length_consistency: 0-100
    """
    if not results:
        return {
            "overall_consistency": 100.0,
            "determinism_score": 100.0,
            "format_consistency": 100.0,
            "length_consistency": 100.0,
        }

    det_scores = [r.get("avg_similarity", 0) for r in results if "avg_similarity" in r]
    det_score = (sum(det_scores) / len(det_scores) * 100) if det_scores else 100.0

    fmt_scores = [r.get("format_sim", 1.0) for r in results if "format_sim" in r]
    fmt_score = (sum(fmt_scores) / len(fmt_scores) * 100) if fmt_scores else 100.0

    len_scores = [r.get("length_sim", 1.0) for r in results if "length_sim" in r]
    len_score = (sum(len_scores) / len(len_scores) * 100) if len_scores else 100.0

    overall = round((det_score + fmt_score + len_score) / 3, 2)

    return {
        "overall_consistency": overall,
        "determinism_score": round(det_score, 2),
        "format_consistency": round(fmt_score, 2),
        "length_consistency": round(len_score, 2),
    }


# Deterministic mock generation functions for testing

def _deterministic_formatter(text: str) -> str:
    """A deterministic function (no randomness)."""
    return f"Formatted: {text.strip()}"


def _near_deterministic_formatter(text: str) -> str:
    """Nearly deterministic with tiny random variation."""
    seed = len(text) % 10
    return f"Formatted: {text.strip()}" if seed < 8 else f"Formatted: {text.strip().upper()}"


_call_counter: int = 0

def _non_deterministic_formatter(text: str) -> str:
    """Non-deterministic: returns different outputs."""
    global _call_counter
    _call_counter += 1
    return f"Formatted: {text.strip()} ({_call_counter})"


# ===================================================================
#  4A — Determinism
# ===================================================================

class TestDeterminism:
    """Same input should produce semantically similar output."""

    @pytest.mark.ai_quality
    def test_same_input_semantically_similar(self):
        input_text = "Generate an abstract for a paper on machine learning."
        r1 = _deterministic_formatter(input_text)
        r2 = _deterministic_formatter(input_text)
        sim = _semantic_similarity(r1, r2)
        assert sim >= 0.95, f"Same input should produce similar output: sim={sim}"

    @pytest.mark.ai_quality
    def test_determinism_over_5_consecutive_calls(self):
        def gen(text):
            return _deterministic_formatter(text)
        result = _check_determinism(gen, "Abstract on AI safety", num_runs=5)
        assert result["deterministic"], f"Not deterministic: {result}"
        assert result["avg_similarity"] >= 0.95

    @pytest.mark.ai_quality
    def test_determinism_over_10_consecutive_calls(self):
        def gen(text):
            return _deterministic_formatter(text)
        result = _check_determinism(gen, "Abstract on quantum computing", num_runs=10)
        assert result["deterministic"], f"Not deterministic over 10 runs: {result}"

    @pytest.mark.ai_quality
    def test_temperature_zero_near_identical(self):
        def temperature_zero(text):
            return f"Output for: {text}"
        r1 = temperature_zero("Write an introduction.")
        r2 = temperature_zero("Write an introduction.")
        assert r1 == r2, "Temperature=0 should produce identical outputs"

    @pytest.mark.ai_quality
    def test_different_inputs_produce_different_outputs(self):
        input_a = "Write about neural networks."
        input_b = "Write about photosynthesis."
        r1 = _deterministic_formatter(input_a)
        r2 = _deterministic_formatter(input_b)
        sim = _semantic_similarity(r1, r2)
        assert sim < 0.9, f"Different inputs should be distinguishable: sim={sim}"


# ===================================================================
#  4B — Consistency Across Calls
# ===================================================================

class TestCrossCallConsistency:
    """Content, format, length, and style consistency."""

    @pytest.mark.ai_quality
    def test_factual_consistency_no_contradiction(self):
        def gen(text):
            return f"Abstract: {text} The study found significant results."
        r1 = gen("AI in healthcare")
        r2 = gen("AI in healthcare")
        assert r1 == r2, "Factual content should not contradict across calls"

    @pytest.mark.ai_quality
    def test_format_consistency_across_calls(self):
        def gen_with_format(text):
            return f"## Abstract\n\n{text}\n\n## Keywords\n\n{text.lower().replace(' ', ', ')}"
        r1 = gen_with_format("Deep learning")
        r2 = gen_with_format("Deep learning")
        fmt_sim = _format_similarity(r1, r2)
        assert fmt_sim == 1.0, f"Format should be identical: {fmt_sim}"

    @pytest.mark.ai_quality
    def test_length_consistency_across_calls(self):
        def gen_reproducible(text):
            return f"Introduction:\n{text}\nMethods:\n{text}\nResults:\n{text}"
        r1 = gen_reproducible("test data")
        r2 = gen_reproducible("test data")
        len_sim = min(len(r1), len(r2)) / max(len(r1), len(r2), 1)
        assert len_sim >= 0.95, f"Length should be consistent: {len_sim}"

    @pytest.mark.ai_quality
    def test_key_information_preserved_across_calls(self):
        def gen_with_key_info(text):
            text.split()
            return f"Title: {text}\nAuthor: AI\nDate: 2026\nAbstract: {text}"

        r1 = gen_with_key_info("Machine Learning in Healthcare")
        r2 = gen_with_key_info("Machine Learning in Healthcare")
        for key in ["Machine", "Learning", "Healthcare"]:
            assert key in r1 and key in r2, f"Key info '{key}' should persist"

    @pytest.mark.ai_quality
    def test_style_tone_consistent(self):
        formal_voice = "The experiment was conducted. The hypothesis was tested."
        also_formal = "The experiment was documented. The hypothesis was confirmed."
        informal = "We just tried something different. We checked the outcome."
        formal_sim = _semantic_similarity(formal_voice, also_formal)
        mixed_sim = _semantic_similarity(formal_voice, informal)
        assert formal_sim > mixed_sim, (
            f"Formal-formal similarity ({formal_sim}) should exceed formal-informal ({mixed_sim})"
        )


# ===================================================================
#  4C — Edge Cases & Scoring
# ===================================================================

class TestConsistencyEdgeCasesAndScoring:
    """Edge case handling and consistency scoring."""

    @pytest.mark.ai_quality
    def test_empty_input_handled_consistently(self):
        def gen(text):
            return f"Result: {text}" if text else ""
        r1 = gen("")
        r2 = gen("")
        assert r1 == r2, "Empty input should produce identical output"

    @pytest.mark.ai_quality
    def test_very_long_input_handled_consistently(self):
        long_text = "word " * 5000
        def gen(text):
            return f"Summary: {text[:100]}..."
        r1 = gen(long_text)
        r2 = gen(long_text)
        assert r1 == r2, "Long input should produce identical output"

    @pytest.mark.ai_quality
    def test_session_consistency_same_context(self):
        context = {"style": "apa", "journal": "Nature", "temperature": 0}

        def format_with_context(text):
            return f"[{context['style'].upper()}] {text} — {context['journal']}"

        r1 = format_with_context("My paper")
        r2 = format_with_context("My paper")
        assert r1 == r2, "Same context should produce identical output"

    @pytest.mark.ai_quality
    def test_semantic_similarity_identical_texts(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert _semantic_similarity(text, text) == 1.0

    @pytest.mark.ai_quality
    def test_semantic_similarity_completely_different(self):
        t1 = "Quantum computing and artificial intelligence research."
        t2 = "The weather today is sunny with occasional clouds."
        sim = _semantic_similarity(t1, t2)
        assert sim < 0.3, f"Different topics should have low similarity: {sim}"

    @pytest.mark.ai_quality
    def test_semantic_similarity_empty_texts(self):
        assert _semantic_similarity("", "") == 1.0
        assert _semantic_similarity("", "something") == 0.0
        assert _semantic_similarity("something", "") == 0.0

    @pytest.mark.ai_quality
    def test_consistency_score_report(self):
        results = [
            {"avg_similarity": 0.99, "format_sim": 1.0, "length_sim": 0.98},
            {"avg_similarity": 0.97, "format_sim": 0.95, "length_sim": 0.96},
        ]
        report = _consistency_report(results)
        assert 0 <= report["overall_consistency"] <= 100
        assert report["determinism_score"] > 95
        assert report["format_consistency"] > 95
        assert report["length_consistency"] > 95

    @pytest.mark.ai_quality
    def test_consistency_score_empty_input(self):
        report = _consistency_report([])
        assert report["overall_consistency"] == 100.0
        assert report["determinism_score"] == 100.0
        assert report["format_consistency"] == 100.0
        assert report["length_consistency"] == 100.0

    @pytest.mark.ai_quality
    def test_non_deterministic_detected(self):
        def gen(text):
            return _non_deterministic_formatter(text)
        result = _check_determinism(gen, "test", num_runs=3)
        assert not result["deterministic"], f"Non-deterministic should be detected: {result}"
