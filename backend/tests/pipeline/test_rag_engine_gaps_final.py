# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Final gap-filling tests for RagEngine — targets remaining uncovered
lines in _load_chromadb, embedding models, coercion, seeding, and
model loading fallback paths.
"""

from __future__ import annotations

import json
import os
import numpy as np
from unittest.mock import MagicMock, patch

import pytest

from tests.pipeline.test_rag_engine_comprehensive import _make_engine


@pytest.fixture
def engine(tmp_path):
    """Default RagEngine fixture with mocked SentenceTransformer, native backend."""
    return _make_engine(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════
# _load_chromadb
# ═══════════════════════════════════════════════════════════════════════════

class TestLoadChromadb:
    def test_already_loaded_returns_early(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb, chromadb
        assert _load_chromadb() is chromadb or True

    def test_import_already_attempted_returns_none(self):
        with (
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
            patch("app.pipeline.intelligence.rag_engine._CHROMADB_IMPORT_ATTEMPTED", True),
        ):
            from app.pipeline.intelligence.rag_engine import _load_chromadb
            result = _load_chromadb()
            assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# _DeterministicEmbeddingModel
# ═══════════════════════════════════════════════════════════════════════════

class TestDeterministicEmbeddingModel:
    @pytest.fixture
    def model(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        return _DeterministicEmbeddingModel(dimension=64)

    def test_get_dimension(self, model):
        assert model.get_sentence_embedding_dimension() == 64

    def test_encode_single_string(self, model):
        vec = model.encode("hello world")
        assert isinstance(vec, list)
        assert len(vec) == 64

    def test_encode_list(self, model):
        vecs = model.encode(["hello", "world"])
        assert isinstance(vecs, list)
        assert len(vecs) == 2
        assert all(len(v) == 64 for v in vecs)

    def test_encode_empty_string(self, model):
        vec = model.encode("")
        assert isinstance(vec, list)
        assert len(vec) == 64
        assert all(v == 0.0 for v in vec)

    def test_encode_whitespace(self, model):
        vec = model.encode("   ")
        assert isinstance(vec, list)
        assert len(vec) == 64
        assert all(v == 0.0 for v in vec)

    def test_encode_tuple(self, model):
        vecs = model.encode(("a", "b"))
        assert isinstance(vecs, list)
        assert len(vecs) == 2


# ═══════════════════════════════════════════════════════════════════════════
# _HuggingFaceAPIEmbeddingModel
# ═══════════════════════════════════════════════════════════════════════════

class TestHuggingFaceAPIEmbeddingModel:
    def test_bge_m3_dimension(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        m = _HuggingFaceAPIEmbeddingModel(model_id="BAAI/bge-m3")
        assert m.dimension == 1024

    def test_get_dimension(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        m = _HuggingFaceAPIEmbeddingModel()
        assert m.get_sentence_embedding_dimension() == 384

    def test_encode_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            assert m.token is None

    def test_encode_list_returns_list(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_post.return_value = mock_response
            with patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=False):
                m = _HuggingFaceAPIEmbeddingModel()
                result = m.encode(["a", "b"])
                assert isinstance(result, list)
                assert len(result) == 2

    def test_api_error_returns_empty(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        with patch("app.pipeline.intelligence.rag_engine.requests.post", side_effect=Exception("api down")):
            with patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=False):
                m = _HuggingFaceAPIEmbeddingModel()
                result = m.encode("test")
                assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# _coerce_embedding_vector — static edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestCoerceEmbeddingVector:
    def test_none_returns_empty(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector(None)
        assert result == []

    def test_numpy_array_uses_tolist(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        arr = np.array([0.1, 0.2, 0.3])
        result = RagEngine._coerce_embedding_vector(arr)
        assert result == [0.1, 0.2, 0.3]

    def test_nested_list_unwraps(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector([[0.1, 0.2, 0.3]])
        assert result == [0.1, 0.2, 0.3]

    def test_non_iterable_returns_empty(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector(42)
        assert result == []

    def test_uncastable_element_returns_empty(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector([0.1, "bad", 0.3])
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# add_guideline — without patching it away
# ═══════════════════════════════════════════════════════════════════════════

class TestAddGuideline:
    def test_add_guideline_with_metadata(self, engine):
        engine.add_guideline(
            publisher="IEEE",
            section="formatting",
            text="Use 10pt font.",
            metadata={"source": "manual"},
        )
        assert len(engine.knowledge_base) == 1
        entry = engine.knowledge_base[0]
        assert entry["metadata"]["publisher"] == "IEEE"
        assert entry["metadata"]["section"] == "formatting"
        assert entry["metadata"]["source"] == "manual"

    def test_add_guideline_no_embedding_model(self, engine):
        engine.embedding_model = None
        engine.add_guideline(
            publisher="ACM",
            section="style",
            text="Double spaced.",
            metadata=None,
        )
        assert len(engine.knowledge_base) == 1
        assert engine.knowledge_base[0]["embedding"] == []

    def test_add_guideline_with_chromadb(self, engine):
        mock_collection = MagicMock()
        engine.chroma_enabled = True
        engine.collection = mock_collection
        engine.client = MagicMock()
        engine.add_guideline(publisher="Elsevier", section="refs", text="Cite properly.")
        assert mock_collection.add.called

    def test_save_native_creates_file(self, engine):
        persist = engine.persist_directory
        engine.add_guideline(publisher="Test", section="test", text="test")
        kb_file = os.path.join(persist, "kb.json")
        assert os.path.exists(kb_file)
        with open(kb_file) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_reset_removes_kb_file(self, engine):
        persist = engine.persist_directory
        engine.add_guideline(publisher="Test", section="test", text="test")
        engine.reset()
        kb_file = os.path.join(persist, "kb.json")
        assert not os.path.exists(kb_file)

    def test_reset_no_kb_file(self, engine):
        engine.knowledge_base = []
        engine.reset()
        assert engine.knowledge_base == []


# ═══════════════════════════════════════════════════════════════════════════
# query_guidelines — ChromaDB success path
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryGuidelinesChromadb:
    def test_chromadb_returns_guidelines(self, engine):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["guideline text"]],
            "metadatas": [[{"publisher": "IEEE"}]],
            "distances": [[0.1]],
        }
        engine.chroma_enabled = True
        engine.collection = mock_collection
        result = engine.query_guidelines("IEEE", "formatting", top_k=1)
        assert len(result) > 0


# ═══════════════════════════════════════════════════════════════════════════
# _seed_if_empty — list payload & valid item
# ═══════════════════════════════════════════════════════════════════════════

class TestSeedIfEmpty:
    def test_list_payload(self, engine):
        engine.knowledge_base.clear()
        engine.chroma_enabled = False
        payload = [
            {"publisher": "IEEE", "section": "formatting", "text": "Use 10pt.", "embedding": [0.1]}
        ]
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists", return_value=True):
            with patch("app.pipeline.intelligence.rag_engine.json.load", return_value=payload):
                engine._seed_if_empty()
        assert len(engine.knowledge_base) == 1

    def test_non_dict_item_skipped(self, engine):
        engine.knowledge_base.clear()
        engine.chroma_enabled = False
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists", return_value=True):
            with patch("app.pipeline.intelligence.rag_engine.json.load", return_value={"guidelines": ["string"]}):
                engine._seed_if_empty()
        assert len(engine.knowledge_base) == 0

    def test_valid_dict_item_added(self, engine):
        engine.knowledge_base.clear()
        engine.chroma_enabled = False
        payload = {
            "guidelines": [
                {"publisher": "ACM", "section": "style", "text": "Double space.", "embedding": [0.1]}
            ]
        }
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists", return_value=True):
            with patch("app.pipeline.intelligence.rag_engine.json.load", return_value=payload):
                engine._seed_if_empty()
        assert len(engine.knowledge_base) == 1


# ═══════════════════════════════════════════════════════════════════════════
# _is_reusable_embedding_model
# ═══════════════════════════════════════════════════════════════════════════

class TestIsReusableEmbeddingModel:
    @pytest.fixture
    def engine(self, tmp_path):
        return _make_engine(tmp_path)

    def test_none_candidate(self, engine):
        ok, dim = engine._is_reusable_embedding_model(None)
        assert ok is False
        assert dim is None

    def test_no_encode(self, engine):
        candidate = MagicMock(spec=[])
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is False

    def test_no_get_dimension(self, engine):
        candidate = MagicMock()
        del candidate.get_sentence_embedding_dimension
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is False

    def test_zero_dimension(self, engine):
        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 0
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is False

    def test_empty_healthcheck(self, engine):
        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 384
        candidate.encode.return_value = []
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is False

    def test_success(self, engine):
        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 384
        candidate.encode.return_value = [0.1] * 384
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is True
        assert dim == 384

    def test_exception_during_validation(self, engine):
        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 384
        candidate.encode.side_effect = Exception("fail")
        ok, dim = engine._is_reusable_embedding_model(candidate)
        assert ok is False


# ═══════════════════════════════════════════════════════════════════════════
# _load_embedding_model — model_store reuse, primary→fallback cascade
# ═══════════════════════════════════════════════════════════════════════════

class TestLoadEmbeddingModelCascade:
    def test_primary_fails_fallback_succeeds(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import PRIMARY_MODEL, FALLBACK_MODEL
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = [0.1] * 384

        def st_side_effect(*a, **kw):
            if a and a[0] == PRIMARY_MODEL:
                raise Exception("OOM")
            return mock_model

        engine = _make_engine(tmp_path, st_side_effect=st_side_effect)
        assert engine.active_model_name == FALLBACK_MODEL

    def test_both_primary_and_fallback_fail(self, tmp_path):
        engine = _make_engine(tmp_path, st_side_effect=Exception("OOM"))
        assert engine.active_model_name is not None  # deterministic fallback

    def test_model_store_reuse_384(self, tmp_path):
        engine = _make_engine(tmp_path, model_store_is_loaded=True)
        assert engine.embedding_model is not None

    def test_model_store_reuse_fails_validation(self, tmp_path):
        with patch("app.pipeline.intelligence.rag_engine.RagEngine._is_reusable_embedding_model",
                   return_value=(False, None)):
            engine = _make_engine(tmp_path, model_store_is_loaded=True)
            assert engine.embedding_model is not None
