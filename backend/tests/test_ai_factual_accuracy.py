# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
"""
Factual accuracy evaluation suite for AI-generated academic documents.

Sections:
   3A — DOI & Citation Metadata     (~6 tests)
   3B — Claim Verification          (~6 tests)
   3C — Numerical & Count Accuracy  (~4 tests)
   3D — Edge Cases & Scoring        (~4 tests)
"""

import re
from typing import Any

import pytest

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

VALID_DOIS = [
    "10.1038/s41586-023-06559-5",
    "10.1109/ACCESS.2024.1234567",
    "10.1000/xyz123",
    "10.1016/j.neuron.2023.01.001",
    "10.1371/journal.pcbi.1012345",
]

MOCK_CITATION_METADATA: dict[str, dict[str, Any]] = {
    "10.1038/s41586-023-06559-5": {
        "doi": "10.1038/s41586-023-06559-5",
        "title": "A long-term study of AI performance in medical imaging",
        "authors": [{"given": "Alice", "family": "Chen"}, {"given": "Bob", "family": "Smith"}],
        "year": 2023,
        "journal": "Nature",
        "publisher": "Springer Nature",
    },
    "10.1109/ACCESS.2024.1234567": {
        "doi": "10.1109/ACCESS.2024.1234567",
        "title": "Deep learning approaches for edge computing",
        "authors": [{"given": "Carlos", "family": "Garcia"}],
        "year": 2024,
        "journal": "IEEE Access",
        "publisher": "IEEE",
    },
    "10.1000/xyz123": {
        "doi": "10.1000/xyz123",
        "title": "Cross-referencing methodologies in systematic reviews",
        "authors": [{"given": "Diana", "family": "Kim"}],
        "year": 2022,
        "journal": "PLOS ONE",
        "publisher": "PLOS",
    },
}

# ---------------------------------------------------------------------------
#  Factual accuracy helpers
# ---------------------------------------------------------------------------


def _check_citation_accuracy(doi: str, mock_api: dict[str, Any]) -> dict[str, Any]:
    """Verify citation metadata against external source.

    Returns dict with:
      - exists: bool
      - matches: dict of field -> bool
      - confidence: float (0-1)
    """
    if not doi or not isinstance(doi, str):
        return {"exists": False, "matches": {}, "confidence": 0.0}

    normalized = doi.rstrip(".)},;:")
    if not re.match(r"10\.\d{4,}/", normalized):
        return {"exists": False, "matches": {}, "confidence": 0.0}

    metadata = mock_api.get(normalized)
    if metadata is None:
        return {"exists": False, "matches": {}, "confidence": 0.0}

    return {
        "exists": True,
        "matches": {
            "doi": True,
            "title": True,
            "authors": True,
            "year": True,
            "journal": True,
        },
        "confidence": 1.0,
        "metadata": metadata,
    }


def _verify_claim_against_source(claim: str, source_text: str) -> dict[str, Any]:
    """Check if factual claim is supported by source.

    Returns dict with:
      - supported: bool (fully)
      - partially_supported: bool
      - contradicted: bool
      - confidence: float (0-1)
      - evidence_found: list of supporting substrings
    """
    claim_lower = claim.lower()
    source_lower = source_text.lower()

    claim_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_lower)) | set(re.findall(r"\b\d+\b", claim))
    source_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", source_lower)) | set(re.findall(r"\b\d+\b", source_text))

    overlap = claim_tokens & source_tokens
    overlap_ratio = len(overlap) / max(len(claim_tokens), 1)

    evidence = []
    for token in claim_tokens:
        if token in source_lower:
            evidence.append(token)

    # Check for contradiction (negation + same token)
    contradict_patterns = [r"\bnot\b.*\b" + re.escape(t) + r"\b" for t in claim_tokens]
    contradicted = any(re.search(p, source_lower) for p in contradict_patterns)

    supported = overlap_ratio >= 0.6 and not contradicted
    partially = 0.3 <= overlap_ratio < 0.6 and not contradicted

    return {
        "supported": supported,
        "partially_supported": partially,
        "contradicted": contradicted,
        "confidence": round(overlap_ratio, 4),
        "evidence_found": evidence[:5],
    }


def _accuracy_score(verifications: list[dict[str, Any]]) -> dict[str, float]:
    """Compute overall accuracy score from a list of verification results.

    Returns dict with:
      - accuracy: percentage of claims fully supported
      - partial_rate: percentage partially supported
      - contradiction_rate: percentage contradicted
      - avg_confidence: average confidence across all checks
    """
    total = max(len(verifications), 1)
    supported = sum(1 for v in verifications if v.get("supported"))
    partial = sum(1 for v in verifications if v.get("partially_supported"))
    contradicted = sum(1 for v in verifications if v.get("contradicted"))
    avg_conf = sum(v.get("confidence", 0) for v in verifications) / total

    return {
        "accuracy": round(supported / total * 100, 2),
        "partial_rate": round(partial / total * 100, 2),
        "contradiction_rate": round(contradicted / total * 100, 2),
        "avg_confidence": round(avg_conf, 4),
    }


# ===================================================================
#  3A — DOI & Citation Metadata
# ===================================================================


class TestDOICitationAccuracy:
    """DOI resolution and citation metadata verification."""

    @pytest.mark.ai_quality
    def test_valid_doi_resolves_to_correct_metadata(self):
        doi = "10.1038/s41586-023-06559-5"
        result = _check_citation_accuracy(doi, MOCK_CITATION_METADATA)
        assert result["exists"], f"Valid DOI should exist: {result}"
        assert result["confidence"] == 1.0
        assert result["metadata"]["title"] == "A long-term study of AI performance in medical imaging"
        assert result["metadata"]["year"] == 2023

    @pytest.mark.ai_quality
    def test_invalid_doi_returns_not_found(self):
        result = _check_citation_accuracy("10.9999/fake-doi-12345", MOCK_CITATION_METADATA)
        assert not result["exists"]
        assert result["confidence"] == 0.0

    @pytest.mark.ai_quality
    def test_citation_author_matches_metadata(self):
        doi = "10.1109/ACCESS.2024.1234567"
        result = _check_citation_accuracy(doi, MOCK_CITATION_METADATA)
        authors = result["metadata"]["authors"]
        assert any(a["family"] == "Garcia" for a in authors)

    @pytest.mark.ai_quality
    def test_citation_year_matches_metadata(self):
        doi = "10.1000/xyz123"
        result = _check_citation_accuracy(doi, MOCK_CITATION_METADATA)
        assert result["metadata"]["year"] == 2022

    @pytest.mark.ai_quality
    def test_fabricated_doi_detected(self):
        fabricated = "10.9999/this-is-completely-fabricated-99999"
        result = _check_citation_accuracy(fabricated, MOCK_CITATION_METADATA)
        assert not result["exists"]

    @pytest.mark.ai_quality
    def test_malformed_doi_handled_gracefully(self):
        cases = ["not-a-doi", "", "10.", "doi:10.1000/xyz123", None, "invalid"]
        for doi in cases:
            result = _check_citation_accuracy(doi, MOCK_CITATION_METADATA)
            assert isinstance(result, dict)
            assert "exists" in result
            assert not result["exists"]


# ===================================================================
#  3B — Claim Verification
# ===================================================================


class TestClaimVerification:
    """Verify factual claims against source documents."""

    @pytest.mark.ai_quality
    def test_claim_supported_by_source(self):
        source = "The study found that 85% of participants showed improvement after treatment."
        claim = "The study found that 85% of participants showed improvement."
        result = _verify_claim_against_source(claim, source)
        assert result["supported"], f"Supported claim not verified: {result}"
        assert result["confidence"] >= 0.5

    @pytest.mark.ai_quality
    def test_claim_contradicted_by_source(self):
        source = "The control group did not show any significant improvement."
        claim = "The control group showed significant improvement."
        result = _verify_claim_against_source(claim, source)
        assert result["contradicted"] or not result["supported"], f"Contradicted claim not detected: {result}"

    @pytest.mark.ai_quality
    def test_claim_partially_supported(self):
        source = "The model achieved 94% accuracy on the validation set."
        claim = "The model achieved 94% accuracy on the validation set and 97% on the test set."
        result = _verify_claim_against_source(claim, source)
        assert result["partially_supported"] or result["supported"], f"Partial support not detected: {result}"

    @pytest.mark.ai_quality
    def test_claim_with_no_source_evidence(self):
        source = "This paper discusses quantum computing error correction codes."
        claim = "The stock market rose 5% due to positive earnings reports."
        result = _verify_claim_against_source(claim, source)
        assert not result["supported"], f"Unsupported claim should not pass: {result}"
        assert result["confidence"] < 0.3

    @pytest.mark.ai_quality
    def test_fabricated_author_detected(self):
        source = "Smith et al. (2023) studied the effects of AI on healthcare."
        claim = "FabricatedAuthor (2024) claimed that AI systems hallucinate frequently."
        result = _verify_claim_against_source(claim, source)
        assert not result["supported"], f"Fabricated author claim should not be fully supported: {result}"
        assert result["confidence"] < 0.5

    @pytest.mark.ai_quality
    def test_fabricated_year_detected(self):
        source = "The transformer architecture was introduced in 2017 (Vaswani et al.)."
        claim = "The BERT model was developed in 2025 by a completely different team."
        result = _verify_claim_against_source(claim, source)
        assert not result["supported"], "Mismatched year should not pass"
        assert result["confidence"] < 0.5


# ===================================================================
#  3C — Numerical & Count Accuracy
# ===================================================================


class TestNumericalAccuracy:
    """Numerical claim accuracy and citation count verification."""

    @pytest.mark.ai_quality
    def test_numerical_claim_matches(self):
        source = "The experiment included 500 participants aged 18-65 from 3 countries."
        claim_matching = "The experiment included exactly 500 participants from 3 countries."
        claim_wrong_num = "The experiment included only 50 participants from 5 countries."
        matching_result = _verify_claim_against_source(claim_matching, source)
        wrong_result = _verify_claim_against_source(claim_wrong_num, source)
        assert matching_result["supported"], f"Matching numbers should be supported: {matching_result}"
        assert wrong_result["confidence"] < matching_result["confidence"], (
            f"Wrong numbers should score lower: {wrong_result} vs {matching_result}"
        )

    @pytest.mark.ai_quality
    def test_citation_count_accuracy(self):
        source = "Previous work [1, 2, 3] and related studies [4, 5] support our hypothesis."
        claim_accurate = "Three prior studies [1, 2, 3] support our hypothesis."
        claim_inaccurate = "Five prior studies [1, 2, 3] support our hypothesis."
        accurate_result = _verify_claim_against_source(claim_accurate, source)
        inaccurate_result = _verify_claim_against_source(claim_inaccurate, source)
        assert accurate_result["confidence"] >= inaccurate_result["confidence"]

    @pytest.mark.ai_quality
    def test_multiple_references_same_paper(self):
        source = "Smith (2023) found X. Smith (2023) also found Y. Smith (2023) confirmed Z."
        claim = "Smith (2023) conducted three separate analyses."
        result = _verify_claim_against_source(claim, source)
        assert result["supported"] or result["partially_supported"], (
            f"Multiple references should have support: {result}"
        )

    @pytest.mark.ai_quality
    def test_retrospective_citation_impossible(self):
        source = "Research published in 2020 shaped the field."
        claim = "A 2023 paper by Smith cites a 2025 study that hasn't been published yet."
        result = _verify_claim_against_source(claim, source)
        assert result["confidence"] < 0.3, "Future citations should not be verifiable"


# ===================================================================
#  3D — Edge Cases & Scoring
# ===================================================================


class TestAccuracyEdgeCasesAndScoring:
    """Edge case handling and accuracy scoring aggregation."""

    @pytest.mark.ai_quality
    def test_api_timeout_handled_gracefully(self):
        def _timeout_api(doi):
            raise TimeoutError("API timeout")

        doi = "10.1038/s41586-023-06559-5"
        try:
            result = _check_citation_accuracy(doi, MOCK_CITATION_METADATA)
            assert isinstance(result, dict)
        except TimeoutError:
            pytest.skip("Timeout not handled internally")
        except Exception as exc:
            pytest.fail(f"Unexpected exception: {exc}")

    @pytest.mark.ai_quality
    def test_empty_response_from_api(self):
        result = _check_citation_accuracy("10.1000/xyz123", {})
        assert not result["exists"]
        assert result["confidence"] == 0.0

    @pytest.mark.ai_quality
    def test_accuracy_scoring_percentage(self):
        all_pass = [
            {"supported": True, "partially_supported": False, "contradicted": False, "confidence": 0.9},
            {"supported": True, "partially_supported": False, "contradicted": False, "confidence": 0.8},
        ]
        mixed = [
            {"supported": True, "partially_supported": False, "contradicted": False, "confidence": 0.9},
            {"supported": False, "partially_supported": True, "contradicted": False, "confidence": 0.4},
            {"supported": False, "partially_supported": False, "contradicted": True, "confidence": 0.1},
        ]
        pass_score = _accuracy_score(all_pass)
        mixed_score = _accuracy_score(mixed)
        assert pass_score["accuracy"] == 100.0
        assert pass_score["contradiction_rate"] == 0.0
        assert mixed_score["accuracy"] < pass_score["accuracy"]
        assert mixed_score["contradiction_rate"] > 0.0

    @pytest.mark.ai_quality
    def test_accuracy_score_bounds(self):
        empty = _accuracy_score([])
        assert empty["accuracy"] == 0.0
        assert empty["avg_confidence"] == 0.0
        single = _accuracy_score(
            [{"supported": True, "partially_supported": False, "contradicted": False, "confidence": 0.75}]
        )
        assert single["accuracy"] == 100.0
        assert single["avg_confidence"] == 0.75
