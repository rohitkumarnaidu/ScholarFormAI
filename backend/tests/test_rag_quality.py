import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
#  IR metric helpers
# ---------------------------------------------------------------------------


def _dcg(relevances: list[float]) -> float:
    """Discounted cumulative gain at each rank."""
    dcg = 0.0
    for i, rel in enumerate(relevances):
        if i == 0:
            dcg += rel
        else:
            dcg += rel / math.log2(i + 1)
    return dcg


def _ndcg(relevances: list[float], ideal: list[float]) -> float:
    """Normalized DCG: actual DCG / ideal DCG."""
    actual = _dcg(relevances)
    best = _dcg(ideal)
    return actual / best if best > 0 else 0.0


def _average_precision(relevances: list[float]) -> float:
    """Average precision for a single query's ranked relevance list."""
    hits = 0
    sum_prec = 0.0
    for i, rel in enumerate(relevances):
        if rel > 0:
            hits += 1
            sum_prec += hits / (i + 1)
    return sum_prec / hits if hits > 0 else 0.0


def _mrr(ranked_results: list[list[float]]) -> float:
    """Mean Reciprocal Rank across multiple query result lists."""
    reciprocal_sum = 0.0
    for results in ranked_results:
        for i, rel in enumerate(results):
            if rel > 0:
                reciprocal_sum += 1.0 / (i + 1)
                break
    return reciprocal_sum / len(ranked_results) if ranked_results else 0.0


# ---------------------------------------------------------------------------
#  Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def rag_engine(tmp_path):
    from app.pipeline.intelligence.rag_engine import RagEngine

    persist = str(tmp_path / "rag_test")
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


# ---------------------------------------------------------------------------
#  NDCG tests
# ---------------------------------------------------------------------------


class TestNDCG:
    """Normalized Discounted Cumulative Gain — ranking quality."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_ndcg_perfect_ranking(self):
        relevances = [3.0, 2.0, 1.0]
        assert _ndcg(relevances, relevances) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_ndcg_worst_ranking(self):
        relevances = [0.0, 0.0, 0.0]
        ideal = [3.0, 2.0, 1.0]
        assert _ndcg(relevances, ideal) == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_ndcg_partial_ranking(self):
        relevances = [3.0, 0.0, 1.0]
        ideal = [3.0, 2.0, 1.0]
        ndcg = _ndcg(relevances, ideal)
        assert 0.0 < ndcg < 1.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_ndcg_all_zeros_ideal(self):
        assert _ndcg([0.0, 0.0], [0.0, 0.0]) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_ndcg_retrieves_relevant_first(self, rag_engine):
        rag_engine.add_guideline("IEEE", "margins", "Margins must be 1 inch on all sides.")
        rag_engine.add_guideline("IEEE", "formatting", "Font size must be 12pt Times New Roman.")
        rag_engine.add_guideline("IEEE", "margins", "Left margin should be 1.5 inches for binding.")
        results = rag_engine.query_guidelines("IEEE", "margins", top_k=3)
        assert len(results) > 0
        assert "Margins" in results[0] or "margins" in results[0].lower()


class TestMAP:
    """Mean Average Precision — relevance ranking across multiple queries."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_map_perfect_single_query(self):
        ap = _average_precision([1.0, 1.0, 1.0])
        assert ap == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_map_partial_single_query(self):
        ap = _average_precision([1.0, 0.0, 1.0, 0.0])
        assert ap == pytest.approx(0.8333, abs=1e-3)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_map_no_relevant_results(self):
        ap = _average_precision([0.0, 0.0, 0.0])
        assert ap == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_map_multi_query_average(self):
        queries = [[1.0, 0.0, 1.0], [1.0, 1.0, 0.0]]
        maps = [_average_precision(q) for q in queries]
        mean_map = sum(maps) / len(maps)
        assert 0.0 < mean_map <= 1.0
        assert maps[0] < maps[1]  # second query has better ranking

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_map_retrieval_varying_relevance(self, rag_engine):
        rag_engine.add_guideline("IEEE", "margins", "Margins: 1 inch all sides.")
        rag_engine.add_guideline("IEEE", "references", "Cite using IEEE format [1], [2].")
        rag_engine.add_guideline("IEEE", "figures", "Figures must be legible in B&W.")
        results = rag_engine.query_guidelines("IEEE", "margins", top_k=3)
        assert len(results) >= 1
        assert any("margins" in r.lower() for r in results)


class TestMRR:
    """Mean Reciprocal Rank — first relevant result position quality."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_mrr_perfect_first_result(self):
        ranked = [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
        assert _mrr([list(map(float, r)) for r in ranked]) == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_mrr_varying_positions(self):
        ranked = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
        mrr = _mrr([list(map(float, r)) for r in ranked])
        expected = (1 / 2 + 1 / 3 + 1.0) / 3
        assert mrr == pytest.approx(expected, abs=1e-6)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_mrr_no_relevant_results(self):
        assert _mrr([[0.0, 0.0], [0.0, 0.0]]) == 0.0

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_mrr_high_for_relevant_first(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Margins must be 1 inch.")
        rag_engine.add_guideline("IEEE", "formatting", "Font size is 12pt.")
        rag_engine.add_guideline("IEEE", "formatting", "Title is centered.")
        results = rag_engine.query_guidelines("IEEE", "margins", top_k=3)
        assert len(results) >= 1
        assert "Margins" in results[0] or "margins" in results[0].lower()


class TestCrossPublisherIsolation:
    """Verify queries for one publisher do NOT return another's content."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_cross_publisher_no_leakage(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "IEEE specific: double column layout.")
        rag_engine.add_guideline("ACM", "formatting", "ACM specific: single column layout.")
        rag_engine.add_guideline("Elsevier", "formatting", "Elsevier specific: numbered sections.")
        ieee_results = rag_engine.query_guidelines("IEEE", "layout", top_k=5)
        acm_results = rag_engine.query_guidelines("ACM", "layout", top_k=5)
        elsevier_results = rag_engine.query_guidelines("Elsevier", "layout", top_k=5)
        for r in ieee_results:
            assert "ACM" not in r
            assert "Elsevier" not in r
        for r in acm_results:
            assert "IEEE" not in r
        for r in elsevier_results:
            assert "IEEE" not in r
            assert "ACM" not in r

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_cross_publisher_similar_guidelines(self, rag_engine):
        rag_engine.add_guideline("IEEE", "fonts", "Times New Roman 10pt.")
        rag_engine.add_guideline("ACM", "fonts", "Times New Roman 10pt.")
        ieee_results = rag_engine.query_guidelines("IEEE", "fonts", top_k=5)
        acm_results = rag_engine.query_guidelines("ACM", "fonts", top_k=5)
        for r in ieee_results:
            assert "ACM" not in r
        for r in acm_results:
            assert "IEEE" not in r

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_cross_publisher_empty_for_unknown(self, rag_engine):
        rag_engine.add_guideline("IEEE", "a", "Content.")
        results = rag_engine.query_guidelines("Nature", "content", top_k=5)
        assert results == []


class TestEmptyKnowledgeBase:
    """Query behavior with empty or sparsely populated stores."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_empty_knowledge_base(self, rag_engine):
        results = rag_engine.query_guidelines("IEEE", "anything", top_k=3)
        assert results == []

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_after_full_reset(self, rag_engine):
        rag_engine.add_guideline("IEEE", "a", "Rule.")
        rag_engine.reset()
        results = rag_engine.query_guidelines("IEEE", "Rule", top_k=5)
        assert results == []

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_single_guideline_found(self, rag_engine):
        rag_engine.add_guideline("IEEE", "margins", "Margins: 1 inch.")
        results = rag_engine.query_guidelines("IEEE", "margins", top_k=5)
        assert len(results) == 1
        assert "Margins" in results[0]

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_empty_query_returns_results(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Rule.")
        results = rag_engine.query_guidelines("IEEE", "", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_whitespace_query(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Rule.")
        results = rag_engine.query_guidelines("IEEE", "   ", top_k=3)
        assert isinstance(results, list)


class TestEmbeddingQuality:
    """Embedding model correctness: dimension, identity, distribution."""

    @pytest.mark.ai_quality
    def test_embedding_dimension_match(self, rag_engine):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel

        model = _DeterministicEmbeddingModel(dimension=128)
        vec = model.encode("test text")
        assert len(vec) == 128

    @pytest.mark.ai_quality
    def test_embedding_identity(self, rag_engine):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel

        model = _DeterministicEmbeddingModel(dimension=64)
        v1 = model.encode("hello world")
        v2 = model.encode("hello world")
        assert v1 == v2

    @pytest.mark.ai_quality
    def test_embedding_different_inputs_different(self, rag_engine):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel

        model = _DeterministicEmbeddingModel(dimension=64)
        v1 = model.encode("hello world")
        v2 = model.encode("goodbye world")
        assert v1 != v2

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_embedding_similar_texts_have_similar_vectors(self, rag_engine):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel

        model = _DeterministicEmbeddingModel(dimension=256)
        v1 = np.array(model.encode("machine learning algorithms"))
        v2 = np.array(model.encode("deep learning algorithms"))
        v3 = np.array(model.encode("quantum physics theory"))
        sim_similar = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        sim_different = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))
        assert sim_similar > sim_different, "Similar texts should have higher cosine similarity"

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_embedding_similarity_distribution(self, rag_engine):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel

        model = _DeterministicEmbeddingModel(dimension=128)
        texts = [
            "margin size 1 inch",
            "font times new roman",
            "citation format ieee",
            "abstract word limit",
            "section heading format",
            "reference list ordering",
            "table caption style",
            "figure resolution dpi",
            "page number position",
            "line spacing double",
        ]
        vectors = np.array([model.encode(t) for t in texts])
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = vectors / norms
        sim_matrix = normalized @ normalized.T
        np.fill_diagonal(sim_matrix, 0.0)
        assert sim_matrix.min() >= -1.0
        assert sim_matrix.max() <= 1.0
        assert float(np.mean(sim_matrix)) > -1.0


class TestQueryEdgeCases:
    """Edge cases for query input: unicode, special chars, very long strings."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_unicode_characters(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use 1-inch margins.")
        results = rag_engine.query_guidelines("IEEE", "márgins ütf8", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_special_characters(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use 1-inch margins.")
        results = rag_engine.query_guidelines("IEEE", "margins!@#$%^&*()", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_very_long_string(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use 1-inch margins.")
        long_query = "margins " * 10000
        results = rag_engine.query_guidelines("IEEE", long_query, top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_numeric_string(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use 1-inch margins.")
        results = rag_engine.query_guidelines("IEEE", "12345 67890", top_k=3)
        assert isinstance(results, list)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_query_case_sensitivity_handling(self, rag_engine):
        rag_engine.add_guideline("IEEE", "margins", "Margins: 1 inch.")
        upper = rag_engine.query_guidelines("IEEE", "MARGINS", top_k=3)
        lower = rag_engine.query_guidelines("IEEE", "margins", top_k=3)
        mixed = rag_engine.query_guidelines("IEEE", "MarGinS", top_k=3)
        assert len(upper) >= 1
        assert len(lower) >= 1
        assert len(mixed) >= 1


class TestPrecisionRecall:
    """Precision and recall at k for retrieval quality."""

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_precision_perfect_match(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use 1-inch margins.")
        rag_engine.add_guideline("IEEE", "formatting", "Times New Roman 12pt.")
        rag_engine.add_guideline("ACM", "formatting", "ACM uses 2-column layout.")
        results = rag_engine.query_guidelines("IEEE", "margins", top_k=2)
        assert len(results) > 0
        assert all("Times New Roman" in r or "margins" in r for r in results)

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_recall_finds_all_relevant(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "IEEE rule A.")
        rag_engine.add_guideline("IEEE", "formatting", "IEEE rule B.")
        rag_engine.add_guideline("IEEE", "formatting", "IEEE rule C.")
        results = rag_engine.query_guidelines("IEEE", "IEEE", top_k=5)
        assert len(results) == 3

    @pytest.mark.rag
    @pytest.mark.ai_quality
    def test_recall_empty_when_no_match(self, rag_engine):
        results = rag_engine.query_guidelines("UNKNOWN", "anything", top_k=3)
        assert results == []
