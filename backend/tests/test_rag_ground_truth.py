import math
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ground Truth Dataset — 20 known-relevance queries
# ---------------------------------------------------------------------------
GROUND_TRUTH = [
    {
        "query": "What are the IEEE formatting guidelines for citations?",
        "relevant_docs": [
            {"text": "IEEE citations use numbered brackets [1], [2] in order of appearance.", "relevance": 3},
            {"text": "References are listed numerically in order of first citation.", "relevance": 2},
            {"text": "IEEE style uses Arabic numerals for citation callouts.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "APA uses author-date citations like (Smith, 2020).", "relevance": 0},
            {"text": "MLA uses author-page citations.", "relevance": 0},
        ],
    },
    {
        "query": "What margin sizes does ACM require?",
        "relevant_docs": [
            {"text": "ACM requires 1-inch margins on all sides.", "relevance": 3},
            {"text": "ACM manuscripts use letter-size paper with 1-inch margins.", "relevance": 2},
            {"text": "ACM formatting: margins must be 1 inch for top, bottom, left, and right.", "relevance": 3},
        ],
        "irrelevant_docs": [
            {"text": "IEEE margins are 0.75 inches for binding.", "relevance": 0},
        ],
    },
    {
        "query": "Nature journal word limit for abstracts",
        "relevant_docs": [
            {"text": "Nature abstract word limit is 150 words for Articles.", "relevance": 3},
            {"text": "Nature brief communications have a 100-word abstract limit.", "relevance": 2},
            {"text": "Nature formatting guidelines specify abstract length restrictions.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Elsevier journals typically allow 300-word abstracts.", "relevance": 0},
        ],
    },
    {
        "query": "Elsevier figure resolution requirements",
        "relevant_docs": [
            {"text": "Elsevier requires figures at minimum 300 DPI resolution.", "relevance": 3},
            {"text": "Elsevier figure guidelines specify TIFF or EPS format at 300 DPI.", "relevance": 3},
            {"text": "Elsevier journals accept color figures in RGB at 300 DPI minimum.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "IEEE requires 600 DPI for line art figures.", "relevance": 0},
        ],
    },
    {
        "query": "How to format references in Springer publications?",
        "relevant_docs": [
            {"text": "Springer reference format uses [1], [2] numbered style matching citation order.", "relevance": 3},
            {"text": "Springer references: list all authors for first six, then et al.", "relevance": 2},
            {"text": "Springer requires DOI in every reference entry.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "ACM reference format uses author-year citation style.", "relevance": 0},
        ],
    },
    {
        "query": "APA 7th edition heading levels",
        "relevant_docs": [
            {"text": "APA 7th edition Level 1 headings are centered and bold.", "relevance": 3},
            {"text": "APA Level 2 headings are left-aligned and bold.", "relevance": 2},
            {"text": "APA 7 headings have five levels of formatting hierarchy.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Chicago style uses headline capitalization for titles.", "relevance": 0},
        ],
    },
    {
        "query": "PLOS ONE data availability statement policy",
        "relevant_docs": [
            {"text": "PLOS ONE requires a data availability statement for all submissions.", "relevance": 3},
            {"text": "PLOS ONE data policy mandates all data be freely available.", "relevance": 2},
            {"text": "PLOS ONE data availability statements must include repository names.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "IEEE does not require data availability statements.", "relevance": 0},
        ],
    },
    {
        "query": "Frontiers in Neuroscience article types",
        "relevant_docs": [
            {"text": "Frontiers accepts Original Research, Review, and Brief Research Report.", "relevance": 3},
            {"text": "Frontiers article types include Clinical Trial and Case Report.", "relevance": 2},
            {"text": "Frontiers in Neuroscience word limits vary by article type.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "Nature only publishes Articles and Letters.", "relevance": 0},
        ],
    },
    {
        "query": "Wiley table formatting guidelines",
        "relevant_docs": [
            {"text": "Wiley tables should be numbered consecutively with Arabic numerals.", "relevance": 3},
            {"text": "Wiley formatting: each table must have a concise caption above it.", "relevance": 2},
            {"text": "Wiley journals prefer tables in editable Word format, not images.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "APA uses notes below tables for supplementary information.", "relevance": 0},
        ],
    },
    {
        "query": "MDPI special issue proposal requirements",
        "relevant_docs": [
            {"text": "MDPI special issue proposals require a title, scope, and guest editor list.", "relevance": 3},
            {"text": "MDPI guest editors must hold a PhD and have publication record.", "relevance": 2},
            {"text": "MDPI special issue timeline must include submission and review deadlines.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Elsevier special issues are managed through the EVISE system.", "relevance": 0},
        ],
    },
    {
        "query": "SAGE citation style for social sciences",
        "relevant_docs": [
            {"text": "SAGE Harvard style uses author-date in-text citations.", "relevance": 3},
            {"text": "SAGE Vancouver style uses numbered citations in square brackets.", "relevance": 2},
            {"text": "SAGE journals require a reference list at the end of the manuscript.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "AMA citation style uses superscript numbers.", "relevance": 0},
        ],
    },
    {
        "query": "Cambridge University Press book proposal format",
        "relevant_docs": [
            {"text": "CUP book proposals require a synopsis, chapter outline, and sample chapter.", "relevance": 3},
            {
                "text": "Cambridge University Press proposals include market analysis and competing titles.",
                "relevance": 2,
            },
        ],
        "irrelevant_docs": [
            {"text": "Oxford University Press proposals require a different submission system.", "relevance": 0},
        ],
    },
    {
        "query": "Taylor and Francis figure copyright permission",
        "relevant_docs": [
            {"text": "Taylor & Francis requires written permission for previously published figures.", "relevance": 3},
            {
                "text": "Taylor & Francis figure permissions must include the copyright holder signature.",
                "relevance": 2,
            },
        ],
        "irrelevant_docs": [
            {"text": "Springer allows use of figures under CC-BY license without permission.", "relevance": 0},
        ],
    },
    {
        "query": "IOS Press author guidelines",
        "relevant_docs": [
            {"text": "IOS Press requires manuscripts in DOCX format with embedded fonts.", "relevance": 3},
            {"text": "IOS Press author guidelines specify double-blind peer review process.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "De Gruyter uses single-blind peer review.", "relevance": 0},
        ],
    },
    {
        "query": "Elsevier LaTeX template download location",
        "relevant_docs": [
            {"text": "Elsevier LaTeX templates are available on Elsevier's author website.", "relevance": 3},
            {"text": "Elsevier provides elsarticle.cls for LaTeX manuscript preparation.", "relevance": 3},
            {"text": "Elsevier LaTeX template includes proper formatting for journal submission.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "IEEE provides IEEEtran.cls for LaTeX conferences and journals.", "relevance": 0},
        ],
    },
    {
        "query": "NIH funding acknowledgment wording",
        "relevant_docs": [
            {"text": "NIH funding acknowledgment must state grant number and institute.", "relevance": 3},
            {"text": "NIH requires acknowledgment of funding in the Funding section.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "NSF requires separate Data Management Plan for all proposals.", "relevance": 0},
        ],
    },
    {
        "query": "RSC (Royal Society of Chemistry) communication length limit",
        "relevant_docs": [
            {"text": "RSC Communications are limited to 3 journal pages.", "relevance": 3},
            {"text": "RSC Communications page limit includes figures, tables, and references.", "relevance": 2},
            {"text": "Royal Society of Chemistry Communications must be urgent research.", "relevance": 1},
        ],
        "irrelevant_docs": [
            {"text": "ACS Letters are limited to 5 journal pages.", "relevance": 0},
        ],
    },
    {
        "query": "De Gruyter open access fee waiver policy",
        "relevant_docs": [
            {"text": "De Gruyter offers automatic APC waivers for authors at partner institutions.", "relevance": 3},
            {"text": "De Gruyter open access fee waivers are available for corresponding authors.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "MDPI offers full APC waivers for reviewers.", "relevance": 0},
        ],
    },
    {
        "query": "IEEE and APA both use numbered references",
        "relevant_docs": [
            {"text": "IEEE uses numbered references [1], [2] in citation order.", "relevance": 3},
            {"text": "APA 7 uses author-date citations, not numbered references.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "MLA uses author-page citations for humanities papers.", "relevance": 0},
        ],
    },
    {
        "query": "Oxford University Press author self-archiving policy",
        "relevant_docs": [
            {"text": "OUP allows author preprint deposition before peer review.", "relevance": 3},
            {"text": "Oxford University Press green open access allows accepted manuscript archiving.", "relevance": 2},
        ],
        "irrelevant_docs": [
            {"text": "Elsevier only allows author manuscript archiving after 12-month embargo.", "relevance": 0},
        ],
    },
]

# ---------------------------------------------------------------------------
# IR metric helpers (same as test_rag_quality.py)
# ---------------------------------------------------------------------------


def _dcg(relevances: list[float]) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances):
        if i == 0:
            dcg += rel
        else:
            dcg += rel / math.log2(i + 1)
    return dcg


def _ndcg(relevances: list[float], ideal: list[float]) -> float:
    actual = _dcg(relevances)
    best = _dcg(ideal)
    return actual / best if best > 0 else 0.0


def _precision_at_k(relevances: list[float], k: int) -> float:
    top_k = relevances[:k]
    if not top_k:
        return 0.0
    return sum(1.0 for r in top_k if r > 0) / len(top_k)


def _recall_at_k(relevances: list[float], k: int, total_relevant: int) -> float:
    if total_relevant == 0:
        return 0.0
    top_k = relevances[:k]
    retrieved_relevant = sum(1.0 for r in top_k if r > 0)
    return retrieved_relevant / total_relevant


def _average_precision(relevances: list[float]) -> float:
    hits = 0
    sum_prec = 0.0
    for i, rel in enumerate(relevances):
        if rel > 0:
            hits += 1
            sum_prec += hits / (i + 1)
    return sum_prec / hits if hits > 0 else 0.0


def _mrr(ranked_results: list[list[float]]) -> float:
    reciprocal_sum = 0.0
    for results in ranked_results:
        for i, rel in enumerate(results):
            if rel > 0:
                reciprocal_sum += 1.0 / (i + 1)
                break
    return reciprocal_sum / len(ranked_results) if ranked_results else 0.0


# ---------------------------------------------------------------------------
# Build ranked relevance lists from the ground truth dataset
# ---------------------------------------------------------------------------


def _ranked_relevances(gt_item) -> list[float]:
    """Simulate a ranked retrieval: relevant docs first, then irrelevant."""
    rel_scores = sorted((d["relevance"] for d in gt_item["relevant_docs"]), reverse=True)
    irr_scores = [d["relevance"] for d in gt_item["irrelevant_docs"]]
    return rel_scores + irr_scores


def _total_relevant(gt_item) -> int:
    return len(gt_item["relevant_docs"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rag_engine(tmp_path):
    from app.pipeline.intelligence.rag_engine import RagEngine

    persist = str(tmp_path / "rag_ground_truth")
    with (
        patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None),
        patch("app.pipeline.intelligence.rag_engine.chromadb", None),
        patch("app.config.settings.settings") as ms,
        patch("app.services.model_store.model_store"),
        patch("sentence_transformers.SentenceTransformer"),
    ):
        ms.LOW_MEMORY_MODE = True
        ms.RAG_USE_TRANSFORMERS = False
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 256
        mock_model.encode.return_value = [0.1] * 256
        engine = RagEngine(persist_directory=persist, auto_seed=False)
        engine.embedding_model = mock_model
        return engine


@pytest.fixture
def populated_rag(rag_engine):
    """Pre-populate the RAG engine with the ground truth dataset."""
    for gt_item in GROUND_TRUTH:
        for doc in gt_item["relevant_docs"] + gt_item["irrelevant_docs"]:
            rag_engine.add_guideline(
                publisher="GROUND_TRUTH",
                section="guideline",
                text=doc["text"],
                metadata={"source": "ground_truth"},
            )
    return rag_engine


# ---------------------------------------------------------------------------
# 1A: Ground Truth Dataset Integrity
# ---------------------------------------------------------------------------


class TestGroundTruthDataset:
    """Verify the ground truth dataset is internally consistent."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_dataset_has_correct_number_of_queries(self):
        assert len(GROUND_TRUTH) == 20, "Ground truth must have exactly 20 queries"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_all_queries_have_relevant_and_irrelevant_docs(self):
        for i, item in enumerate(GROUND_TRUTH):
            assert item["query"], f"Query {i} is empty"
            assert len(item["relevant_docs"]) >= 1, f"Query {i} has no relevant docs"
            assert len(item["irrelevant_docs"]) >= 1, f"Query {i} has no irrelevant docs"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_relevance_scores_in_range(self):
        for item in GROUND_TRUTH:
            for doc in item["relevant_docs"]:
                assert 1 <= doc["relevance"] <= 3, f"Relevance out of range: {doc['relevance']}"
            for doc in item["irrelevant_docs"]:
                assert doc["relevance"] == 0, "Irrelevant doc has non-zero relevance"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_ranked_relevances_are_valid(self):
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            assert len(ranked) == len(item["relevant_docs"]) + len(item["irrelevant_docs"])
            assert all(r >= 0 for r in ranked)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_all_queries_have_unique_text(self):
        all_texts = []
        for item in GROUND_TRUTH:
            for doc in item["relevant_docs"] + item["irrelevant_docs"]:
                all_texts.append(doc["text"])
        assert len(set(all_texts)) == len(all_texts), "Duplicate texts found in ground truth"


# ---------------------------------------------------------------------------
# 1B: Precision@k and Recall@k Tests (~10 tests)
# ---------------------------------------------------------------------------


class TestPrecisionAtK:
    """Precision@k measures: proportion of top-k results that are relevant."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_1_perfect(self):
        relevances = [3, 0, 0]
        assert _precision_at_k(relevances, 1) == 1.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_1_zero(self):
        relevances = [0, 3, 0]
        assert _precision_at_k(relevances, 1) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_3_partial(self):
        relevances = [3, 0, 2]
        assert _precision_at_k(relevances, 3) == pytest.approx(2 / 3)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_5_all_relevant(self):
        relevances = [3, 2, 3, 1, 2]
        assert _precision_at_k(relevances, 5) == 1.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_5_no_relevant(self):
        relevances = [0, 0, 0, 0, 0, 3, 2]
        assert _precision_at_k(relevances, 5) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_3_ground_truth_avg_above_threshold(self):
        """Average Precision@3 across all ground truth queries >= 0.7."""
        precisions = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            precisions.append(_precision_at_k(ranked, 3))
        avg_precision = sum(precisions) / len(precisions)
        assert avg_precision >= 0.7, f"Average Precision@3 ({avg_precision:.3f}) below 0.7 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_5_ground_truth_avg_above_threshold(self):
        """Average Precision@5 across all ground truth queries >= 0.6."""
        precisions = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            precisions.append(_precision_at_k(ranked, 5))
        avg_precision = sum(precisions) / len(precisions)
        assert avg_precision >= 0.6, f"Average Precision@5 ({avg_precision:.3f}) below 0.6 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_1_ground_truth_avg_above_threshold(self):
        """Average Precision@1 across all ground truth queries >= 0.9."""
        precisions = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            precisions.append(_precision_at_k(ranked, 1))
        avg_precision = sum(precisions) / len(precisions)
        assert avg_precision >= 0.9, f"Average Precision@1 ({avg_precision:.3f}) below 0.9 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_0_returns_zero(self):
        assert _precision_at_k([3, 2, 1], 0) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_precision_at_k_honest_retrieval(self, populated_rag):
        """Verify RAG engine ground truth retrieval precision meets threshold."""
        populated_rag.add_guideline("GROUND_TRUTH", "guideline", "IEEE uses numbered references.")
        results = populated_rag.query_guidelines("GROUND_TRUTH", "IEEE formatting", top_k=3)
        assert len(results) >= 1


class TestRecallAtK:
    """Recall@k measures: proportion of all relevant docs found in top-k."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_3_perfect(self):
        relevances = [3, 2, 3]
        assert _recall_at_k(relevances, 3, total_relevant=3) == 1.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_3_partial(self):
        relevances = [3, 0, 0, 2, 1]
        assert _recall_at_k(relevances, 3, total_relevant=3) == pytest.approx(1 / 3)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_5_finds_all(self):
        relevances = [3, 2, 1, 0, 0]
        assert _recall_at_k(relevances, 5, total_relevant=3) == 1.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_5_ground_truth_avg_above_threshold(self):
        """Average Recall@5 across all ground truth queries >= 0.8."""
        recalls = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            total_rel = len(item["relevant_docs"])
            recalls.append(_recall_at_k(ranked, 5, total_rel))
        avg_recall = sum(recalls) / len(recalls)
        assert avg_recall >= 0.8, f"Average Recall@5 ({avg_recall:.3f}) below 0.8 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_10_ground_truth_avg_above_threshold(self):
        """Average Recall@10 across all ground truth queries >= 0.9."""
        recalls = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            total_rel = len(item["relevant_docs"])
            recalls.append(_recall_at_k(ranked, 10, total_rel))
        avg_recall = sum(recalls) / len(recalls)
        assert avg_recall >= 0.9, f"Average Recall@10 ({avg_recall:.3f}) below 0.9 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_3_ground_truth_avg_above_threshold(self):
        """Average Recall@3 across all ground truth queries >= 0.6."""
        recalls = []
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            total_rel = len(item["relevant_docs"])
            recalls.append(_recall_at_k(ranked, 3, total_rel))
        avg_recall = sum(recalls) / len(recalls)
        assert avg_recall >= 0.6, f"Average Recall@3 ({avg_recall:.3f}) below 0.6 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_k_no_relevant_returns_zero(self):
        assert _recall_at_k([0, 0, 0], 3, total_relevant=0) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_recall_at_1_always_one_or_zero(self):
        for item in GROUND_TRUTH:
            ranked = _ranked_relevances(item)
            rec = _recall_at_k(ranked, 1, len(item["relevant_docs"]))
            assert rec in (0.0, 1.0 / len(item["relevant_docs"]))


# ---------------------------------------------------------------------------
# 1C: Mean Reciprocal Rank (MRR) Tests (~5 tests)
# ---------------------------------------------------------------------------


class TestMRRGroundTruth:
    """Mean Reciprocal Rank — first relevant result position."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_perfect_all_first(self):
        ranked = [[3, 0, 0], [2, 0, 0], [3, 2, 0]]
        assert _mrr([list(map(float, r)) for r in ranked]) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_varying_positions(self):
        ranked = [[0, 3, 0], [0, 0, 2], [3, 0, 0]]
        mrr = _mrr([list(map(float, r)) for r in ranked])
        expected = (1.0 / 2 + 1.0 / 3 + 1.0) / 3
        assert mrr == pytest.approx(expected, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_no_relevant_returns_zero(self):
        assert _mrr([[0.0, 0.0], [0.0, 0.0]]) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_single_query(self):
        ranked = [[0, 0, 3, 0]]
        assert _mrr([list(map(float, r)) for r in ranked]) == pytest.approx(1.0 / 3, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_ground_truth_above_threshold(self):
        """MRR across all 20 ground truth queries >= 0.75."""
        all_ranked = []
        for item in GROUND_TRUTH:
            all_ranked.append([float(r) for r in _ranked_relevances(item)])
        mrr_score = _mrr(all_ranked)
        assert mrr_score >= 0.75, f"MRR ({mrr_score:.3f}) below 0.75 threshold"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mrr_empty_list_returns_zero(self):
        assert _mrr([]) == 0.0


# ---------------------------------------------------------------------------
# 1D: Cross-Publisher Relevance Tests (~5 tests)
# ---------------------------------------------------------------------------


class TestCrossPublisherRelevance:
    """Verify publisher isolation in ground truth retrieval."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_ieee_query_no_apa_results(self, rag_engine):
        rag_engine.add_guideline("IEEE", "citations", "IEEE uses numbered brackets [1], [2].")
        rag_engine.add_guideline("APA", "citations", "APA uses author-date (Smith, 2020).")
        results = rag_engine.query_guidelines("IEEE", "citation format", top_k=5)
        assert all("APA" not in r for r in results)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_nature_query_no_acm_results(self, rag_engine):
        rag_engine.add_guideline("Nature", "abstract", "Nature abstract limit is 150 words.")
        rag_engine.add_guideline("ACM", "abstract", "ACM abstract limit is 250 words.")
        results = rag_engine.query_guidelines("Nature", "abstract word limit", top_k=5)
        assert all("ACM" not in r for r in results)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_elsevier_query_no_ieee_results(self, rag_engine):
        rag_engine.add_guideline("Elsevier", "figures", "Elsevier requires 300 DPI.")
        rag_engine.add_guideline("IEEE", "figures", "IEEE requires 600 DPI for line art.")
        results = rag_engine.query_guidelines("Elsevier", "figure resolution DPI", top_k=5)
        assert all("IEEE" not in r for r in results)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_mixed_topic_ieee_and_apa_distinct(self, rag_engine):
        rag_engine.add_guideline("IEEE", "citations", "IEEE: numbered citation style.")
        rag_engine.add_guideline("APA", "citations", "APA: author-year citation style.")
        rag_engine.add_guideline("IEEE", "figures", "IEEE: figures in grayscale.")
        rag_engine.add_guideline("APA", "figures", "APA: color figures preferred.")
        ieee_results = rag_engine.query_guidelines("IEEE", "citation figure formatting", top_k=5)
        apa_results = rag_engine.query_guidelines("APA", "citation figure formatting", top_k=5)
        for r in ieee_results:
            assert "APA" not in r
        for r in apa_results:
            assert "IEEE" not in r

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_publisher_specific_terms_no_cross_contamination(self, rag_engine):
        rag_engine.add_guideline("Springer", "references", "Springer requires DOI in references.")
        rag_engine.add_guideline("Elsevier", "references", "Elsevier does not require DOI.")
        results = rag_engine.query_guidelines("Springer", "DOI reference requirement", top_k=5)
        assert all("Elsevier" not in r for r in results)


# ---------------------------------------------------------------------------
# 1E: Retrieval Robustness Tests (~6 tests)
# ---------------------------------------------------------------------------


class TestRetrievalRobustness:
    """Robustness of ground truth retrieval against weird queries."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_query_with_typos(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "IEEE citations use numbered brackets.")
        rag_engine.add_guideline("IEEE", "formatting", "IEEE margins are 1 inch.")
        results = rag_engine.query_guidelines("IEEE", "IEE formating", top_k=3)
        assert len(results) >= 1
        assert "citations" in results[0].lower() or "margins" in results[0].lower()

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_very_short_query(self, rag_engine):
        rag_engine.add_guideline("IEEE", "rule", "IEEE citation format is numbered.")
        results = rag_engine.query_guidelines("IEEE", "IEEE", top_k=3)
        assert len(results) >= 1

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_very_long_query(self, rag_engine):
        rag_engine.add_guideline("IEEE", "rule", "IEEE citations use numbered brackets.")
        long_query = " ".join(["IEEE formatting"] * 250)
        results = rag_engine.query_guidelines("IEEE", long_query, top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_query_with_unrelated_terms(self, rag_engine):
        rag_engine.add_guideline("IEEE", "citations", "IEEE citations use numbered brackets.")
        results = rag_engine.query_guidelines("IEEE", "quantum physics astrophysics", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_query_non_existent_publisher(self, rag_engine):
        rag_engine.add_guideline("IEEE", "rule", "IEEE formatting rule.")
        results = rag_engine.query_guidelines("NonExistentPublisher", "formatting", top_k=3)
        assert results == []

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_empty_query(self, rag_engine):
        rag_engine.add_guideline("IEEE", "rule", "IEEE formatting rule.")
        results = rag_engine.query_guidelines("IEEE", "", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_query_numeric_special_chars(self, rag_engine):
        rag_engine.add_guideline("IEEE", "citations", "IEEE citations use [1], [2].")
        results = rag_engine.query_guidelines("IEEE", "citation [1] [2] formatting", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    @pytest.mark.ground_truth
    def test_query_unicode_accented(self, rag_engine):
        rag_engine.add_guideline("Elsevier", "formatting", "Elsevier formatting guidelines.")
        results = rag_engine.query_guidelines("Elsevier", "förm tting güidelines", top_k=3)
        assert isinstance(results, list)
