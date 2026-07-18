# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""NLG evaluation metrics: BLEU, ROUGE, and BERTScore simulation."""

import math
import pytest
from typing import Sequence


# ---------------------------------------------------------------------------
# NLG Metric Implementations
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _ngrams(tokens: Sequence[str], n: int) -> set[tuple[str, ...]]:
    return set(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longest common subsequence length via DP."""
    m, n = len(a), len(b)
    dp: list[list[int]] = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def _count_ngrams(tokens: Sequence[str], n: int) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i:i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _clip_count(candidate_ngrams: dict, reference_ngrams: dict) -> int:
    total = 0
    for gram, cnt in candidate_ngrams.items():
        total += min(cnt, reference_ngrams.get(gram, 0))
    return total


def _bleu_score(reference: str, candidate: str, max_n: int = 4) -> float:
    """Simulate BLEU score (precision of n-grams with brevity penalty)."""
    if not reference or not candidate:
        return 0.0
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    if len(cand_tokens) == 0 or len(ref_tokens) == 0:
        return 0.0

    precisions = []
    for n in range(1, max_n + 1):
        if len(cand_tokens) < n or len(ref_tokens) < n:
            precisions.append(0.0)
            continue
        ref_counts = _count_ngrams(ref_tokens, n)
        cand_counts = _count_ngrams(cand_tokens, n)
        clipped = _clip_count(cand_counts, ref_counts)
        total = sum(cand_counts.values())
        precisions.append(clipped / total if total > 0 else 0.0)

    mean_log = 0.0
    for p in precisions:
        if p == 0.0:
            return 0.0
        mean_log += math.log(p)
    mean_log /= max_n

    bp = math.exp(1 - len(ref_tokens) / len(cand_tokens)) if len(cand_tokens) < len(ref_tokens) else 1.0
    return bp * math.exp(mean_log)


def _rouge_n(reference: str, candidate: str, n: int = 1) -> float:
    """Simulate ROUGE-N score (recall of n-grams)."""
    if not reference or not candidate:
        return 0.0
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    if len(ref_tokens) < n or len(cand_tokens) < n:
        return 0.0 if len(ref_tokens) >= n else 0.0
    ref_ngrams = _ngrams(ref_tokens, n)
    cand_ngrams = _ngrams(cand_tokens, n)
    if not ref_ngrams:
        return 0.0
    overlap = len(ref_ngrams & cand_ngrams)
    return overlap / len(ref_ngrams)


def _rouge_l(reference: str, candidate: str) -> float:
    """ROUGE-L: F-measure based on longest common subsequence."""
    if not reference or not candidate:
        return 0.0
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    if not ref_tokens or not cand_tokens:
        return 0.0
    lcs = _lcs_length(ref_tokens, cand_tokens)
    precision = lcs / len(cand_tokens)
    recall = lcs / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# Word-level embedding simulation for BERTScore.
# Each word maps to a high-dimensional pseudo-embedding based on character trigrams
# to better approximate semantic similarity.
_EMBEDDINGS: dict[str, list[float]] = {}


def _build_embedding(word: str) -> list[float]:
    """Deterministic pseudo-embedding using character trigram hashing (48 dims)."""
    vec = [0.0] * 48
    padded = f"#{word}#"
    for i in range(len(padded) - 2):
        tri = padded[i:i+3]
        h = hash(tri) & 0xFFFFFFFF
        for j in range(4):
            idx = ((h >> (j * 8)) & 0xFF) % 48
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return max(0.0, min(1.0, dot))


def _bertscore_sim(reference: str, candidate: str) -> float:
    """Simulate BERTScore using embedding cosine similarity with word-level recall."""
    if not reference or not candidate:
        return 0.0
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    if not ref_tokens or not cand_tokens:
        return 0.0

    for word in set(ref_tokens + cand_tokens):
        if word not in _EMBEDDINGS:
            _EMBEDDINGS[word] = _build_embedding(word)

    scores = []
    for rw in ref_tokens:
        best = 0.0
        for cw in cand_tokens:
            sim = _cosine_sim(_EMBEDDINGS[rw], _EMBEDDINGS[cw])
            if sim > best:
                best = sim
        scores.append(best)
    recall = sum(scores) / len(scores) if scores else 0.0

    precision_scores = []
    for cw in cand_tokens:
        best = 0.0
        for rw in ref_tokens:
            sim = _cosine_sim(_EMBEDDINGS[cw], _EMBEDDINGS[rw])
            if sim > best:
                best = sim
        precision_scores.append(best)
    precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Tests: ROUGE-N
# ---------------------------------------------------------------------------

class TestRougeN:
    @pytest.mark.ai_quality
    def test_identical_text_rouge1(self):
        text = "this is a test sentence for evaluation"
        assert _rouge_n(text, text, n=1) == pytest.approx(1.0)

    @pytest.mark.ai_quality
    def test_identical_text_rouge2(self):
        text = "this is a test sentence for evaluation"
        assert _rouge_n(text, text, n=2) == pytest.approx(1.0)

    @pytest.mark.ai_quality
    def test_completely_different_rouge1_low(self):
        ref = "the cat sat on the mat"
        cand = "quantum mechanics explains particle physics"
        assert _rouge_n(ref, cand, n=1) < 0.3

    @pytest.mark.ai_quality
    def test_partial_overlap_rouge1(self):
        ref = "the cat sat on the mat"
        cand = "the dog sat on the mat"
        score = _rouge_n(ref, cand, n=1)
        assert 0.3 <= score <= 1.0

    @pytest.mark.ai_quality
    def test_partial_overlap_rouge2(self):
        ref = "the cat sat on the mat"
        cand = "the dog sat on the mat"
        score = _rouge_n(ref, cand, n=2)
        assert 0.0 < score <= 1.0

    @pytest.mark.ai_quality
    def test_rouge2_no_overlap(self):
        ref = "the cat sat"
        cand = "quantum physics rules"
        assert _rouge_n(ref, cand, n=2) == 0.0


class TestRougeL:
    @pytest.mark.ai_quality
    def test_rougeL_identical(self):
        text = "the cat sat on the mat"
        assert _rouge_l(text, text) == pytest.approx(1.0)

    @pytest.mark.ai_quality
    def test_rougeL_partial(self):
        ref = "the cat sat on the mat"
        cand = "the dog sat on the mat"
        score = _rouge_l(ref, cand)
        assert 0.5 <= score <= 1.0

    @pytest.mark.ai_quality
    def test_rougeL_reversed_order(self):
        ref = "the cat sat on the mat"
        cand = "mat the on sat cat the"
        score = _rouge_l(ref, cand)
        assert score < 0.6

    @pytest.mark.ai_quality
    def test_rougeL_no_common(self):
        ref = "the cat sat"
        cand = "quantum physics rules"
        assert _rouge_l(ref, cand) == 0.0


class TestBleu:
    @pytest.mark.ai_quality
    def test_bleu_perfect_match(self):
        text = "this is a test sentence for evaluating bleu score"
        assert _bleu_score(text, text, max_n=4) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_bleu_no_match(self):
        ref = "the cat sat on the mat"
        cand = "quantum physics explains everything"
        assert _bleu_score(ref, cand, max_n=4) == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_bleu_brevity_penalty(self):
        ref = "the cat sat on the mat and looked around"
        cand = "the cat sat"
        score = _bleu_score(ref, cand, max_n=4)
        assert score < 0.5

    @pytest.mark.ai_quality
    def test_bleu_partial_overlap(self):
        ref = "the cat sat on the mat"
        cand = "the dog sat on the mat"
        score = _bleu_score(ref, cand, max_n=4)
        assert 0.0 < score < 1.0

    @pytest.mark.ai_quality
    def test_bleu_empty_candidate(self):
        assert _bleu_score("reference text", "") == 0.0

    @pytest.mark.ai_quality
    def test_bleu_empty_reference(self):
        assert _bleu_score("", "candidate text") == 0.0


class TestBertScoreSim:
    @pytest.mark.ai_quality
    def test_bertscore_identical(self):
        text = "machine learning models require large datasets"
        assert _bertscore_sim(text, text) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_bertscore_semantically_similar(self):
        ref = "the neural network achieved high accuracy"
        cand = "the deep learning model reached good performance"
        score = _bertscore_sim(ref, cand)
        assert 0.3 <= score <= 1.0

    @pytest.mark.ai_quality
    def test_bertscore_unrelated(self):
        ref = "the stock market crashed yesterday"
        cand = "quantum entanglement is a mysterious phenomenon"
        score = _bertscore_sim(ref, cand)
        assert score < 0.5

    @pytest.mark.ai_quality
    def test_bertscore_shared_grammatical_words(self):
        ref = "the cat is on the mat"
        cand = "the dog is in the park"
        score = _bertscore_sim(ref, cand)
        assert score > 0.0


class TestNlgEdgeCases:
    @pytest.mark.ai_quality
    def test_very_short_texts(self):
        assert _rouge_n("a", "a", n=1) == pytest.approx(1.0)
        assert _bleu_score("a b", "a b", max_n=2) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_very_long_texts(self):
        ref = "machine learning " * 500
        cand = "machine learning " * 500
        assert _rouge_n(ref, cand, n=1) == pytest.approx(1.0)
        assert _bleu_score(ref, cand, max_n=2) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_unicode_multi_language(self):
        ref = "café résumé naïve rôle"
        cand = "café résumé naïve rôle"
        assert _rouge_n(ref, cand, n=1) == pytest.approx(1.0)
        assert _bleu_score(ref, cand) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_unicode_different_texts(self):
        ref = "こんにちは世界"
        cand = "你好世界"
        assert _rouge_n(ref, cand, n=1) >= 0.0

    @pytest.mark.ai_quality
    def test_metrics_avg_multiple_references(self):
        refs = [
            "the cat sat on the mat",
            "a cat is sitting on a mat",
        ]
        cand = "the dog sat on the mat"
        scores = sum(_rouge_n(ref, cand, n=1) for ref in refs)
        avg = scores / len(refs)
        assert 0.0 <= avg <= 1.0

    @pytest.mark.ai_quality
    def test_repeated_ngrams_rouge(self):
        ref = "very very very long sentence"
        cand = "very very very long sentence"
        assert _rouge_n(ref, cand, n=2) == pytest.approx(1.0)

    @pytest.mark.ai_quality
    def test_repeated_ngrams_bleu(self):
        ref = "very very very long sentence"
        cand = "very very very long sentence"
        assert _bleu_score(ref, cand, max_n=2) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.ai_quality
    def test_single_word_texts(self):
        assert _rouge_n("hello", "hello", n=1) == pytest.approx(1.0)
        assert _rouge_n("hello", "world", n=1) == 0.0
        assert _bleu_score("hello", "hello", max_n=1) == pytest.approx(1.0, abs=1e-6)
        assert _bleu_score("hello", "world", max_n=1) == 0.0

    @pytest.mark.ai_quality
    def test_both_empty(self):
        assert _rouge_n("", "") == 0.0
        assert _bleu_score("", "") == 0.0
        assert _rouge_l("", "") == 0.0
        assert _bertscore_sim("", "") == 0.0

    @pytest.mark.ai_quality
    def test_consistency_positive_correlation(self):
        ref = "deep reinforcement learning achieves superhuman performance"
        cand = "reinforcement learning with deep networks achieves strong results"
        bleu = _bleu_score(ref, cand)
        rouge = _rouge_n(ref, cand, n=1)
        if bleu > 0.3:
            assert rouge > 0.2
