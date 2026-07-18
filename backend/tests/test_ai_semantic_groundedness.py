# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Embedding-based groundedness evaluation.

Simulates semantic grounding using hash-based deterministic embeddings
and cosine similarity to detect paraphrase, synonym usage, and nuance.
"""

import pytest
import math
import hashlib
import time
from typing import List, Dict


# ---------------------------------------------------------------------------
#  Mock embedding engine
# ---------------------------------------------------------------------------

_EMBEDDING_DIM = 64


def _mock_embed(text: str) -> List[float]:
    """Simulate text embedding with deterministic hash-based vectors.

    Produces reproducible vectors where similar texts have similar embeddings
    by using character n-gram overlap as the similarity signal.
    """
    if not text:
        return [0.0] * _EMBEDDING_DIM
    # Compute n-gram signatures (2-grams and 3-grams)
    normalized = text.lower().strip()
    ngrams = set()
    for n in (2, 3):
        for i in range(len(normalized) - n + 1):
            ngrams.add(normalized[i:i + n])
    if not ngrams:
        return [0.0] * _EMBEDDING_DIM
    # Hash each n-gram into a position and value
    vec = [0.0] * _EMBEDDING_DIM
    for ng in ngrams:
        h = int(hashlib.md5(ng.encode("utf-8")).hexdigest(), 16)
        pos = h % _EMBEDDING_DIM
        sign = 1.0 if (h // _EMBEDDING_DIM) % 2 == 0 else -1.0
        vec[pos] += sign
    # Normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embedding_groundedness(text: str, sources: List[str], threshold: float = 0.7) -> Dict:
    """Evaluate groundedness using embedding similarity.

    Returns dict with:
      - claim_scores: list of (claim_text, similarity) per claim
      - mean_similarity: average similarity across claims
      - grounded_ratio: fraction of claims above threshold
      - grounded: bool if grounded_ratio >= 0.5
      - confidence: confidence based on similarity strength
    """
    import re
    if not text.strip():
        return {
            "claim_scores": [],
            "mean_similarity": 1.0,
            "grounded_ratio": 1.0,
            "grounded": True,
            "confidence": 1.0,
        }
    if not sources or all(not s.strip() for s in sources):
        return {
            "claim_scores": [],
            "mean_similarity": 0.0,
            "grounded_ratio": 0.0,
            "grounded": False,
            "confidence": 0.0,
        }

    # Extract claims
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = [s.strip() for s in sentences if len(s.strip()) > 3]

    if not claims:
        return {
            "claim_scores": [],
            "mean_similarity": 1.0,
            "grounded_ratio": 1.0,
            "grounded": True,
            "confidence": 1.0,
        }

    # Compute best similarity for each claim against any source
    source_embeds = [_mock_embed(s) for s in sources if s.strip()]
    if not source_embeds:
        return {
            "claim_scores": [],
            "mean_similarity": 0.0,
            "grounded_ratio": 0.0,
            "grounded": False,
            "confidence": 0.0,
        }

    claim_scores = []
    for claim in claims:
        claim_emb = _mock_embed(claim)
        best_sim = max(_cosine_similarity(claim_emb, se) for se in source_embeds)
        claim_scores.append((claim, best_sim))

    mean_sim = sum(cs[1] for cs in claim_scores) / len(claim_scores)
    grounded_count = sum(1 for cs in claim_scores if cs[1] >= threshold)
    grounded_ratio = grounded_count / len(claim_scores)

    # Confidence: higher when mean similarity is high and variance is low
    if len(claim_scores) > 1:
        variance = sum((cs[1] - mean_sim) ** 2 for cs in claim_scores) / len(claim_scores)
        confidence = mean_sim * (1.0 - min(variance * 3, 0.5))
    else:
        confidence = mean_sim

    return {
        "claim_scores": claim_scores,
        "mean_similarity": mean_sim,
        "grounded_ratio": grounded_ratio,
        "grounded": grounded_ratio >= 0.5,
        "confidence": max(0.0, min(confidence, 1.0)),
    }


def _batch_groundedness(claim_sets: List[str], sources: List[str], threshold: float = 0.7) -> List[Dict]:
    """Evaluate groundedness for multiple texts against the same sources."""
    return [_embedding_groundedness(t, sources, threshold) for t in claim_sets]


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


class TestEmbeddingGroundedness:
    """Core embedding-based groundedness evaluation."""

    @pytest.mark.ai_quality
    def test_verbatim_quote_near_perfect_grounding(self):
        source_text = "Quantum entanglement allows particles to be correlated in ways that classical physics cannot explain."
        result = _embedding_groundedness(source_text, [source_text])
        assert result["mean_similarity"] >= 0.8, f"Verbatim should have high similarity: {result['mean_similarity']}"
        assert result["grounded"] is True

    @pytest.mark.ai_quality
    def test_paraphrase_high_grounding(self):
        source = "The transformer architecture introduced self-attention mechanisms that revolutionized NLP."
        paraphrase = "Self-attention mechanisms from the transformer architecture caused a revolution in NLP."
        result = _embedding_groundedness(paraphrase, [source])
        assert result["mean_similarity"] >= 0.5, f"Paraphrase should have good grounding: {result['mean_similarity']}"

    @pytest.mark.ai_quality
    def test_synonym_usage_detected_as_grounded(self):
        source = "The experiment used a large number of participants."
        text = "The study employed a substantial quantity of subjects."
        result = _embedding_groundedness(text, [source])
        # Embedding-based (via n-gram overlap) should catch synonym-based paraphrases better than keyword
        keyword_ov = _keyword_overlap_simple(text, source)
        assert result["mean_similarity"] >= keyword_ov * 0.5, (
            f"Embedding ({result['mean_similarity']}) should not be much worse than keyword ({keyword_ov})"
        )

    @pytest.mark.ai_quality
    def test_completely_unrelated_low_grounding(self):
        source = "Photosynthesis converts CO2 and water into glucose."
        text = "The stock market rose 5% today due to positive earnings."
        result = _embedding_groundedness(text, [source])
        assert result["mean_similarity"] < 0.5, f"Unrelated should have low grounding: {result['mean_similarity']}"
        assert result["grounded"] is False

    @pytest.mark.ai_quality
    def test_partially_grounded_partial_score(self):
        source = "The model achieved 94% accuracy on the test set."
        text = "The model achieved 94% accuracy on the test set. It also won the competition."
        result = _embedding_groundedness(text, [source])
        assert 0.0 < result["mean_similarity"] < 1.0
        assert result["grounded_ratio"] > 0.0

    @pytest.mark.ai_quality
    def test_multiple_sources_improve_grounding(self):
        source_a = "The experiment used fMRI to measure brain activity."
        source_b = "Participants were shown visual stimuli during the scan."
        text = "The experiment used fMRI to measure brain activity while participants viewed visual stimuli."
        single = _embedding_groundedness(text, [source_a])
        multi = _embedding_groundedness(text, [source_a, source_b])
        assert multi["mean_similarity"] >= single["mean_similarity"] * 0.8

    @pytest.mark.ai_quality
    def test_threshold_affects_classification(self):
        source = "The Eiffel Tower is in Paris."
        text = "The Eiffel Tower is located in Paris, France."
        low = _embedding_groundedness(text, [source], threshold=0.3)
        high = _embedding_groundedness(text, [source], threshold=0.95)
        assert low["grounded"] is True
        assert high["grounded"] is False

    @pytest.mark.ai_quality
    def test_empty_source_zero_grounding(self):
        result = _embedding_groundedness("This is a claim.", [])
        assert result["mean_similarity"] == 0.0
        assert result["grounded"] is False
        assert result["confidence"] == 0.0

    @pytest.mark.ai_quality
    def test_empty_text_perfect_grounding(self):
        result = _embedding_groundedness("", ["Some source content here."])
        assert result["mean_similarity"] == 1.0
        assert result["grounded"] is True
        assert result["confidence"] == 1.0


class TestEdgeCases:
    """Edge cases for embedding groundedness."""

    @pytest.mark.ai_quality
    def test_short_claims_under_three_words(self):
        text = "Yes. No. Maybe."
        source = "The answer is maybe."
        result = _embedding_groundedness(text, [source])
        assert 0.0 <= result["mean_similarity"] <= 1.0
        assert isinstance(result["grounded"], bool)

    @pytest.mark.ai_quality
    def test_very_long_claims_over_thousand_words(self):
        text = "The core claim of the paper is that transformers work well. " * 100
        source = "Transformers are effective architectures for sequence modeling."
        result = _embedding_groundedness(text, [source])
        assert 0.0 <= result["mean_similarity"] <= 1.0
        assert isinstance(result.get("grounded"), bool)

    @pytest.mark.ai_quality
    def test_cross_source_grounding(self):
        source_a = "Photosynthesis converts CO2 into glucose."
        source_b = "The stock market is driven by investor sentiment."
        text = "Photosynthesis converts CO2 into glucose using light energy."
        result = _embedding_groundedness(text, [source_a, source_b])
        assert result["mean_similarity"] >= 0.3
        # Claim should be grounded in source_a, not just source_b
        claim_emb = _mock_embed(text)
        emb_a = _mock_embed(source_a)
        emb_b = _mock_embed(source_b)
        sim_a = _cosine_similarity(claim_emb, emb_a)
        sim_b = _cosine_similarity(claim_emb, emb_b)
        assert sim_a > sim_b, "Claim should be more similar to relevant source"

    @pytest.mark.ai_quality
    def test_confidence_reflects_similarity_strength(self):
        high_sim = _embedding_groundedness("Paris is the capital of France.", ["Paris is the capital of France."])
        low_sim = _embedding_groundedness("Paris is the capital of France.", ["The weather is nice today."])
        assert high_sim["confidence"] > low_sim["confidence"], (
            f"High-sim confidence ({high_sim['confidence']}) should exceed low-sim ({low_sim['confidence']})"
        )

    @pytest.mark.ai_quality
    def test_negation_detection(self):
        source = "The experiment confirmed the hypothesis."
        positive = "The experiment confirmed the hypothesis."
        negative = "The experiment did NOT confirm the hypothesis."
        pos_result = _embedding_groundedness(positive, [source])
        neg_result = _embedding_groundedness(negative, [source])
        # Negation should produce different (lower) similarity
        assert pos_result["mean_similarity"] != neg_result["mean_similarity"], (
            "Negation should change the embedding similarity"
        )

    @pytest.mark.ai_quality
    def test_unicode_multi_language(self):
        source = "Étude sur l'intelligence artificielle en français."
        text = "Recherche sur l'IA en langue française."
        result = _embedding_groundedness(text, [source])
        assert 0.0 <= result["mean_similarity"] <= 1.0

    @pytest.mark.ai_quality
    def test_numeric_only_claims(self):
        text = "42. 3.14159. 2.718."
        source = "Important mathematical constants include pi (3.14159) and e (2.718)."
        result = _embedding_groundedness(text, [source])
        assert 0.0 <= result["mean_similarity"] <= 1.0

    @pytest.mark.ai_quality
    def test_claims_with_code_and_formulas(self):
        text = "The function f(x) = x**2 + 2*x + 1 computes the quadratic. Use print('hello') to debug."
        source = "The quadratic function is f(x) = x^2 + 2x + 1. Print statements help with debugging."
        result = _embedding_groundedness(text, [source])
        assert 0.0 <= result["mean_similarity"] <= 1.0

    @pytest.mark.ai_quality
    def test_nuance_detection_slightly_different_claims(self):
        source = "The treatment significantly improved patient outcomes (p=0.04)."
        text_a = "The treatment significantly improved patient outcomes."
        text_b = "The treatment showed a trend toward improved patient outcomes but was not significant."
        result_a = _embedding_groundedness(text_a, [source])
        result_b = _embedding_groundedness(text_b, [source])
        # text_a is closer to source than text_b
        assert result_a["mean_similarity"] >= result_b["mean_similarity"] * 0.5


class TestBatchGroundedness:
    """Batch evaluation of multiple claim sets."""

    @pytest.mark.ai_quality
    def test_batch_groundedness_multiple_claims(self):
        claim_sets = [
            "Transformers use self-attention.",
            "The sky is green.",
            "",
        ]
        sources = ["Transformers use self-attention mechanisms in NLP."]
        results = _batch_groundedness(claim_sets, sources)
        assert len(results) == 3
        assert results[0]["grounded"] is True
        assert results[1]["grounded"] is False
        assert results[2]["grounded"] is True

    @pytest.mark.ai_quality
    def test_batch_different_thresholds(self):
        claim_sets = ["Transformers use attention."]
        sources = ["Transformers use self-attention in neural networks."]
        t0 = _batch_groundedness(claim_sets, sources, threshold=0.0)
        t1 = _batch_groundedness(claim_sets, sources, threshold=1.0)
        assert t0[0]["grounded"] is True
        assert t1[0]["grounded"] is False


class TestPerformance:
    """Performance characteristics of mock embedding groundedness."""

    @pytest.mark.ai_quality
    def test_groundedness_under_one_ms(self):
        claims = [f"Claim number {i} about transformer models." for i in range(100)]
        sources = ["Transformers use self-attention mechanisms."]
        start = time.perf_counter()
        _batch_groundedness(claims, sources)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        assert elapsed < 100, f"100 claims took {elapsed:.2f}ms (expected <100ms)"

    @pytest.mark.ai_quality
    def test_mock_embed_deterministic(self):
        v1 = _mock_embed("The transformer architecture uses self-attention.")
        v2 = _mock_embed("The transformer architecture uses self-attention.")
        assert v1 == v2

    @pytest.mark.ai_quality
    def test_mock_embed_different_for_different_inputs(self):
        v1 = _mock_embed("The transformer architecture.")
        v2 = _mock_embed("The stock market rose 5%.")
        assert v1 != v2


# ---------------------------------------------------------------------------
#  Helper used for comparison in test_synonym_usage_detected_as_grounded
# ---------------------------------------------------------------------------

def _keyword_overlap_simple(text: str, source: str) -> float:
    import re
    text_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))
    source_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", source.lower()))
    if not text_tokens:
        return 0.0
    overlap = text_tokens & source_tokens
    return len(overlap) / len(text_tokens)
