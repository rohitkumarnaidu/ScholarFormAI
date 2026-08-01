# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive gap-filling tests for RagEngine — covers uncovered branches,
edge cases in HF API embedding, ChromaDB/native backends, and model loading.
"""

from __future__ import annotations

import json
import os
import numpy as np
from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_engine(
    tmp_path,
    low_memory=False,
    use_transformers=True,
    auto_seed=False,
    chromadb_module=None,
    st_side_effect=None,
    model_store_is_loaded=False,
    hf_provider="",
):
    """Build a RagEngine with all external dependencies mocked."""
    persist = str(tmp_path / "rag_store")

    patch_settings = patch("app.config.settings.settings")
    patch_model_store = patch("app.services.model_store.model_store")

    mock_model = MagicMock(name="st_model")
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = [0.1] * 384

    if st_side_effect is not None:
        patch_st = patch("sentence_transformers.SentenceTransformer", side_effect=st_side_effect)
    else:
        patch_st = patch("sentence_transformers.SentenceTransformer", return_value=mock_model)

    with (
        patch_settings as ms,
        patch_model_store as mm,
        patch_st,
        patch.dict(os.environ, {"RAG_EMBEDDING_PROVIDER": hf_provider}, clear=False),
    ):
        ms.LOW_MEMORY_MODE = low_memory
        ms.RAG_USE_TRANSFORMERS = use_transformers
        mm.is_loaded.return_value = model_store_is_loaded
        if model_store_is_loaded:
            stored = MagicMock(name="stored_model")
            stored.get_sentence_embedding_dimension.return_value = 384
            stored.encode.return_value = [0.1] * 384
            mm.get_model.return_value = stored

        from app.pipeline.intelligence.rag_engine import RagEngine

        if chromadb_module is not None:
            with patch("app.pipeline.intelligence.rag_engine.chromadb", chromadb_module):
                engine = RagEngine(persist_directory=persist, auto_seed=auto_seed)
        else:
            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                engine = RagEngine(persist_directory=persist, auto_seed=auto_seed)

    engine._mock_model = mock_model
    return engine


@pytest.fixture
def engine(tmp_path):
    """Default RagEngine fixture with mocked SentenceTransformer, no auto-seed, native backend."""
    return _make_engine(tmp_path)


class TestLoadEmbeddingModelHfApi:
    """Cover the HuggingFace API embedding provider path."""

    def test_hf_provider_initialized(self, tmp_path):
        """HF API provider is used when RAG_EMBEDDING_PROVIDER=hf_api."""
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer"),
            patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as mock_hf_cls,
        ):
            ms.LOW_MEMORY_MODE = True
            ms.RAG_USE_TRANSFORMERS = False
            mm.is_loaded.return_value = False

            mock_hf = MagicMock()
            mock_hf.encode.return_value = [0.1, 0.2, 0.3]
            mock_hf.dimension = 384
            mock_hf_cls.return_value = mock_hf

            persist = str(tmp_path / "hf_test")
            from app.pipeline.intelligence.rag_engine import RagEngine

            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                with patch.dict(os.environ, {"RAG_EMBEDDING_PROVIDER": "hf_api"}, clear=False):
                    engine = RagEngine(persist_directory=persist, auto_seed=False)
                    assert "huggingface_api" in engine.active_model_name

    def test_hf_provider_health_check_fails(self, tmp_path):
        """HF API health check fails -> falls back to deterministic."""
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer"),
            patch("app.pipeline.intelligence.rag_engine._HuggingFaceAPIEmbeddingModel") as mock_hf_cls,
        ):
            ms.LOW_MEMORY_MODE = True
            ms.RAG_USE_TRANSFORMERS = False
            mm.is_loaded.return_value = False

            mock_hf = MagicMock()
            mock_hf.encode.return_value = []
            mock_hf_cls.return_value = mock_hf

            persist = str(tmp_path / "hf_fail")
            from app.pipeline.intelligence.rag_engine import RagEngine, DETERMINISTIC_FALLBACK_MODEL

            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                with patch.dict(os.environ, {"RAG_EMBEDDING_PROVIDER": "huggingface_api"}, clear=False):
                    engine = RagEngine(persist_directory=persist, auto_seed=False)
                    assert engine.active_model_name == DETERMINISTIC_FALLBACK_MODEL


class TestNumpyCompat:
    """Cover NumPy compatibility patching in __init__."""

    def test_numpy_float_patched(self, tmp_path):
        """np.float_ is restored if missing (NumPy 2.x compat)."""
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            from app.pipeline.intelligence.rag_engine import RagEngine

            orig_float = getattr(np, 'float_', None)
            orig_int = getattr(np, 'int_', None)

            if hasattr(np, 'float_'):
                del np.float_
            if hasattr(np, 'int_'):
                del np.int_

            try:
                persist = str(tmp_path / "numpy_test")
                with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                    engine = RagEngine(persist_directory=persist, auto_seed=False)
                    assert hasattr(np, 'float_')
                    assert hasattr(np, 'int_')
            finally:
                if orig_float is not None:
                    np.float_ = orig_float
                if orig_int is not None:
                    np.int_ = orig_int


class TestChromaDbInitGaps:
    """Cover edge cases in ChromaDB initialization."""

    def test_chromadb_known_error_no_warning(self, tmp_path):
        """Known compat error does NOT get logged as warning."""
        persist = str(tmp_path / "compat_test")
        mock_chroma = MagicMock()
        mock_chroma.PersistentClient.side_effect = Exception("no such column: collections.topic")

        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
            patch("app.pipeline.intelligence.rag_engine.chromadb", mock_chroma),
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory=persist, auto_seed=False)
            assert engine.backend == "native"

    def test_chromadb_unknown_error_logs_warning(self, tmp_path, caplog):
        """Unknown compat error gets logged as warning."""
        persist = str(tmp_path / "unknown_test")
        mock_chroma = MagicMock()
        mock_chroma.PersistentClient.side_effect = Exception("some random error")

        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
            patch("app.pipeline.intelligence.rag_engine.chromadb", mock_chroma),
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory=persist, auto_seed=False)
            assert engine.backend == "native"

    def test_chromadb_module_none(self, tmp_path):
        """chromadb_module is None after load attempt."""
        persist = str(tmp_path / "none_test")
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
            patch("app.pipeline.intelligence.rag_engine._CHROMADB_AVAILABLE", False),
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            from app.pipeline.intelligence.rag_engine import RagEngine
            engine = RagEngine(persist_directory=persist, auto_seed=False)
            assert engine.backend == "native"


class TestHuggingFaceAPIEmbeddingModelGaps:
    """Cover uncovered paths in _HuggingFaceAPIEmbeddingModel."""

    def test_encode_400_sentence_similarity_recovery(self):
        """400 with SentenceSimilarityPipeline triggers endpoint recovery."""
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.api_url = "https://router.huggingface.co/hf-inference/models/test-model"
            m.max_retries = 2

            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                first_response = MagicMock()
                first_response.status_code = 400
                first_response.text = "SentenceSimilarityPipeline error"
                second_response = MagicMock()
                second_response.status_code = 200
                second_response.json.return_value = [[0.1, 0.2]]

                mp.side_effect = [first_response, second_response]
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    result = m.encode("test")
                    assert result == [0.1, 0.2]

    def test_encode_400_no_recovery(self):
        """400 without SentenceSimilarityPipeline does not recover."""
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.api_url = "https://router.huggingface.co/hf-inference/models/test-model"

            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                response = MagicMock()
                response.status_code = 400
                response.text = "Some other error"
                mp.return_value = response
                result = m.encode("test")
                assert result == []

    def test_encode_500_retry_then_abandon(self):
        """500-599 errors retry then return empty."""
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.max_retries = 2

            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                response = MagicMock()
                response.status_code = 503
                response.text = "Service Unavailable"
                mp.return_value = response
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    result = m.encode("test")
                    assert result == []
                    assert mp.call_count == 2

    def test_encode_500_on_last_retry_returns_empty(self):
        """500 on final retry returns empty."""
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.max_retries = 1

            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                response = MagicMock()
                response.status_code = 503
                response.text = "Fail"
                mp.return_value = response
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    result = m.encode("test")
                    assert result == []

    def test_encode_exception_at_end_returns_empty(self):
        """Exception logs error and returns empty after retries exhausted."""
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.max_retries = 2

            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.side_effect = [Exception("fail1"), Exception("fail2")]
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    result = m.encode("test")
                    assert result == []

    def test_normalize_embedding_api_url_empty(self):
        """Empty URL returns default."""
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url("", "test-model")
        assert "router.huggingface.co" in url

    def test_normalize_embedding_api_url_adds_pipeline(self):
        """URL without pipeline path gets it added."""
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(
            "https://router.huggingface.co/hf-inference/models/test-model", "test"
        )
        assert "/pipeline/feature-extraction" in url

    def test_normalize_embedding_api_url_already_has_pipeline(self):
        """URL already with pipeline path is kept as-is."""
        from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
        url = _HuggingFaceAPIEmbeddingModel._normalize_embedding_api_url(
            "https://router.huggingface.co/hf-inference/models/test-model/pipeline/feature-extraction", "test"
        )
        assert url.endswith("/pipeline/feature-extraction")


class TestSeedIfEmptyGaps:
    """Cover remaining _seed_if_empty branches."""

    def test_chromadb_count_gt_zero_skips(self, engine):
        """ChromaDB has data -> skip seeding."""
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.collection.count.return_value = 5
        engine.knowledge_base = []
        with patch.object(engine, "add_guideline") as mock_add:
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_default_file_not_found(self, engine):
        """default_guidelines.json not found -> skip."""
        with (
            patch("os.path.exists", return_value=False),
            patch.object(engine, "add_guideline") as mock_add,
        ):
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_payload_is_dict_without_guidelines_key(self, engine):
        """Dict without 'guidelines' key -> skip."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps({"other": []})
            mock_open.return_value = mf
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_payload_is_unexpected_type(self, engine):
        """Payload is a string -> empty guidelines."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = '"string"'
            mock_open.return_value = mf
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_item_missing_required_fields(self, engine):
        """Item missing publisher/section/text -> skipped."""
        data = {"guidelines": [{"publisher": "IEEE", "text": "no section"}]}
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps(data)
            mock_open.return_value = mf
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_seed_exception_does_not_crash(self, engine):
        """Exception during seed does not crash."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=PermissionError("denied")),
        ):
            engine._seed_if_empty()


class TestQueryGuidelinesNativeGaps:
    """Cover native query_guidelines edge cases."""

    def test_embedding_model_none_returns_empty(self, engine):
        """No embedding model -> empty results."""
        engine.embedding_model = None
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_query_embedding_empty_returns_empty(self, engine):
        """Empty query embedding -> empty results."""
        engine.embedding_model.encode.return_value = []
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_no_publisher_match(self, engine):
        """No items matching publisher -> empty."""
        engine.knowledge_base = [
            {"text": "ACM rule.", "metadata": {"publisher": "ACM"}, "embedding": [0.1, 0.2]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_item_with_no_embedding_skipped(self, engine):
        """Item missing embedding -> skipped."""
        engine.knowledge_base = [
            {"text": "IEEE rule.", "metadata": {"publisher": "IEEE"}, "embedding": []},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_dimension_mismatch_skipped(self, engine):
        """Item with different embedding dimension -> skipped."""
        engine.knowledge_base = [
            {"text": "IEEE rule.", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_zero_norm_skipped(self, engine):
        """Item with zero vector norm -> skipped."""
        engine.knowledge_base = [
            {"text": "IEEE rule.", "metadata": {"publisher": "IEEE"}, "embedding": [0.0, 0.0]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_query_exception_returns_empty(self, engine):
        """Exception during native query -> empty."""
        engine.embedding_model.encode.side_effect = RuntimeError("fail")
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_chromadb_query_exception_falls_back(self, engine):
        """ChromaDB query exception -> native fallback."""
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.collection.query.side_effect = Exception("chroma fail")
        engine.knowledge_base = [
            {"text": "IEEE rule.", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test")
        assert "IEEE rule." in results


class TestQueryRulesGaps:
    """Cover query_rules edge cases."""

    def test_empty_template_defaults(self, engine):
        """Empty template -> IEEE, empty section -> general."""
        with patch.object(engine, "query_guidelines", return_value=["rule"]):
            results = engine.query_rules("", "")
            assert results[0]["metadata"]["publisher"] == "IEEE"
            assert results[0]["metadata"]["section"] == "general"

    def test_none_template_defaults(self, engine):
        """None template -> IEEE."""
        with patch.object(engine, "query_guidelines", return_value=["rule"]):
            results = engine.query_rules(None, "")  # type: ignore[arg-type]
            assert results[0]["metadata"]["publisher"] == "IEEE"

    def test_exception_returns_empty(self, engine):
        """Exception -> empty list."""
        with patch.object(engine, "query_guidelines", side_effect=Exception("fail")):
            results = engine.query_rules("IEEE", "abstract")
            assert results == []


class TestResetGaps:
    """Cover reset edge cases."""

    def test_reset_chromadb_exception(self, engine):
        """ChromaDB delete_collection exception handled."""
        engine.chroma_enabled = True
        engine.client = MagicMock()
        engine.collection = MagicMock()
        engine.client.delete_collection.side_effect = Exception("delete fail")
        engine.knowledge_base = [{"text": "test"}]
        engine.reset()
        assert engine.knowledge_base == []

    def test_reset_no_kb_file(self, engine):
        """No kb_file on disk -> still clears knowledge_base."""
        engine.knowledge_base = [{"text": "test"}]
        engine.reset()
        assert engine.knowledge_base == []

    def test_reset_chromadb_only(self, engine):
        """ChromaDB reset path with no kb_file."""
        engine.chroma_enabled = True
        engine.client = MagicMock()
        engine.collection = MagicMock()
        engine.reset()
        engine.client.delete_collection.assert_called_once()


class TestGetRagEngineGaps:
    """Cover get_rag_engine singleton edge cases."""

    def test_singleton_returns_same(self):
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            import app.pipeline.intelligence.rag_engine as rag_mod
            rag_mod._rag_engine = None
            from app.pipeline.intelligence.rag_engine import get_rag_engine

            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                r1 = get_rag_engine()
                r2 = get_rag_engine()
                assert r1 is r2
