# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.model_store import model_store

logger = logging.getLogger(__name__)

MODEL_NAME = "multi-qa-MiniLM-L6-v2"
MODEL_KEY = "embedding_model_session"
DEFAULT_TTL_SECONDS = 24 * 60 * 60


class _DeterministicEmbeddingModel:
    """Fallback embedding model when sentence-transformers is unavailable."""

    def __init__(self, dimension: int = 256) -> None:
        import hashlib
        import numpy as np

        self._hashlib = hashlib
        self._np = np
        self._dimension = max(int(dimension), 64)

    def get_sentence_embedding_dimension(self) -> int:
        return self._dimension

    def _encode_one(self, text: Any) -> List[float]:
        vec = self._np.zeros(self._dimension, dtype=float)
        normalized = str(text or "").lower()
        tokens = [t for t in normalized.split() if t]
        if not tokens:
            return vec.tolist()
        for token in tokens:
            digest = self._hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest, byteorder="big") % self._dimension
            vec[idx] += 1.0
        norm = self._np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def encode(self, texts: Any):
        if isinstance(texts, (list, tuple)):
            return [self._encode_one(t) for t in texts]
        return self._encode_one(texts)


class SessionVectorStore:
    def __init__(self, persist_directory: Optional[str] = None) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        self.persist_directory = Path(persist_directory) if persist_directory else base_dir / "db" / "session_store"
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._chroma = None
        self._embedding_model = None

    def _load_chroma(self):
        if self._chroma is not None:
            return self._chroma
        try:
            import chromadb

            self._chroma = chromadb
            return self._chroma
        except Exception as exc:
            logger.warning("SessionVectorStore: chromadb unavailable: %s", exc)
            self._chroma = None
            return None

    def _get_client(self):
        if self._client is not None:
            return self._client
        chroma = self._load_chroma()
        if chroma is None:
            raise RuntimeError("chromadb is not available")
        self._client = chroma.PersistentClient(path=str(self.persist_directory))
        return self._client

    def _get_embedding_model(self):
        if self._embedding_model is not None:
            return self._embedding_model
        if model_store.is_loaded(MODEL_KEY):
            self._embedding_model = model_store.get_model(MODEL_KEY)
            return self._embedding_model
        try:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(MODEL_NAME)
            model_store.set_model(MODEL_KEY, self._embedding_model)
            logger.info("SessionVectorStore: loaded embedding model %s", MODEL_NAME)
            return self._embedding_model
        except Exception as exc:
            logger.warning("SessionVectorStore: sentence-transformers unavailable: %s", exc)
            self._embedding_model = _DeterministicEmbeddingModel()
            model_store.set_model(MODEL_KEY, self._embedding_model)
            return self._embedding_model

    def _collection_name(self, session_id: str) -> str:
        safe = str(session_id).replace("-", "_")
        return f"session_{safe}"

    def create_collection(self, session_id: str) -> str:
        client = self._get_client()
        name = self._collection_name(session_id)
        client.get_or_create_collection(name)
        self._schedule_ttl_delete(session_id, DEFAULT_TTL_SECONDS)
        return name

    def _schedule_ttl_delete(self, session_id: str, ttl_seconds: int) -> None:
        self._persist_redis_ttl(session_id, ttl_seconds)
        # Volatile in-memory timers have been removed in favor of Redis TTL
        # and the scheduled purge_expired_vector_sessions Celery task.

    def _persist_redis_ttl(self, session_id: str, ttl_seconds: int) -> None:
        """Persist vector session TTL key to Redis if available."""
        try:
            from app.cache.redis_cache import redis_cache

            r_client = redis_cache.client
            if r_client:
                key1 = f"vector_session:{session_id}:ttl"
                r_client.setex(key1, int(ttl_seconds), "active")
                raw_id = self._collection_name(session_id)[len("session_") :]
                if raw_id != str(session_id):
                    key2 = f"vector_session:{raw_id}:ttl"
                    r_client.setex(key2, int(ttl_seconds), "active")
                logger.info("Persisted Redis TTL for vector session %s (%ds)", session_id, ttl_seconds)
        except Exception as exc:
            logger.warning("SessionVectorStore: Failed to persist Redis TTL for %s: %s", session_id, exc)

    def add_chunks(self, session_id: str, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        client = self._get_client()
        collection = client.get_or_create_collection(self._collection_name(session_id))
        model = self._get_embedding_model()

        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []
        embeddings: List[List[float]] = []

        for idx, chunk in enumerate(chunks):
            text = str(chunk.get("text") or "").strip()
            if not text:
                continue
            metadata = {
                "source_doc": chunk.get("source_doc"),
                "section": chunk.get("section"),
                "page": chunk.get("page"),
            }
            embedding = model.encode(text)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            documents.append(text)
            metadatas.append(metadata)
            ids.append(f"{session_id}_{idx}")
            embeddings.append([float(v) for v in embedding])

        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
        return len(documents)

    def query(self, session_id: str, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not question:
            return []
        try:
            client = self._get_client()
            collection = client.get_or_create_collection(self._collection_name(session_id))
            model = self._get_embedding_model()
            embedding = model.encode(question)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            results = collection.query(
                query_embeddings=[embedding],
                n_results=int(top_k or 5),
                include=["documents", "metadatas", "distances"],
            )
            documents = results.get("documents", [[]])[0] if results else []
            metadatas = results.get("metadatas", [[]])[0] if results else []
            distances = results.get("distances", [[]])[0] if results else []
            output: List[Dict[str, Any]] = []
            for text, meta, dist in zip(documents, metadatas, distances):
                score = 1.0 - float(dist) if dist is not None else 0.0
                output.append(
                    {
                        "text": text,
                        "source_doc": (meta or {}).get("source_doc"),
                        "section": (meta or {}).get("section"),
                        "score": score,
                    }
                )
            return output
        except Exception as exc:
            logger.warning("SessionVectorStore query failed for %s: %s", session_id, exc)
            return []

    def delete_collection(self, session_id: str) -> None:
        client = self._get_client()
        name = self._collection_name(session_id)
        try:
            client.delete_collection(name)
        except Exception as exc:
            logger.debug("SessionVectorStore: delete_collection failed for %s: %s", session_id, exc)
        try:
            from app.cache.redis_cache import redis_cache

            r_client = redis_cache.client
            if r_client:
                r_client.delete(f"vector_session:{session_id}:ttl")
                raw_id = name[len("session_") :]
                if raw_id != str(session_id):
                    r_client.delete(f"vector_session:{raw_id}:ttl")
        except Exception:
            pass
