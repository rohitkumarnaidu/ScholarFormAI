# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for RagEngine (rag_engine.py) — 80+ tests covering all internal methods,
model loading, embedding, ChromaDB/native backends, persistence, seeding, and reset.

Model loading imports `SentenceTransformer` inside `_load_embedding_model()`, not at
module level, so we patch `sentence_transformers.SentenceTransformer` instead.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

try:
    import sentence_transformers  # noqa: F401
except ImportError:
    pytestmark = pytest.mark.skipif(True, reason="sentence_transformers not installed in CI")

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
        patch.dict(os.environ, {"RAG_EMBEDDING_PROVIDER": ""}, clear=False),
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


# ===================================================================
#  _load_chromadb  (module-level function)
# ===================================================================

class TestLoadChromadb:
    """Tests for the lazy chromadb loader."""

    def test_already_loaded_returns_chromadb(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb
        with patch("app.pipeline.intelligence.rag_engine.chromadb", "fake_mod"):
            result = _load_chromadb()
            assert result == "fake_mod"

    def test_import_attempted_returns_none(self):
        from app.pipeline.intelligence.rag_engine import _load_chromadb
        with (
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
            patch("app.pipeline.intelligence.rag_engine._CHROMADB_IMPORT_ATTEMPTED", True),
        ):
            result = _load_chromadb()
            assert result is None

    def test_import_success(self):
        import app.pipeline.intelligence.rag_engine as rag_mod
        from app.pipeline.intelligence.rag_engine import _load_chromadb

        fake_mod = MagicMock()
        was_there = "chromadb" in sys.modules
        saved = sys.modules.get("chromadb")
        sys.modules["chromadb"] = fake_mod
        try:
            with (
                patch.object(rag_mod, "chromadb", None),
                patch.object(rag_mod, "_CHROMADB_IMPORT_ATTEMPTED", False),
                patch.object(rag_mod, "_CHROMADB_AVAILABLE", False),
            ):
                result = _load_chromadb()
                assert result is fake_mod
                assert rag_mod._CHROMADB_AVAILABLE is True
                assert rag_mod._CHROMADB_IMPORT_ATTEMPTED is True
        finally:
            if was_there:
                sys.modules["chromadb"] = saved
            else:
                sys.modules.pop("chromadb", None)

    def test_import_failure(self):
        import app.pipeline.intelligence.rag_engine as rag_mod
        from app.pipeline.intelligence.rag_engine import _load_chromadb

        with (
            patch.dict("sys.modules", {"chromadb": None}, clear=False),
            patch.object(rag_mod, "chromadb", None),
            patch.object(rag_mod, "_CHROMADB_IMPORT_ATTEMPTED", False),
            patch.object(rag_mod, "_CHROMADB_AVAILABLE", True),
        ):
            result = _load_chromadb()
            assert result is None
            assert rag_mod._CHROMADB_AVAILABLE is False


# ===================================================================
#  _DeterministicEmbeddingModel
# ===================================================================

class TestDeterministicEmbeddingModel:
    """Cover every method of the deterministic fallback embedding model."""

    @pytest.fixture
    def model(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        return _DeterministicEmbeddingModel(dimension=64)

    def test_dimension(self, model):
        assert model.get_sentence_embedding_dimension() == 64

    def test_min_dimension(self):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(dimension=8)
        assert m.get_sentence_embedding_dimension() >= 32

    def test_token_index_bounds(self, model):
        idx = model._token_index("hello")
        assert 0 <= idx < 64

    def test_token_index_deterministic(self, model):
        assert model._token_index("hello") == model._token_index("hello")

    def test_encode_single_text(self, model):
        vec = model._encode_one("hello world")
        assert len(vec) == 64
        assert any(v != 0 for v in vec)

    def test_encode_empty_text(self, model):
        vec = model._encode_one("")
        assert len(vec) == 64
        assert all(v == 0 for v in vec)

    def test_encode_none(self, model):
        vec = model._encode_one(None)
        assert len(vec) == 64

    def test_encode_list(self, model):
        result = model.encode(["hello", "world"])
        assert len(result) == 2
        assert all(len(v) == 64 for v in result)

    def test_encode_single_string(self, model):
        result = model.encode("hello")
        assert len(result) == 64

    def test_normalized_vector_has_unit_norm(self, model):
        vec = np.array(model._encode_one("a b c d e f g h i j k l m n o p"))
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-9


# ===================================================================
#  _HuggingFaceAPIEmbeddingModel
# ===================================================================

class TestHuggingFaceAPIEmbeddingModel:
    """Cover remote HuggingFace API embedding model."""

    def test_default_dimension(self):
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            assert m.dimension == 384

    def test_bge_m3_dimension(self):
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel(model_id="BAAI/bge-m3")
            assert m.dimension == 1024

    def test_no_token_returns_empty(self):
        with patch.dict(os.environ, {"HF_TOKEN": ""}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            assert m.encode("test") == []

    def test_successful_encode_single(self):
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.return_value.status_code = 200
                mp.return_value.json.return_value = [[0.1, 0.2, 0.3]]
                result = m.encode("test")
                assert result == [0.1, 0.2, 0.3]

    def test_successful_encode_list(self):
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.return_value.status_code = 200
                mp.return_value.json.return_value = [[0.1], [0.2]]
                result = m.encode(["a", "b"])
                assert result == [[0.1], [0.2]]

    def test_http_error_returns_empty(self):
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.return_value.status_code = 500
                mp.return_value.text = "Server Error"
                assert m.encode("test") == []

    def test_retry_on_server_error(self):
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.max_retries = 2
            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.return_value.status_code = 500
                mp.return_value.text = "Error"
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    m.encode("test")
                    assert mp.call_count == 2

    def test_retry_on_exception(self):
        with patch.dict(os.environ, {"HF_TOKEN": "tok"}, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            m.max_retries = 2
            with patch("app.pipeline.intelligence.rag_engine.requests.post") as mp:
                mp.side_effect = [Exception("timeout"), MagicMock(status_code=200, json=lambda: [[0.5]])]
                with patch("app.pipeline.intelligence.rag_engine.time.sleep"):
                    result = m.encode("test")
                    assert result == [0.5]

    def test_url_normalization_adds_pipeline(self):
        with patch.dict(os.environ, {
            "HF_TOKEN": "tok",
            "RAG_EMBEDDING_API_URL": "https://router.huggingface.co/hf-inference/models/test-model",
        }, clear=False):
            from app.pipeline.intelligence.rag_engine import _HuggingFaceAPIEmbeddingModel
            m = _HuggingFaceAPIEmbeddingModel()
            assert "/pipeline/feature-extraction" in m.api_url


# ===================================================================
#  RagEngine — _coerce_embedding_vector
# ===================================================================

class TestCoerceEmbeddingVector:
    """Static method for converting embedding types."""

    def test_none(self, engine):
        assert engine._coerce_embedding_vector(None) == []

    def test_numpy_array(self, engine):
        assert engine._coerce_embedding_vector(np.array([1.0, 2.0])) == [1.0, 2.0]

    def test_list(self, engine):
        assert engine._coerce_embedding_vector([3.0, 4.0]) == [3.0, 4.0]

    def test_nested_list(self, engine):
        assert engine._coerce_embedding_vector([[5.0, 6.0]]) == [5.0, 6.0]

    def test_empty_list(self, engine):
        assert engine._coerce_embedding_vector([]) == []

    def test_non_iterable(self, engine):
        assert engine._coerce_embedding_vector(42) == []

    def test_unconvertable_elements(self, engine):
        assert engine._coerce_embedding_vector([object()]) == []


# ===================================================================
#  RagEngine.__init__
# ===================================================================

class TestInit:
    """Constructor behavior under various conditions."""

    def test_custom_persist_directory(self, tmp_path):
        str(tmp_path / "custom")
        e = _make_engine(tmp_path)
        # persist dir is tmp_path/rag_store, just verify it exists
        assert "rag_store" in e.persist_directory

    def test_auto_seed_disabled_for_custom_persist(self, tmp_path):
        e = _make_engine(tmp_path)
        assert e.auto_seed is False

    def test_default_persist_directory(self):
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
            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                e = RagEngine(auto_seed=False)
            assert e.auto_seed is False

    def test_auto_seed_default_for_production(self):
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
            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                e = RagEngine()
            assert e.auto_seed is True

    def test_chromadb_initialized_when_available(self, tmp_path):
        persist = str(tmp_path / "chr_test")
        mock_chroma = MagicMock()
        mock_chroma.PersistentClient.return_value.get_or_create_collection.return_value = MagicMock()

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

            with patch("app.pipeline.intelligence.rag_engine.chromadb", mock_chroma):
                e = RagEngine(persist_directory=persist, auto_seed=False)
                assert e.chroma_enabled is True
                assert e.backend == "chromadb"

    def test_chromadb_fallback_to_native(self, tmp_path):
        persist = str(tmp_path / "nat_test")
        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
            patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None),
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = False
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            from app.pipeline.intelligence.rag_engine import RagEngine
            e = RagEngine(persist_directory=persist, auto_seed=False)
            assert e.chroma_enabled is False
            assert e.backend == "native"
            assert e.collection is None


# ===================================================================
#  _is_reusable_embedding_model
# ===================================================================

class TestReusableEmbeddingModel:
    """Validation of pre-loaded embedding models."""

    def test_none(self, engine):
        ok, dim = engine._is_reusable_embedding_model(None)
        assert ok is False

    def test_no_encode(self, engine):
        ok, dim = engine._is_reusable_embedding_model(object())
        assert ok is False

    def test_no_dimension_method(self, engine):
        obj = MagicMock(spec=["encode"])
        ok, dim = engine._is_reusable_embedding_model(obj)
        assert ok is False

    def test_invalid_dimension(self, engine):
        obj = MagicMock()
        obj.get_sentence_embedding_dimension.return_value = 0
        obj.encode.return_value = [0.1]
        ok, dim = engine._is_reusable_embedding_model(obj)
        assert ok is False

    def test_encode_fails(self, engine):
        obj = MagicMock()
        obj.get_sentence_embedding_dimension.return_value = 384
        obj.encode.return_value = None
        ok, dim = engine._is_reusable_embedding_model(obj)
        assert ok is False

    def test_valid_model(self, engine):
        obj = MagicMock()
        obj.get_sentence_embedding_dimension.return_value = 384
        obj.encode.return_value = [0.1] * 384
        ok, dim = engine._is_reusable_embedding_model(obj)
        assert ok is True
        assert dim == 384


# ===================================================================
#  _activate_deterministic_embedding
# ===================================================================

class TestActivateDeterministicEmbedding:
    """Fallback to deterministic hash embedding."""

    def test_sets_deterministic_model(self, engine):
        model_store = MagicMock()
        engine._activate_deterministic_embedding(model_store, "OOM")
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert engine.active_model_name == DETERMINISTIC_FALLBACK_MODEL
        assert engine.embedding_model is not None

    def test_stores_in_model_store(self, engine):
        model_store = MagicMock()
        engine._activate_deterministic_embedding(model_store, "test")
        model_store.set_model.assert_called_once()

    def test_model_store_failure_handled(self, engine, caplog):
        model_store = MagicMock()
        model_store.set_model.side_effect = RuntimeError("store full")
        engine._activate_deterministic_embedding(model_store, "test")
        assert engine.embedding_model is not None


# ===================================================================
#  _load_embedding_model (model loading chain)
# ===================================================================

class TestLoadEmbeddingModel:
    """Model loading priority and fallback."""

    def test_low_memory_uses_deterministic(self, tmp_path):
        e = _make_engine(tmp_path, low_memory=True, use_transformers=True)
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert e.active_model_name == DETERMINISTIC_FALLBACK_MODEL

    def test_use_transformers_false_uses_deterministic(self, tmp_path):
        e = _make_engine(tmp_path, low_memory=False, use_transformers=False)
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert e.active_model_name == DETERMINISTIC_FALLBACK_MODEL

    def test_no_hf_provider_uses_deterministic(self, tmp_path):
        e = _make_engine(tmp_path, low_memory=True, use_transformers=False)
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert e.active_model_name == DETERMINISTIC_FALLBACK_MODEL

    def test_sentence_transformer_import_fails(self, tmp_path):
        def fail_import(*a, **kw):
            raise ImportError("no sentence_transformers")

        e = _make_engine(tmp_path, st_side_effect=fail_import)
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert e.active_model_name == DETERMINISTIC_FALLBACK_MODEL

    def test_primary_model_fails_fallback_succeeds(self, tmp_path):
        from app.pipeline.intelligence.rag_engine import FALLBACK_MODEL, PRIMARY_MODEL

        fallback_model = MagicMock(name="fallback_model")
        fallback_model.get_sentence_embedding_dimension.return_value = 384

        def side_effect(model_name, **kw):
            if model_name == PRIMARY_MODEL:
                raise Exception("OOM")
            return fallback_model

        e = _make_engine(tmp_path, st_side_effect=side_effect)
        assert e.active_model_name == FALLBACK_MODEL

    def test_both_models_fail_uses_deterministic(self, tmp_path):
        def side_effect(*a, **kw):
            raise Exception("no model for you")

        e = _make_engine(tmp_path, st_side_effect=side_effect)
        from app.pipeline.intelligence.rag_engine import DETERMINISTIC_FALLBACK_MODEL
        assert e.active_model_name == DETERMINISTIC_FALLBACK_MODEL

    def test_reuses_model_from_model_store(self, tmp_path):
        e = _make_engine(tmp_path, model_store_is_loaded=True)
        from app.pipeline.intelligence.rag_engine import FALLBACK_MODEL
        assert e.active_model_name == FALLBACK_MODEL  # 384d → fallback name

    def test_reuse_invalid_model_triggers_reload(self, tmp_path):
        invalid = MagicMock(name="invalid")
        invalid.get_sentence_embedding_dimension.return_value = 0

        with (
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mst,
        ):
            ms.LOW_MEMORY_MODE = False
            ms.RAG_USE_TRANSFORMERS = True
            mm.is_loaded.return_value = True
            mm.get_model.return_value = invalid

            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = [0.1] * 384
            mst.return_value = mock_model

            persist = str(tmp_path / "reuse_invalid")
            from app.pipeline.intelligence.rag_engine import RagEngine
            with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                e = RagEngine(persist_directory=persist, auto_seed=False)
                from app.pipeline.intelligence.rag_engine import PRIMARY_MODEL
                assert e.active_model_name == PRIMARY_MODEL


# ===================================================================
#  _seed_if_empty
# ===================================================================

class TestSeedIfEmpty:
    """Auto-seeding from default_guidelines.json."""

    def test_knowledge_base_not_empty_skips(self, engine):
        engine.knowledge_base = [{"text": "existing"}]
        with patch.object(engine, "add_guideline") as mock_add:
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_chromadb_has_data_skips(self, engine):
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.collection.count.return_value = 5
        with patch.object(engine, "add_guideline") as mock_add:
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_default_file_not_found(self, engine):
        with (
            patch("os.path.exists", return_value=False),
            patch.object(engine, "add_guideline") as mock_add,
        ):
            engine._seed_if_empty()
            mock_add.assert_not_called()

    def test_successful_seed_with_guidelines_key(self, engine):
        test_data = {
            "guidelines": [
                {"publisher": "IEEE", "section": "abstract", "text": "Write abstract."},
                {"publisher": "APA", "section": "references", "text": "Cite refs."},
            ]
        }
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps(test_data)
            mock_open.return_value = mf
            engine._seed_if_empty()
            assert mock_add.call_count == 2

    def test_seed_with_template_and_category_keys(self, engine):
        test_data = {
            "guidelines": [
                {"template": "IEEE", "category": "intro", "guideline": "Start here."},
            ]
        }
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps(test_data)
            mock_open.return_value = mf
            engine._seed_if_empty()
            mock_add.assert_called_once()

    def test_skips_incomplete_items(self, engine):
        test_data = {
            "guidelines": [
                {"publisher": "IEEE", "text": "no section"},
                {"publisher": "APA", "section": "refs", "text": "valid"},
            ]
        }
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps(test_data)
            mock_open.return_value = mf
            engine._seed_if_empty()
            assert mock_add.call_count == 1

    def test_list_format(self, engine):
        test_data = [
            {"publisher": "ACM", "section": "body", "text": "Write body."},
        ]
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch.object(engine, "add_guideline") as mock_add,
        ):
            mf = MagicMock()
            mf.__enter__.return_value.read.return_value = json.dumps(test_data)
            mock_open.return_value = mf
            engine._seed_if_empty()
            mock_add.assert_called_once()

    def test_dict_without_guidelines_key(self, engine):
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

    def test_exception_during_seed_does_not_crash(self, engine):
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=PermissionError("denied")),
        ):
            engine._seed_if_empty()  # should not raise


# ===================================================================
#  add_guideline
# ===================================================================

class TestAddGuideline:
    """Adding guideline rules."""

    def test_adds_to_knowledge_base(self, engine):
        engine.add_guideline("IEEE", "abstract", "Write an abstract.")
        assert len(engine.knowledge_base) == 1
        assert engine.knowledge_base[0]["text"] == "Write an abstract."
        assert engine.knowledge_base[0]["metadata"]["publisher"] == "IEEE"

    def test_adds_to_chromadb_when_enabled(self, engine):
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.add_guideline("ACM", "references", "Cite refs.")
        assert engine.collection.add.called

    def test_with_custom_metadata(self, engine):
        engine.add_guideline("IEEE", "body", "Some body", metadata={"source": "user"})
        assert engine.knowledge_base[0]["metadata"]["source"] == "user"

    def test_no_embedding_model_uses_empty_embedding(self, engine):
        engine.embedding_model = None
        engine.add_guideline("IEEE", "intro", "Intro.")
        assert engine.knowledge_base[0]["embedding"] == []

    def test_saves_native_after_add(self, engine):
        with patch.object(engine, "_save_native") as mock_save:
            engine.add_guideline("IEEE", "intro", "Intro text.")
            mock_save.assert_called_once()


# ===================================================================
#  query_guidelines
# ===================================================================

class TestQueryGuidelines:
    """Retrieving guidelines via ChromaDB or native fallback."""

    def test_chromadb_query(self, engine):
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.collection.query.return_value = {"documents": [["r1", "r2"]]}
        results = engine.query_guidelines("IEEE", "abstract", top_k=2)
        assert results == ["r1", "r2"]

    def test_chromadb_failure_falls_to_native(self, engine):
        engine.chroma_enabled = True
        engine.collection = MagicMock()
        engine.collection.query.side_effect = Exception("chroma down")
        engine.knowledge_base = [
            {"text": "Do IEEE.", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]},
            {"text": "Do ACM.", "metadata": {"publisher": "ACM"}, "embedding": [0.3, 0.4]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test", top_k=2)
        assert "Do IEEE." in results

    def test_native_empty_no_embedding_model(self, engine):
        engine.embedding_model = None
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_native_empty_when_no_publisher_match(self, engine):
        engine.knowledge_base = [
            {"text": "ACM rule.", "metadata": {"publisher": "ACM"}, "embedding": [0.1]},
        ]
        engine.embedding_model.encode.return_value = [0.1]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_native_empty_when_embedding_fails(self, engine):
        engine.knowledge_base = [
            {"text": "IEEE rule.", "metadata": {"publisher": "IEEE"}, "embedding": None},
        ]
        engine.embedding_model.encode.return_value = []
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_native_dimension_mismatch_skipped(self, engine):
        engine.knowledge_base = [
            {"text": "IEEE 2d.", "metadata": {"publisher": "IEEE"}, "embedding": [0.1, 0.2]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_native_zero_norm_skipped(self, engine):
        engine.knowledge_base = [
            {"text": "IEEE zero.", "metadata": {"publisher": "IEEE"}, "embedding": [0.0, 0.0]},
        ]
        engine.embedding_model.encode.return_value = [0.1, 0.2]
        results = engine.query_guidelines("IEEE", "test")
        assert results == []

    def test_exception_in_native_query(self, engine):
        engine.embedding_model.encode.side_effect = Exception("encode fail")
        results = engine.query_guidelines("IEEE", "test")
        assert results == []


# ===================================================================
#  query_rules (phase-2 interface adapter)
# ===================================================================

class TestQueryRules:
    """Interface required by PipelineOrchestrator."""

    def test_basic(self, engine):
        with patch.object(engine, "query_guidelines", return_value=["rule text"]):
            results = engine.query_rules("IEEE", "abstract")
            assert len(results) == 1
            assert results[0]["text"] == "rule text"
            assert results[0]["metadata"]["publisher"] == "IEEE"

    def test_empty_template_defaults(self, engine):
        with patch.object(engine, "query_guidelines", return_value=["rule"]):
            results = engine.query_rules("", "")
            assert results[0]["metadata"]["publisher"] == "IEEE"
            assert results[0]["metadata"]["section"] == "general"

    def test_exception_returns_empty(self, engine):
        with patch.object(engine, "query_guidelines", side_effect=Exception("fail")):
            results = engine.query_rules("IEEE", "abstract")
            assert results == []


# ===================================================================
#  Persistence (_save_native / _load_native)
# ===================================================================

class TestPersistence:
    """Native JSON persistence."""

    def test_save_native(self, engine, tmp_path):
        engine.kb_file = str(tmp_path / "kb.json")
        engine.knowledge_base = [{"text": "t1", "metadata": {}, "embedding": []}]
        engine._save_native()
        assert (tmp_path / "kb.json").exists()

    def test_load_native(self, engine, tmp_path):
        kb = tmp_path / "kb.json"
        kb.write_text(json.dumps([{"text": "loaded"}]))
        engine.kb_file = str(kb)
        engine._load_native()
        assert len(engine.knowledge_base) == 1
        assert engine.knowledge_base[0]["text"] == "loaded"

    def test_load_native_file_not_found(self, engine):
        engine.kb_file = os.path.join(engine.persist_directory, "nonexistent.json")
        engine._load_native()
        assert engine.knowledge_base == []


# ===================================================================
#  reset
# ===================================================================

class TestReset:
    """Clearing all indexed guidelines."""

    def test_clears_knowledge_base(self, engine):
        engine.knowledge_base = [{"text": "something"}]
        engine.reset()
        assert engine.knowledge_base == []

    def test_removes_kb_file(self, engine, tmp_path):
        kb = tmp_path / "kb.json"
        kb.write_text("[]")
        engine.kb_file = str(kb)
        engine.reset()
        assert not kb.exists()

    def test_resets_chromadb(self, engine):
        engine.chroma_enabled = True
        engine.client = MagicMock()
        engine.collection = MagicMock()
        engine.reset()
        assert engine.client.delete_collection.called

    def test_chromadb_reset_exception_handled(self, engine):
        engine.chroma_enabled = True
        engine.client = MagicMock()
        engine.client.delete_collection.side_effect = Exception("fail")
        engine.reset()  # should not raise


# ===================================================================
#  get_rag_engine (singleton)
# ===================================================================

class TestGetRagEngine:
    """Singleton factory."""

    def test_returns_engine(self):
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

            from app.pipeline.intelligence.rag_engine import _rag_engine, get_rag_engine
            # Ensure singleton is None before test
            test_rag = _rag_engine
            try:
                import app.pipeline.intelligence.rag_engine as rag_mod
                rag_mod._rag_engine = None
                with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                    result = get_rag_engine()
                    assert result is not None
            finally:
                rag_mod._rag_engine = test_rag

    def test_singleton(self):
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
            from app.pipeline.intelligence.rag_engine import get_rag_engine
            orig = rag_mod._rag_engine
            try:
                rag_mod._rag_engine = None
                with patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None):
                    r1 = get_rag_engine()
                    r2 = get_rag_engine()
                    assert r1 is r2
            finally:
                rag_mod._rag_engine = orig
