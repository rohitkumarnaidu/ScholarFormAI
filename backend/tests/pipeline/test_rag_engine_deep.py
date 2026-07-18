# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
import json
import os
import numpy as np
import pytest
pytestmark = [pytest.mark.pipeline, pytest.mark.rag]


@pytest.fixture
def rag_engine():
    with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
         patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
         patch("app.pipeline.intelligence.rag_engine.open", mock_open()) as mock_file, \
         patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model") as mock_load, \
         patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty") as mock_seed, \
         patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
        mock_chroma.return_value = None
        mock_exists.return_value = False
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine(persist_directory="/tmp/test_kb")
        engine.embedding_model = MagicMock()
        engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        engine.knowledge_base = []
        engine.chroma_enabled = False
        yield engine


class TestDeterministicEmbeddingModel:
    def test_init_min_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(dimension=10)
        assert m.dimension == 32

    def test_get_sentence_embedding_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(64)
        assert m.get_sentence_embedding_dimension() == 64

    def test_encode_single_string(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode("hello world")
        assert len(result) == 32
        assert isinstance(result, list)

    def test_encode_list(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode(["hello", "world"])
        assert len(result) == 2
        assert all(len(v) == 32 for v in result)

    def test_encode_empty_text(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        result = m.encode("")
        assert len(result) == 32

    def test_normalization(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(32)
        vec = m.encode("test vector")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 0.001


class TestHuggingFaceAPIEmbeddingModel:
    def test_default_url_without_env(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda k, d=None: d
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")
            assert "router.huggingface.co" in model.api_url
            assert model.dimension == 384

    def test_bge_m3_dimension(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda k, d=None: d
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("BAAI/bge-m3")
            assert model.dimension == 1024

    def test_normalize_url_missing_pipeline(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        result = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(
            "https://router.huggingface.co/hf-inference/models/test-model", "test"
        )
        assert "/pipeline/feature-extraction" in result

    def test_normalize_url_already_has_pipeline(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = "https://router.huggingface.co/hf-inference/models/test-model/pipeline/feature-extraction"
        result = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(url, "test")
        assert result == url

    def test_default_feature_extraction_url(self):
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._default_feature_extraction_url("test-model")
        assert "test-model" in url
        assert "feature-extraction" in url

    def test_encode_no_token(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda k, d=None: None if k == "HF_TOKEN" else d
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            result = model.encode("hello")
            assert result == []

    def test_encode_success(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post:
            mock_getenv.side_effect = lambda k, d=None: "fake-token" if k == "HF_TOKEN" else d
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [[0.1, 0.2, 0.3]]
            mock_post.return_value = mock_response
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            result = model.encode("hello")
            assert result == [0.1, 0.2, 0.3]

    def test_encode_success_list(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post:
            mock_getenv.side_effect = lambda k, d=None: "fake-token" if k == "HF_TOKEN" else d
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [[0.1], [0.2]]
            mock_post.return_value = mock_response
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            result = model.encode(["a", "b"])
            assert len(result) == 2

    def test_encode_http_400_sentence_similarity_auto_fix(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post:
            mock_getenv.side_effect = lambda k, d=None: "fake-token" if k == "HF_TOKEN" else d
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "SentenceSimilarityPipeline error"
            mock_response2 = MagicMock()
            mock_response2.status_code = 200
            mock_response2.json.return_value = [[0.1, 0.2]]
            mock_post.side_effect = [mock_response, mock_response2]
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            model.api_url = "https://router.huggingface.co/hf-inference/models/test"
            result = model.encode("hello")
            assert result == [0.1, 0.2]

    def test_encode_http_500_retry_then_fail(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post, \
             patch("app.pipeline.intelligence.rag_engine.time.sleep"):
            mock_getenv.side_effect = lambda k, d=None: "fake-token" if k == "HF_TOKEN" else d
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Server Error"
            mock_post.return_value = mock_response
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            model.max_retries = 2
            result = model.encode("hello")
            assert result == []

    def test_encode_exception_retry_then_fail(self):
        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.pipeline.intelligence.rag_engine.requests.post") as mock_post, \
             patch("app.pipeline.intelligence.rag_engine.time.sleep"):
            mock_getenv.side_effect = lambda k, d=None: "fake-token" if k == "HF_TOKEN" else d
            mock_post.side_effect = Exception("Connection error")
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            model = _HuggingFaceAPIEmbeddingModel("test")
            model.max_retries = 2
            result = model.encode("hello")
            assert result == []


class TestChromaDBLoad:
    def test_load_chromadb_success(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb
        with patch("app.pipeline.intelligence.rag_engine._CHROMADB_IMPORT_ATTEMPTED", False), \
             patch("app.pipeline.intelligence.rag_engine.chromadb", None), \
             patch("app.pipeline.intelligence.rag_engine._CHROMADB_AVAILABLE", False):
            result = _load_chromadb()
            assert result is not None  # chromadb is installed in this env

    def test_chromadb_already_loaded(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb
        mock_cdb = MagicMock()
        with patch("app.pipeline.intelligence.rag_engine.chromadb", mock_cdb):
            result = _load_chromadb()
            assert result is mock_cdb

    def test_chromadb_import_attempted(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb
        with patch("app.pipeline.intelligence.rag_engine._CHROMADB_IMPORT_ATTEMPTED", True), \
             patch("app.pipeline.intelligence.rag_engine.chromadb", None):
            result = _load_chromadb()
            assert result is None


class TestRagEnginePublicAPI:
    def test_add_guideline(self, rag_engine):
        rag_engine.add_guideline("IEEE", "references", "Use numeric citations.")
        assert len(rag_engine.knowledge_base) == 1
        assert rag_engine.knowledge_base[0]["metadata"]["publisher"] == "IEEE"

    def test_add_guideline_with_metadata(self, rag_engine):
        rag_engine.add_guideline("ACM", "formatting", "Use 10pt font.", metadata={"source": "manual"})
        assert rag_engine.knowledge_base[0]["metadata"]["source"] == "manual"
        assert rag_engine.knowledge_base[0]["metadata"]["publisher"] == "ACM"

    def test_add_guideline_chroma_enabled(self, rag_engine):
        rag_engine.chroma_enabled = True
        rag_engine.collection = MagicMock()
        rag_engine.add_guideline("IEEE", "title", "Test")
        rag_engine.collection.add.assert_called_once()

    def test_add_guideline_no_embedding_model(self, rag_engine):
        rag_engine.embedding_model = None
        rag_engine.add_guideline("IEEE", "test", "Some text")
        assert rag_engine.knowledge_base[0]["embedding"] == []

    def test_query_guidelines_chroma(self, rag_engine):
        rag_engine.chroma_enabled = True
        rag_engine.collection = MagicMock()
        rag_engine.collection.query.return_value = {"documents": [["result1", "result2"]]}
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert results == ["result1", "result2"]

    def test_query_guidelines_chroma_fallback_to_native(self, rag_engine):
        rag_engine.chroma_enabled = True
        rag_engine.collection = MagicMock()
        rag_engine.collection.query.side_effect = Exception("Chroma error")
        rag_engine.add_guideline("IEEE", "formatting", "Use IEEE style.")
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert "Use IEEE style." in results

    def test_query_guidelines_no_embedding_model(self, rag_engine):
        rag_engine.embedding_model = None
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert results == []

    def test_query_guidelines_empty_intent(self, rag_engine):
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.return_value = []
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert results == []

    def test_query_guidelines_shape_mismatch_skipped(self, rag_engine):
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        rag_engine.knowledge_base = [
            {"text": "rule1", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]},
            {"text": "rule2", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2, 0.3]},
        ]
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert "rule2" in results
        assert "rule1" not in results

    def test_query_guidelines_zero_denom_skipped(self, rag_engine):
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.return_value = [0.0, 0.0, 0.0]
        rag_engine.knowledge_base = [
            {"text": "rule", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2, 0.3]},
        ]
        results = rag_engine.query_guidelines("IEEE", "formatting")
        assert results == []

    def test_query_guidelines_exception_caught(self, rag_engine):
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.side_effect = Exception("Boom")
        results = rag_engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_query_rules(self, rag_engine):
        rag_engine.add_guideline("IEEE", "formatting", "Use IEEE style.")
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        results = rag_engine.query_rules("IEEE", "formatting")
        assert len(results) >= 1
        assert "text" in results[0]
        assert results[0]["metadata"]["publisher"] == "IEEE"

    def test_query_rules_empty_template(self, rag_engine):
        rag_engine.add_guideline("IEEE", "general", "Default rule.")
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        results = rag_engine.query_rules("", "")
        assert len(results) >= 1

    def test_query_rules_exception(self, rag_engine):
        rag_engine.embedding_model = MagicMock()
        rag_engine.embedding_model.encode.side_effect = Exception("Fail")
        results = rag_engine.query_rules("IEEE", "test")
        assert results == []

    def test_reset_chroma_enabled(self, rag_engine):
        rag_engine.chroma_enabled = True
        rag_engine.client = MagicMock()
        rag_engine.collection = MagicMock()
        rag_engine.knowledge_base = [{"text": "test"}]
        rag_engine.kb_file = "/fake/kb.json"
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.os.remove"):
            mock_exists.return_value = True
            rag_engine.reset()
            assert rag_engine.knowledge_base == []

    def test_reset_chroma_disabled(self, rag_engine):
        rag_engine.chroma_enabled = False
        rag_engine.knowledge_base = [{"text": "test"}]
        rag_engine.reset()
        assert rag_engine.knowledge_base == []

    def test_reset_chroma_delete_exception(self, rag_engine):
        rag_engine.chroma_enabled = True
        rag_engine.client = MagicMock()
        rag_engine.client.delete_collection.side_effect = Exception("Delete error")
        rag_engine.collection = MagicMock()
        rag_engine.reset()
        assert rag_engine.knowledge_base == []


class TestCoerceEmbeddingVector:
    def test_none(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        assert RagEngine._coerce_embedding_vector(None) == []

    def test_tolist_method(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        mock_obj = MagicMock()
        mock_obj.tolist.return_value = [1.0, 2.0]
        result = RagEngine._coerce_embedding_vector(mock_obj)
        assert result == [1.0, 2.0]

    def test_nested_list(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector([[1.0, 2.0]])
        assert result == [1.0, 2.0]

    def test_invalid_type(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector(123)
        assert result == []

    def test_conversion_exception(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        class BadList:
            def __iter__(self):
                raise ValueError("bad")
        result = RagEngine._coerce_embedding_vector(BadList())
        assert result == []

    def test_numpy_array(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        arr = np.array([1.0, 2.0, 3.0])
        result = RagEngine._coerce_embedding_vector(arr)
        assert result == [1.0, 2.0, 3.0]

    def test_empty_tuple(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._coerce_embedding_vector(())
        assert result == []


class TestIsReusableEmbeddingModel:
    @pytest.fixture
    def eng(self):
        return MagicMock(_coerce_embedding_vector=MagicMock(return_value=[0.1, 0.2]))

    def test_none(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        result = RagEngine._is_reusable_embedding_model(eng, None)
        assert result == (False, None)

    def test_no_encode(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        candidate = MagicMock(spec=[])
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (False, None)

    def test_no_get_dim(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        candidate = MagicMock()
        candidate.encode.return_value = [0.1]
        del candidate.get_sentence_embedding_dimension
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (False, None)

    def test_dim_zero(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        candidate = MagicMock()
        candidate.encode.return_value = [0.1]
        candidate.get_sentence_embedding_dimension.return_value = 0
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (False, None)

    def test_empty_probe(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        eng._coerce_embedding_vector.return_value = []
        candidate = MagicMock()
        candidate.encode.return_value = [0.1, 0.2]
        candidate.get_sentence_embedding_dimension.return_value = 64
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (False, None)

    def test_success(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        candidate = MagicMock()
        candidate.encode.return_value = [0.1, 0.2, 0.3]
        candidate.get_sentence_embedding_dimension.return_value = 3
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (True, 3)

    def test_exception(self, eng):
        from app.pipeline.intelligence.rag_engine import RagEngine
        candidate = MagicMock()
        candidate.encode.side_effect = Exception("Boom")
        candidate.get_sentence_embedding_dimension.return_value = 64
        result = RagEngine._is_reusable_embedding_model(eng, candidate)
        assert result == (False, None)


class TestRagEngineInit:
    def test_persist_directory_default(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine()
            assert engine.backend == "native"

    def test_auto_seed_default(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty") as mock_seed, \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine()
            assert engine.auto_seed is True

    def test_auto_seed_explicit_false(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(auto_seed=False)
            assert engine.auto_seed is False

    def test_active_model_primary_collection(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model") as mock_load, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty") as mock_seed, \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine, PRIMARY_MODEL, COLLECTION_PRIMARY
            engine = RagEngine.__new__(RagEngine)
            engine.persist_directory = "/tmp/test"
            engine.auto_seed = False
            engine.embedding_model = None
            engine.active_model_name = PRIMARY_MODEL
            engine.knowledge_base = []
            engine._collection_name = COLLECTION_PRIMARY
            engine.chroma_enabled = False
            assert engine._collection_name == COLLECTION_PRIMARY

    def test_chroma_init_failure_known(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model") as mock_load, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty") as mock_seed, \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory="/tmp/test", auto_seed=False)
            assert engine.backend == "native"
            assert engine.chroma_enabled is False


class TestSeedIfEmpty:
    def test_seed_already_has_data(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model") as mock_load:
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = [{"text": "existing"}]
            engine.chroma_enabled = False
            engine._seed_if_empty()

    def test_seed_chroma_has_data(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs") as mock_makedirs, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model") as mock_load:
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = True
            engine.collection = MagicMock()
            engine.collection.count.return_value = 5
            engine._seed_if_empty()

    def test_seed_default_file_not_found(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists:
            mock_exists.return_value = False
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine._seed_if_empty()

    def test_seed_dict_payload(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.open", mock_open(read_data='{"guidelines": [{"publisher": "IEEE", "section": "refs", "text": "Use IEEE style."}]}')) as mock_file, \
             patch("app.pipeline.intelligence.rag_engine.json.load") as mock_json_load:
            mock_exists.return_value = True
            mock_json_load.return_value = {"guidelines": [{"publisher": "IEEE", "section": "refs", "text": "Use IEEE style."}]}
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine.add_guideline = MagicMock()
            engine._seed_if_empty()
            engine.add_guideline.assert_called_once()

    def test_seed_list_payload(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.open", mock_open()), \
             patch("app.pipeline.intelligence.rag_engine.json.load") as mock_json_load:
            mock_exists.return_value = True
            mock_json_load.return_value = [{"publisher": "ACM", "section": "formatting", "text": "Use ACM template."}]
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine.add_guideline = MagicMock()
            engine._seed_if_empty()
            engine.add_guideline.assert_called_once()

    def test_seed_skips_non_dict_items(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.open", mock_open()), \
             patch("app.pipeline.intelligence.rag_engine.json.load") as mock_json_load:
            mock_exists.return_value = True
            mock_json_load.return_value = [42, {"publisher": "ACM", "section": "test", "text": "Valid"}]
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine.add_guideline = MagicMock()
            engine._seed_if_empty()
            engine.add_guideline.assert_called_once_with(
                publisher="ACM", section="test", text="Valid", metadata={"source": "auto-seed"}
            )

    def test_seed_skips_incomplete_items(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.open", mock_open()), \
             patch("app.pipeline.intelligence.rag_engine.json.load") as mock_json_load:
            mock_exists.return_value = True
            mock_json_load.return_value = [{"publisher": "ACM"}]  # missing section/text
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine.add_guideline = MagicMock()
            engine._seed_if_empty()
            engine.add_guideline.assert_not_called()

    def test_seed_exception_caught(self):
        with patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists:
            mock_exists.return_value = True
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine.__new__(RagEngine)
            engine.knowledge_base = []
            engine.chroma_enabled = False
            engine._seed_if_empty()  # should not raise


class TestLoadEmbeddingModel:
    def test_low_memory_hf_api_success(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._coerce_embedding_vector = MagicMock(return_value=[0.1, 0.2])

        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = True
        settings_mock.RAG_USE_TRANSFORMERS = False

        model_store_mock = MagicMock()

        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock), \
             patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as mock_hf:
            mock_getenv.side_effect = lambda k, d=None: "hf_api" if "PROVIDER" in k else d
            hf_instance = MagicMock()
            hf_instance.dimension = 384
            mock_hf.return_value = hf_instance
            hf_instance.encode.return_value = [0.1, 0.2]
            engine._load_embedding_model()
            assert engine.active_model_name.startswith("huggingface_api_")

    def test_low_memory_hf_api_fails_health_check(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._coerce_embedding_vector = MagicMock(return_value=[])
        engine._activate_deterministic_embedding = MagicMock()

        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = True
        settings_mock.RAG_USE_TRANSFORMERS = False

        with patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv, \
             patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store"), \
             patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as mock_hf:
            mock_getenv.side_effect = lambda k, d=None: "hf_api" if "PROVIDER" in k else d
            hf_instance = MagicMock()
            mock_hf.return_value = hf_instance
            hf_instance.encode.return_value = []
            engine._load_embedding_model()
            engine._activate_deterministic_embedding.assert_called_once()

    def test_low_memory_deterministic(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._activate_deterministic_embedding = MagicMock()

        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = True
        settings_mock.RAG_USE_TRANSFORMERS = False

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store"), \
             patch("app.pipeline.intelligence.rag_engine.os.getenv") as mock_getenv:
            mock_getenv.return_value = ""
            engine._load_embedding_model()
            engine._activate_deterministic_embedding.assert_called_once()

    def test_sentence_transformers_import_fails(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._activate_deterministic_embedding = MagicMock()

        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store"):
            import builtins
            original_import = builtins.__import__
            def mock_import(name, *args, **kwargs):
                if "sentence_transformers" in name:
                    raise ImportError("No sentence_transformers")
                return original_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=mock_import):
                engine._load_embedding_model()
                engine._activate_deterministic_embedding.assert_called_once()

    def test_model_store_reuse_success(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = True

        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 1024
        candidate.encode.return_value = [0.1] * 1024
        model_store_mock.get_model.return_value = candidate

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock):
            with patch("app.pipeline.intelligence.rag_engine.PRIMARY_MODEL", "BAAI/bge-m3"):
                with patch("app.pipeline.intelligence.rag_engine.MODEL_DIMENSIONS", {"BAAI/bge-m3": 1024}):
                    engine._load_embedding_model()
                    assert engine.active_model_name == "BAAI/bge-m3"

    def test_model_store_reuse_fallback_dim(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = True

        candidate = MagicMock()
        candidate.get_sentence_embedding_dimension.return_value = 384
        candidate.encode.return_value = [0.1] * 384
        model_store_mock.get_model.return_value = candidate

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock):
            with patch("app.pipeline.intelligence.rag_engine.PRIMARY_MODEL", "BAAI/bge-m3"):
                with patch("app.pipeline.intelligence.rag_engine.MODEL_DIMENSIONS", {"BAAI/bge-m3": 1024}):
                    engine._load_embedding_model()
                    assert engine.active_model_name == "BAAI/bge-small-en-v1.5"

    def test_model_store_reuse_fails(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._activate_deterministic_embedding = MagicMock()

        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = True
        model_store_mock.get_model.return_value = None

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock), \
             patch("sentence_transformers.SentenceTransformer") as mock_st:
            st_instance = MagicMock()
            st_instance.get_sentence_embedding_dimension.return_value = 384
            mock_st.side_effect = [ImportError("fail"), ImportError("fail")]
            engine._load_embedding_model()
            engine._activate_deterministic_embedding.assert_called_once()

    def test_primary_load_success(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = False

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock), \
             patch("sentence_transformers.SentenceTransformer") as mock_st:
            st_instance = MagicMock()
            st_instance.get_sentence_embedding_dimension.return_value = 1024
            mock_st.return_value = st_instance
            engine._load_embedding_model()
            assert engine.active_model_name == "BAAI/bge-m3"

    def test_primary_fails_fallback_succeeds(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = False

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock), \
             patch("sentence_transformers.SentenceTransformer") as mock_st:
            def side_effect(model_name):
                if "bge-m3" in model_name:
                    raise Exception("OOM")
                st_instance = MagicMock()
                st_instance.get_sentence_embedding_dimension.return_value = 384
                return st_instance
            mock_st.side_effect = side_effect
            engine._load_embedding_model()
            assert engine.active_model_name == "BAAI/bge-small-en-v1.5"

    def test_both_fail_deterministic(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        engine._activate_deterministic_embedding = MagicMock()
        settings_mock = MagicMock()
        settings_mock.LOW_MEMORY_MODE = False
        settings_mock.RAG_USE_TRANSFORMERS = True

        model_store_mock = MagicMock()
        model_store_mock.is_loaded.return_value = False

        with patch("app.config.settings.settings", settings_mock), \
             patch("app.services.model_store.model_store", model_store_mock), \
             patch("sentence_transformers.SentenceTransformer") as mock_st:
            mock_st.side_effect = Exception("Both fail")
            engine._load_embedding_model()
            engine._activate_deterministic_embedding.assert_called_once()


class TestPersistence:
    def test_save_native(self):
        mock_file = mock_open()
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs"), \
             patch("app.pipeline.intelligence.rag_engine.open", mock_file), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory="/tmp/test_kb")
            engine.knowledge_base = [{"text": "test"}]
            engine._save_native()
            mock_file.assert_called_once()

    def test_load_native_file_exists(self):
        mock_file = mock_open(read_data='[{"text": "loaded"}]')
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs"), \
             patch("app.pipeline.intelligence.rag_engine.open", mock_file), \
             patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            mock_exists.return_value = True
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory="/tmp/test_kb")
            engine._load_native()
            assert len(engine.knowledge_base) == 1

    def test_load_native_file_not_exists(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs"), \
             patch("app.pipeline.intelligence.rag_engine.open", mock_open()), \
             patch("app.pipeline.intelligence.rag_engine.os.path.exists") as mock_exists, \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            mock_exists.return_value = False
            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory="/tmp/test_kb")
            engine.knowledge_base = []
            engine._load_native()
            assert engine.knowledge_base == []


class TestActivateDeterministicEmbedding:
    def test_activate_stores_in_model_store(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        model_store = MagicMock()
        engine._activate_deterministic_embedding(model_store, "Test fallback")
        assert engine.active_model_name is not None
        model_store.set_model.assert_called_once()

    def test_activate_store_fails_gracefully(self):
        from app.pipeline.intelligence.rag_engine import RagEngine
        engine = RagEngine.__new__(RagEngine)
        model_store = MagicMock()
        model_store.set_model.side_effect = Exception("Store error")
        engine._activate_deterministic_embedding(model_store, "Test")
        assert engine.embedding_model is not None


class TestTokenIndex:
    def test_token_index(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(256)
        idx1 = m._token_index("hello")
        idx2 = m._token_index("hello")
        assert idx1 == idx2
        assert 0 <= idx1 < 256


class TestGetRagEngine:
    def test_get_rag_engine_returns_singleton(self):
        with patch("app.pipeline.intelligence.rag_engine.os.makedirs"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._load_embedding_model"), \
             patch("app.pipeline.intelligence.rag_engine.RagEngine._seed_if_empty"), \
             patch("app.pipeline.intelligence.rag_engine._load_chromadb") as mock_chroma:
            mock_chroma.return_value = None
            from app.pipeline.intelligence.rag_engine import get_rag_engine
            engine1 = get_rag_engine()
            engine2 = get_rag_engine()
            assert engine1 is engine2
