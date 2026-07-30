# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
import json
import math

import numpy as np
import pytest

pytestmark = pytest.mark.slow

from app.pipeline.agents.deep_learning import TransformerPatternDetector


class TestInit:
    def test_fallback_mode_no_torch(self):
        d = TransformerPatternDetector()
        assert d.tokenizer is None
        assert d.model is None
        assert d.device == "cpu"

    def test_default_model_name(self):
        d = TransformerPatternDetector()
        assert d.model_name == "allenai/scibert_scivocab_uncased"


class TestEncode:
    def test_encode_document_no_model_returns_zeros(self):
        d = TransformerPatternDetector()
        emb = d.encode_document("test document")
        assert isinstance(emb, np.ndarray) and emb.shape == (768,) and np.all(emb == 0.0)

    def test_encode_document_cache_hit(self):
        d = TransformerPatternDetector()
        d.embeddings_cache["test document"] = np.ones(768)
        emb = d.encode_document("test document")
        assert np.all(emb == 1.0)

    def test_encode_metadata_full(self):
        d = TransformerPatternDetector()
        emb = d.encode_metadata({"title": "Paper", "authors": ["A"], "abstract": "Abs", "venue": "N"})
        assert emb.shape == (768,) and np.all(emb == 0.0)

    def test_encode_metadata_partial(self):
        d = TransformerPatternDetector()
        emb = d.encode_metadata({"title": "Only"})
        assert emb.shape == (768,) and np.all(emb == 0.0)

    def test_encode_metadata_empty(self):
        d = TransformerPatternDetector()
        emb = d.encode_metadata({})
        assert emb.shape == (768,) and np.all(emb == 0.0)


class TestClustering:
    def test_fit_insufficient_data(self):
        d = TransformerPatternDetector()
        assert d.fit_clusters([np.zeros(768)] * 3, n_clusters=5) is False

    def test_fit_sufficient_data(self):
        d = TransformerPatternDetector()
        np.random.seed(42)
        embs = [np.random.rand(768) for _ in range(10)]
        assert d.fit_clusters(embs, n_clusters=3) is True
        assert d.clusters is not None and d.cluster_centers is not None

    def test_predict_cluster_untrained_returns_neg1(self):
        d = TransformerPatternDetector()
        assert d.predict_cluster(np.zeros(768)) == -1

    def test_predict_cluster_trained(self):
        d = TransformerPatternDetector()
        np.random.seed(42)
        embs = [np.random.rand(768) for _ in range(10)]
        d.fit_clusters(embs, n_clusters=3)
        assert isinstance(d.predict_cluster(embs[0]), int)


class TestSimilarity:
    def test_similar_vectors(self):
        d = TransformerPatternDetector()
        sim = d.compute_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
        assert abs(sim - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        d = TransformerPatternDetector()
        sim = d.compute_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
        assert abs(sim) < 1e-6

    def test_zero_vectors_returns_nan(self):
        d = TransformerPatternDetector()
        sim = d.compute_similarity(np.zeros(768), np.zeros(768))
        assert math.isnan(sim)

    def test_find_similar_documents(self):
        d = TransformerPatternDetector()
        docs = [("a", np.array([1.0, 0.0])), ("b", np.array([0.0, 1.0]))]
        results = d.find_similar_documents(np.array([1.0, 0.0]), docs, top_k=2)
        assert len(results) == 2 and results[0][0] == "a"

    def test_find_similar_empty_list(self):
        d = TransformerPatternDetector()
        assert d.find_similar_documents(np.array([1.0, 0.0]), []) == []


class TestAnomaly:
    def test_no_cluster_centers(self):
        d = TransformerPatternDetector()
        is_anom, score = d.detect_anomaly_semantic(np.zeros(768))
        assert is_anom is False and score == 0.0

    def test_with_centers(self):
        d = TransformerPatternDetector()
        np.random.seed(42)
        embs = [np.random.rand(768) for _ in range(10)]
        d.fit_clusters(embs, n_clusters=3)
        is_anom, score = d.detect_anomaly_semantic(embs[0], threshold=0.1)
        assert isinstance(is_anom, bool) and 0.0 <= score <= 1.0

    def test_below_threshold(self):
        d = TransformerPatternDetector()
        d.cluster_centers = np.array([[1.0, 0.0], [0.0, 1.0]])
        is_anom, score = d.detect_anomaly_semantic(np.array([-1.0, -1.0]), threshold=0.9)
        assert is_anom is True


class TestSaveLoad:
    def test_save_no_cache(self, tmp_path):
        d = TransformerPatternDetector()
        d.save_model(str(tmp_path / "model.json"))
        saved = json.loads(tmp_path.joinpath("model.json").read_text())
        assert saved["cluster_centers"] is None

    def test_save_with_cache(self, tmp_path):
        d = TransformerPatternDetector()
        d.embeddings_cache["doc1"] = np.ones(768)
        d.save_model(str(tmp_path / "model.json"))
        assert tmp_path.joinpath("model.json.embeddings.npy").exists()


class TestSummary:
    def test_untrained(self):
        s = TransformerPatternDetector().get_summary()
        assert s["clusters_trained"] is False and s["n_clusters"] == 0

    def test_trained(self):
        d = TransformerPatternDetector()
        np.random.seed(42)
        d.fit_clusters([np.random.rand(768) for _ in range(10)], n_clusters=3)
        s = d.get_summary()
        assert s["clusters_trained"] is True and s["n_clusters"] == 3
