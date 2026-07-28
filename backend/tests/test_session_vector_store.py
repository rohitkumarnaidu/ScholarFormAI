import pytest
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
import numpy as np
from app.cache.redis_cache import redis_cache, RedisCache


class TestDeterministicEmbeddingModel:
    @pytest.fixture
    def model(self):
        from app.services.session_vector_store import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel(dimension=64)
        return m

    def test_default_dimension(self):
        from app.services.session_vector_store import _DeterministicEmbeddingModel
        m = _DeterministicEmbeddingModel()
        assert m._dimension >= 64

    def test_custom_dimension(self, model):
        assert model._dimension == 64

    def test_get_embedding_dimension(self, model):
        assert model.get_sentence_embedding_dimension() == 64

    def test_encode_single_text_returns_list(self, model):
        result = model.encode("hello world")
        assert isinstance(result, list)
        assert len(result) == 64

    def test_encode_empty_text(self, model):
        result = model.encode("")
        assert result == [0.0] * 64

    def test_encode_none_text(self, model):
        result = model.encode(None)
        assert result == [0.0] * 64

    def test_encode_list(self, model):
        results = model.encode(["hello", "world"])
        assert len(results) == 2
        for r in results:
            assert len(r) == 64

    def test_deterministic_output(self, model):
        r1 = model.encode("test text")
        r2 = model.encode("test text")
        assert r1 == r2

    def test_different_text_different_output(self, model):
        r1 = model.encode("hello")
        r2 = model.encode("world")
        assert r1 != r2

    def test_unit_normalized(self, model):
        vec = model.encode("unit test vector")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-6


class TestSessionVectorStore:
    @pytest.fixture
    def store(self):
        with patch("pathlib.Path.mkdir"):
            with patch("app.services.session_vector_store.model_store"):
                from app.services.session_vector_store import SessionVectorStore
                s = SessionVectorStore(persist_directory="/tmp/test_store")
                s._chroma = None
                s._client = None
                s._embedding_model = None
                return s

    def test_init_creates_dir(self):
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("app.services.session_vector_store.model_store"):
                from app.services.session_vector_store import SessionVectorStore
                SessionVectorStore(persist_directory="/tmp/test_store")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_collection_name(self, store):
        assert store._collection_name("abc-123") == "session_abc_123"
        assert store._collection_name("test-session") == "session_test_session"

    def test_load_chroma_returns_none_on_import_error(self, store):
        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("no chroma")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            assert store._load_chroma() is None

    def test_get_client_raises_when_chroma_unavailable(self, store):
        with patch.object(store, "_load_chroma", return_value=None):
            with pytest.raises(RuntimeError, match="chromadb is not available"):
                store._get_client()

    def test_get_client_creates_persistent_client(self, store):
        mock_chroma = MagicMock()
        mock_chroma.PersistentClient = MagicMock(return_value="client_obj")
        with patch.object(store, "_load_chroma", return_value=mock_chroma):
            client = store._get_client()
        assert client == "client_obj"
        assert store._client == "client_obj"

    def test_get_client_caches(self, store):
        store._client = "cached"
        assert store._get_client() == "cached"

    def test_get_embedding_model_deterministic_fallback(self, store):
        import builtins
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("no st")
            return original_import(name, *args, **kwargs)

        with patch("app.services.session_vector_store.model_store.is_loaded", return_value=False):
            with patch("app.services.session_vector_store.model_store.get_model", return_value=None):
                with patch("builtins.__import__", side_effect=fake_import):
                    model = store._get_embedding_model()
                from app.services.session_vector_store import _DeterministicEmbeddingModel
                assert isinstance(model, _DeterministicEmbeddingModel)

    def test_create_collection(self, store):
        mock_client = MagicMock()
        store._client = mock_client
        with patch.object(store, "_schedule_ttl_delete"):
            name = store.create_collection("session-1")
        assert name == "session_session_1"
        mock_client.get_or_create_collection.assert_called_with("session_session_1")

    def test_add_chunks_empty(self, store):
        assert store.add_chunks("s1", []) == 0

    def test_add_chunks_skips_empty_text(self, store):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        store._client = mock_client
        model = MagicMock()
        model.encode.return_value = [0.5] * 64
        store._embedding_model = model
        result = store.add_chunks("s1", [{"text": ""}, {"text": "valid"}])
        assert result == 1
        mock_collection.add.assert_called_once()

    def test_query_empty_question(self, store):
        assert store.query("s1", "") == []

    def test_query_returns_results(self, store):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"source_doc": "a"}, {"source_doc": "b"}]],
            "distances": [[0.1, 0.3]],
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        store._client = mock_client
        model = MagicMock()
        model.encode.return_value = [0.5] * 64
        store._embedding_model = model
        results = store.query("s1", "test question", top_k=2)
        assert len(results) == 2
        assert results[0]["text"] == "doc1"
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.7

    def test_query_exception_returns_empty(self, store):
        store._client = MagicMock(side_effect=Exception("boom"))
        assert store.query("s1", "test") == []

    def test_delete_collection(self, store):
        mock_client = MagicMock()
        store._client = mock_client
        store.delete_collection("s1")
        mock_client.delete_collection.assert_called_with("session_s1")

    def test_delete_collection_failure_logged(self, store):
        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = ValueError("not found")
        store._client = mock_client
        store.delete_collection("s1")
        mock_client.delete_collection.assert_called_once()

    def test_ttl_delete_schedules_async(self, store):
        mock_loop = MagicMock()
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            store._schedule_ttl_delete("s1", 60)
        mock_loop.create_task.assert_called_once()

    def test_ttl_delete_falls_back_to_timer(self, store):
        with patch("asyncio.get_running_loop", side_effect=RuntimeError):
            with patch("threading.Timer") as mock_timer:
                store._schedule_ttl_delete("s1", 60)
            mock_timer.assert_called_once()
            mock_timer.return_value.start.assert_called_once()

    def test_persist_redis_ttl_success(self, store):
        mock_redis = MagicMock()
        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            store._persist_redis_ttl("s1", 3600)
            mock_redis.setex.assert_called_with("vector_session:s1:ttl", 3600, "active")

    def test_persist_redis_ttl_with_hyphen(self, store):
        mock_redis = MagicMock()
        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            store._persist_redis_ttl("session-123", 3600)
            assert mock_redis.setex.call_count == 2
            mock_redis.setex.assert_any_call("vector_session:session-123:ttl", 3600, "active")
            mock_redis.setex.assert_any_call("vector_session:session_123:ttl", 3600, "active")

    def test_persist_redis_ttl_exception_handled(self, store):
        with patch("app.cache.redis_cache.RedisCache.client", new_callable=PropertyMock, side_effect=Exception("Redis error")):
            store._persist_redis_ttl("s1", 3600)

    def test_delete_collection_cleans_redis_key(self, store):
        mock_client = MagicMock()
        store._client = mock_client
        mock_redis = MagicMock()
        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            store.delete_collection("s1")
            mock_redis.delete.assert_called_with("vector_session:s1:ttl")


class TestPurgeExpiredVectorSessionsTask:
    def test_purge_redis_unavailable(self):
        with patch.object(redis_cache, "_client", None), patch.object(redis_cache, "_initialized", True):
            from app.tasks.celery_tasks import purge_expired_vector_sessions

            res = purge_expired_vector_sessions()
            assert res["status"] == "redis_unavailable"
            assert res["purged_collections"] == 0

    def test_purge_chromadb_unavailable(self):
        mock_redis = MagicMock()
        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            with patch("app.services.session_vector_store.SessionVectorStore._load_chroma", return_value=None):
                from app.tasks.celery_tasks import purge_expired_vector_sessions

                res = purge_expired_vector_sessions()
                assert res["status"] == "chromadb_unavailable"

    def test_purge_active_session_not_purged(self):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = True
        mock_col = MagicMock()
        mock_col.name = "session_s1"
        mock_chroma_client = MagicMock()
        mock_chroma_client.list_collections.return_value = [mock_col]

        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            with patch("app.services.session_vector_store.SessionVectorStore._load_chroma", return_value=MagicMock()):
                with patch("app.services.session_vector_store.SessionVectorStore._get_client", return_value=mock_chroma_client):
                    with patch("app.services.session_vector_store.SessionVectorStore.delete_collection") as mock_del:
                        from app.tasks.celery_tasks import purge_expired_vector_sessions

                        res = purge_expired_vector_sessions()
                        assert res["status"] == "success"
                        assert res["purged_collections"] == 0
                        mock_del.assert_not_called()

    def test_purge_expired_session_purged(self):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = False
        mock_col = MagicMock()
        mock_col.name = "session_s1"
        mock_chroma_client = MagicMock()
        mock_chroma_client.list_collections.return_value = [mock_col]

        with patch.object(redis_cache, "_client", mock_redis), patch.object(redis_cache, "_initialized", True):
            with patch("app.services.session_vector_store.SessionVectorStore._load_chroma", return_value=MagicMock()):
                with patch("app.services.session_vector_store.SessionVectorStore._get_client", return_value=mock_chroma_client):
                    with patch("app.services.session_vector_store.SessionVectorStore.delete_collection") as mock_del:
                        from app.tasks.celery_tasks import purge_expired_vector_sessions

                        res = purge_expired_vector_sessions()
                        assert res["status"] == "success"
                        assert res["purged_collections"] == 1
                        mock_del.assert_called_once_with("s1")

