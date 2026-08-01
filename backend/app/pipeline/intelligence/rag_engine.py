# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
RAG Engine — Local Retrieval-Augmented Generation for academic formatting guidelines.

Embedding model priority:
  1. BAAI/bge-m3  (1024d, 8192 token context, multilingual, dense+sparse)
  2. BAAI/bge-small-en-v1.5  (384d fallback if BGE-M3 fails to load)
"""

import hashlib
import json
import logging
import os
import time
from typing import Any

import numpy as np
import requests

from app.utils.singleton import get_or_create

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional ChromaDB — imported at module level so tests can patch it via:
#   with patch('app.pipeline.intelligence.rag_engine.chromadb') as mock: ...
# ---------------------------------------------------------------------------
chromadb = None  # type: ignore[assignment]
_CHROMADB_AVAILABLE = False
_CHROMADB_IMPORT_ATTEMPTED = False


def _load_chromadb():
    """Lazy-load chromadb only when a RagEngine instance needs it."""
    global chromadb, _CHROMADB_AVAILABLE, _CHROMADB_IMPORT_ATTEMPTED

    if chromadb is not None:
        _CHROMADB_AVAILABLE = True
        return chromadb

    if _CHROMADB_IMPORT_ATTEMPTED:
        return None

    _CHROMADB_IMPORT_ATTEMPTED = True
    try:
        import chromadb as chromadb_module  # type: ignore[import-not-found]

        chromadb = chromadb_module
        _CHROMADB_AVAILABLE = True
        return chromadb
    except Exception:
        _CHROMADB_AVAILABLE = False
        return None


# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #
PRIMARY_MODEL = "BAAI/bge-m3"
FALLBACK_MODEL = "BAAI/bge-small-en-v1.5"
DETERMINISTIC_FALLBACK_MODEL = "deterministic-hash-v1"
DETERMINISTIC_DIMENSION = 256

# Embedding dimensions per model (used for ChromaDB collection naming)
MODEL_DIMENSIONS = {
    PRIMARY_MODEL: 1024,
    FALLBACK_MODEL: 384,
}

# Collection names — separate collections to avoid dimension mismatches
COLLECTION_PRIMARY = "guidelines_bge_m3"  # 1024-d
COLLECTION_FALLBACK = "publisher_guidelines"  # 384-d (legacy)


class _DeterministicEmbeddingModel:
    """
    Dependency-light fallback embedding model.
    Uses token hashing into a fixed vector so semantic retrieval keeps working
    even when sentence-transformers cannot be imported.
    """

    def __init__(self, dimension: int = DETERMINISTIC_DIMENSION):
        self.dimension = max(int(dimension), 32)

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def _token_index(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, byteorder="big") % self.dimension

    def _encode_one(self, text: Any) -> list[float]:
        vec = np.zeros(self.dimension, dtype=float)
        normalized = str(text or "").lower()
        tokens = [t for t in normalized.split() if t]
        if not tokens:
            return vec.tolist()

        for token in tokens:
            vec[self._token_index(token)] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def encode(self, texts: Any):
        if isinstance(texts, (list, tuple)):
            return [self._encode_one(t) for t in texts]
        return self._encode_one(texts)


class _HuggingFaceAPIEmbeddingModel:
    """
    Uses the free Hugging Face Inference API to compute embeddings remotely.
    Saves ~1.5GB of RAM locally.
    """

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_id = model_id

        # Pull URL directly from env if provided; normalize to feature-extraction endpoint.
        custom_url = os.getenv("RAG_EMBEDDING_API_URL", "").strip()
        self.api_url = self._normalize_embedding_api_url(custom_url, model_id)

        self.token = os.getenv("HF_TOKEN")
        self.timeout_seconds = float(os.getenv("RAG_HF_TIMEOUT_SECONDS", "30"))
        self.max_retries = max(1, int(os.getenv("RAG_HF_MAX_RETRIES", "3")))
        self.retry_backoff_seconds = max(0.0, float(os.getenv("RAG_HF_RETRY_BACKOFF_SECONDS", "1.0")))

        # We need to know the dimension. all-MiniLM-L6-v2 is 384
        self.dimension = 384
        if "bge-m3" in model_id.lower():
            self.dimension = 1024

    @staticmethod
    def _default_feature_extraction_url(model_id: str) -> str:
        return f"https://router.huggingface.co/hf-inference/models/{model_id}/pipeline/feature-extraction"

    @classmethod
    def _normalize_embedding_api_url(cls, api_url: str, model_id: str) -> str:
        if not api_url:
            return cls._default_feature_extraction_url(model_id)

        normalized = api_url.rstrip("/")
        if "router.huggingface.co/hf-inference/models/" in normalized and "/pipeline/" not in normalized:
            fixed = normalized + "/pipeline/feature-extraction"
            logger.warning(
                "RagEngine: RAG_EMBEDDING_API_URL missing pipeline path; using '%s'.",
                fixed,
            )
            return fixed
        return normalized

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, texts: Any) -> list[Any]:
        if not self.token:
            logger.error("RagEngine: HF_TOKEN is missing. Cannot use HuggingFace API.")
            return []

        headers = {"Authorization": f"Bearer {self.token}"}

        # The HF feature-extraction API expects a dict: {"inputs": [...texts...]}
        is_single = isinstance(texts, str)
        payload = {"inputs": [texts] if is_single else texts}

        last_error: str | None = None
        request_url = self.api_url
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    request_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}: {response.text}"

                    # Recover automatically when a root model endpoint resolves to sentence-similarity.
                    if (
                        response.status_code == 400
                        and "SentenceSimilarityPipeline" in response.text
                        and "/pipeline/feature-extraction" not in request_url
                        and "router.huggingface.co/hf-inference/models/" in request_url
                    ):
                        request_url = request_url + "/pipeline/feature-extraction"
                        self.api_url = request_url
                        logger.warning(
                            "RagEngine: HF endpoint expected sentence-similarity payload. "
                            "Switching to feature-extraction endpoint '%s'.",
                            request_url,
                        )
                        continue

                    logger.error("RagEngine: HF API error %s", last_error)
                    if 500 <= response.status_code < 600 and attempt < self.max_retries:
                        time.sleep(self.retry_backoff_seconds * attempt)
                        continue
                    return []

                embeddings = response.json()
                if is_single and len(embeddings) > 0:
                    return embeddings[0]
                return embeddings
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    logger.warning(
                        "RagEngine: HF API request failed (attempt %d/%d): %s",
                        attempt,
                        self.max_retries,
                        e,
                    )
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                logger.error("RagEngine: HF API request failed: %s", e)
                return []

        if last_error:
            logger.error("RagEngine: HF API request failed after retries: %s", last_error)
        return []


class RagEngine:
    """
    Local RAG Engine for academic formatting guidelines.
    Uses ChromaDB with a resilient native fallback for Pydantic v1/v2 compatibility.

    Model loading order:
      1. Reuse model from global ModelStore (if pre-loaded at startup)
      2. Try BAAI/bge-m3  (best quality, 1024d, 8192 tokens)
      3. Fall back to BAAI/bge-small-en-v1.5  (lighter, 384d)
    """

    def __init__(self, persist_directory: str | None = None, auto_seed: bool | None = None):
        if persist_directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.persist_directory = os.path.join(base_dir, "db", "semantic_store")
        else:
            self.persist_directory = os.path.abspath(persist_directory)
        # Default behavior:
        # - Production/default store: auto-seed enabled
        # - Custom/test temp store: auto-seed disabled unless explicitly requested
        self.auto_seed = (persist_directory is None) if auto_seed is None else bool(auto_seed)

        os.makedirs(self.persist_directory, exist_ok=True)

        # ---- Load embedding model (with fallback) ---- #
        self.embedding_model = None
        self.active_model_name: str = ""
        self._load_embedding_model()

        # ---- Resolve collection name based on active model ---- #
        if self.active_model_name == PRIMARY_MODEL:
            self._collection_name = COLLECTION_PRIMARY
        else:
            self._collection_name = COLLECTION_FALLBACK

        # Native fallback state
        self.kb_file = os.path.join(self.persist_directory, "kb.json")
        self.knowledge_base: list[dict[str, Any]] = []

        # Attempt ChromaDB initialization
        self.chroma_enabled = False
        self.backend = "native"

        try:
            # NumPy 2.0+ removed np.float_, np.int_ etc. which ChromaDB may reference
            # Pre-patch to prevent AttributeError at import time
            if not hasattr(np, "float_"):
                np.float_ = np.float64  # Restore removed alias for compatibility
            if not hasattr(np, "int_"):
                np.int_ = np.int64

            chromadb_module = chromadb if chromadb is not None else _load_chromadb()
            if chromadb_module is None:
                raise ImportError("chromadb not installed or unavailable")
            self.client = chromadb_module.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(self._collection_name)
            self.chroma_enabled = True
            self.backend = "chromadb"
            logger.info(
                "RagEngine initialized with backend=%s model=%s collection=%s",
                self.backend,
                self.active_model_name,
                self._collection_name,
            )
        except Exception as e:
            error_msg = str(e)
            _known_compat_errors = (
                "unable to infer type",
                "chroma_db_impl",
                "np.float_",
                "Core Pydantic V1",
                "chroma_server_nofile",
                "ConfigError",
                "no such column: collections.topic",
            )
            is_known = any(s in error_msg for s in _known_compat_errors)

            if not is_known:
                logger.warning("RagEngine: ChromaDB unavailable (%s). Using native store.", error_msg)

            self.client = None
            self.collection = None
            self.backend = "native"
            self._load_native()
            logger.info(
                "RagEngine initialized with backend=%s model=%s",
                self.backend,
                self.active_model_name,
            )

        # ---- Auto-Seed Default Guidelines ---- #
        if self.auto_seed:
            self._seed_if_empty()

    def _seed_if_empty(self):
        """Auto-seed default guidelines if the knowledge base is completely empty."""
        try:
            # Check if store already has data
            if len(self.knowledge_base) > 0:
                return
            if self.chroma_enabled and self.collection.count() > 0:
                return

            default_file = os.path.join(os.path.dirname(__file__), "default_guidelines.json")
            if not os.path.exists(default_file):
                logger.warning("RagEngine: default_guidelines.json not found, cannot seed.")
                return

            logger.info("RagEngine: Knowledge base is empty. Seeding from default_guidelines.json...")
            with open(default_file) as f:
                payload = json.load(f)

            if isinstance(payload, dict):
                guidelines = payload.get("guidelines", [])
            elif isinstance(payload, list):
                guidelines = payload
            else:
                guidelines = []

            for item in guidelines:
                if not isinstance(item, dict):
                    continue
                publisher = item.get("publisher") or item.get("template")
                section = item.get("section") or item.get("category")
                text = item.get("text") or item.get("guideline")
                if not publisher or not section or not text:
                    continue
                self.add_guideline(
                    publisher=str(publisher), section=str(section), text=str(text), metadata={"source": "auto-seed"}
                )
            logger.info("RagEngine: Auto-seeding complete.")
        except Exception as e:
            logger.error("RagEngine: Failed to seed default guidelines: %s", e)

    # ------------------------------------------------------------------ #
    #  Model loading
    # ------------------------------------------------------------------ #
    @staticmethod
    def _coerce_embedding_vector(raw_embedding: Any) -> list[float]:
        """
        Convert an embedding object to a JSON-safe numeric list.
        Returns [] when conversion is not possible.
        """
        if raw_embedding is None:
            return []

        if hasattr(raw_embedding, "tolist"):
            raw_embedding = raw_embedding.tolist()

        if (
            isinstance(raw_embedding, (list, tuple))
            and raw_embedding
            and isinstance(raw_embedding[0], (list, tuple, np.ndarray))
        ):
            raw_embedding = raw_embedding[0]

        if not isinstance(raw_embedding, (list, tuple, np.ndarray)):
            return []

        try:
            return [float(v) for v in raw_embedding]
        except Exception as e:
            logger.warning("RagEngine: Failed to coerce embedding vector: %s", e)
            return []

    def _is_reusable_embedding_model(self, candidate: Any) -> tuple[bool, int | None]:
        """
        Validate a model loaded from ModelStore before reusing it.
        """
        try:
            if candidate is None or not hasattr(candidate, "encode"):
                return False, None
            if not hasattr(candidate, "get_sentence_embedding_dimension"):
                return False, None

            dim = int(candidate.get_sentence_embedding_dimension())
            if dim <= 0:
                return False, None

            probe = self._coerce_embedding_vector(candidate.encode("healthcheck"))
            if not probe:
                return False, None
            return True, dim
        except Exception as e:
            logger.warning("RagEngine: Embedding model validation failed: %s", e)
            return False, None

    def _activate_deterministic_embedding(self, model_store: Any, reason: str):
        """
        Ensure embedding functionality remains available even when transformer
        models cannot be loaded in the current environment.
        """
        self.embedding_model = _DeterministicEmbeddingModel(DETERMINISTIC_DIMENSION)
        self.active_model_name = DETERMINISTIC_FALLBACK_MODEL
        try:
            model_store.set_model("embedding_model", self.embedding_model)
        except Exception as e:
            logger.warning("RagEngine: Failed to store embedding model in ModelStore: %s", e)
            pass
        logger.warning(
            "RagEngine: %s Using deterministic fallback model '%s' (dim=%d).",
            reason,
            DETERMINISTIC_FALLBACK_MODEL,
            DETERMINISTIC_DIMENSION,
        )

    def _load_embedding_model(self):
        """Load the embedding model with graceful fallback."""
        # 1. Check ModelStore for a pre-loaded model
        from app.config.settings import settings
        from app.services.model_store import model_store

        # Check for remote API override first
        provider = os.getenv("RAG_EMBEDDING_PROVIDER", "").lower()
        if (settings.LOW_MEMORY_MODE or not settings.RAG_USE_TRANSFORMERS) and provider in (
            "huggingface_api",
            "hf_api",
        ):
            model_id = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            logger.info(f"RagEngine: RAG_USE_TRANSFORMERS=false. Using HuggingFace API remotely with '{model_id}'.")

            hf_model = _HuggingFaceAPIEmbeddingModel(model_id=model_id)
            # Do a quick test
            probe = self._coerce_embedding_vector(hf_model.encode("healthcheck"))
            if probe:
                self.embedding_model = hf_model
                self.active_model_name = "huggingface_api_" + model_id
                model_store.set_model("embedding_model", self.embedding_model)
                logger.info(f"RagEngine: HuggingFace API connected successfully (dim={hf_model.dimension}).")
                return
            else:
                logger.warning("RagEngine: HuggingFace API failed health check. Falling back to deterministic hash.")

        if settings.LOW_MEMORY_MODE or not settings.RAG_USE_TRANSFORMERS:
            reason = "Low-memory mode enabled." if settings.LOW_MEMORY_MODE else "RAG_USE_TRANSFORMERS=false."
            self._activate_deterministic_embedding(model_store, reason)
            return

        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            self._activate_deterministic_embedding(
                model_store,
                f"SentenceTransformer import failed ({exc}).",
            )
            return

        if model_store.is_loaded("embedding_model"):
            candidate = model_store.get_model("embedding_model")
            is_usable, test_dim = self._is_reusable_embedding_model(candidate)
            if is_usable:
                self.embedding_model = candidate
                if test_dim == MODEL_DIMENSIONS[PRIMARY_MODEL]:
                    self.active_model_name = PRIMARY_MODEL
                else:
                    self.active_model_name = FALLBACK_MODEL
                logger.info(
                    "RagEngine: Reusing global SentenceTransformer from ModelStore (dim=%s, model=%s).",
                    test_dim,
                    self.active_model_name,
                )
                return
            logger.warning("RagEngine: Ignoring invalid embedding model from ModelStore and reloading.")

        # 2. Try loading BGE-M3 (primary)
        try:
            logger.info("RagEngine: Loading primary model '%s'...", PRIMARY_MODEL)
            self.embedding_model = SentenceTransformer(PRIMARY_MODEL)
            self.active_model_name = PRIMARY_MODEL
            # Register in ModelStore for reuse
            model_store.set_model("embedding_model", self.embedding_model)
            logger.info(
                "RagEngine: Primary model loaded successfully (dim=%s).",
                self.embedding_model.get_sentence_embedding_dimension(),
            )
            return
        except Exception as exc:
            logger.warning(
                "RagEngine: Failed to load primary model '%s': %s. Falling back to '%s'.",
                PRIMARY_MODEL,
                exc,
                FALLBACK_MODEL,
            )

        # 3. Fallback to bge-small-en-v1.5
        try:
            logger.info("RagEngine: Loading fallback model '%s'...", FALLBACK_MODEL)
            self.embedding_model = SentenceTransformer(FALLBACK_MODEL)
            self.active_model_name = FALLBACK_MODEL
            model_store.set_model("embedding_model", self.embedding_model)
            logger.info(
                "RagEngine: Fallback model loaded (dim=%s).",
                self.embedding_model.get_sentence_embedding_dimension(),
            )
        except Exception as exc:
            logger.error(
                "RagEngine: Failed to load fallback model '%s': %s. Using deterministic fallback.",
                FALLBACK_MODEL,
                exc,
            )
            self._activate_deterministic_embedding(
                model_store,
                f"Primary and fallback transformer models unavailable ({exc}).",
            )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def add_guideline(self, publisher: str, section: str, text: str, metadata: dict | None = None):
        """Add a guideline rule to the store."""
        full_metadata = metadata or {}
        full_metadata.update({"publisher": publisher.upper(), "section": section.lower()})

        if self.chroma_enabled:
            doc_id = f"{publisher}_{section}_{hash(text)}"
            self.collection.add(ids=[doc_id], documents=[text], metadatas=[full_metadata])

        # Always update native store for consistent fallback
        if self.embedding_model is not None:
            embedding = self._coerce_embedding_vector(self.embedding_model.encode(text))
        else:
            embedding = []
        self.knowledge_base.append({"text": text, "metadata": full_metadata, "embedding": embedding})
        self._save_native()

    def query_guidelines(self, publisher: str, intent: str, top_k: int = 3) -> list[str]:
        """Retrieve the most relevant guideline text."""
        if self.chroma_enabled:
            try:
                results = self.collection.query(
                    query_texts=[intent],
                    n_results=top_k,
                    where={"publisher": publisher.upper()},
                )
                if results and results["documents"]:
                    return results["documents"][0]
            except Exception as e:
                logger.warning("RagEngine: Chroma query failed (%s). Falling back to native.", e)

        # Native Fallback: Cosine Similarity
        if self.embedding_model is None:
            return []

        try:
            query_emb_vec = self._coerce_embedding_vector(self.embedding_model.encode(intent))
            if not query_emb_vec:
                return []
            query_emb = np.array(query_emb_vec, dtype=float)
            scores = []
            for item in self.knowledge_base:
                if item["metadata"]["publisher"] == publisher.upper():
                    item_emb_vec = self._coerce_embedding_vector(item.get("embedding", []))
                    if not item_emb_vec:
                        continue
                    item_emb = np.array(item_emb_vec, dtype=float)
                    if item_emb.shape != query_emb.shape:
                        continue
                    denom = np.linalg.norm(query_emb) * np.linalg.norm(item_emb)
                    if denom == 0:
                        continue
                    sim = np.dot(query_emb, item_emb) / denom
                    scores.append((sim, item["text"]))

            scores.sort(key=lambda x: x[0], reverse=True)
            return [s[1] for s in scores[:top_k]]
        except Exception as e:
            logger.warning("RagEngine: Native query failed (%s). Returning empty list.", e)
            return []

    def query_rules(self, template_name: str, section_name: str, top_k: int = 2) -> list[dict[str, Any]]:
        """
        [PHASE-2 INTERFACE ADAPTER]
        Required by PipelineOrchestrator.
        Returns a list of rule dictionaries: [{"text": "...", "metadata": {...}}]
        """
        try:
            publisher = template_name.upper() if template_name else "IEEE"
            intent = section_name.lower() if section_name else "general"

            guidelines = self.query_guidelines(publisher, intent, top_k=top_k)

            return [{"text": txt, "metadata": {"publisher": publisher, "section": intent}} for txt in guidelines]
        except Exception as e:
            logger.warning("RagEngine Guard: query_rules failed: %s. Returning empty list.", e)
            return []

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #
    def _save_native(self):
        with open(self.kb_file, "w") as f:
            json.dump(self.knowledge_base, f)

    def _load_native(self):
        if os.path.exists(self.kb_file):
            with open(self.kb_file) as f:
                self.knowledge_base = json.load(f)

    def reset(self):
        """Clear all indexed guidelines."""
        if self.chroma_enabled:
            try:
                self.client.delete_collection(self._collection_name)
                self.collection = self.client.get_or_create_collection(self._collection_name)
            except Exception as e:
                logger.warning("RagEngine: Failed to reset ChromaDB collection: %s", e)
                pass
        self.knowledge_base = []
        if os.path.exists(self.kb_file):
            os.remove(self.kb_file)


# --------------------------------------------------------------------------- #
#  Singleton Access
# --------------------------------------------------------------------------- #
_rag_engine = None


def get_rag_engine() -> RagEngine:
    global _rag_engine
    _rag_engine = get_or_create(_rag_engine, RagEngine)
    return _rag_engine
