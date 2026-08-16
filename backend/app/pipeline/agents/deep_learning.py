# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep learning integration using transformers for pattern detection.
"""

import logging
from typing import Any

import numpy as np


import json

from sklearn.cluster import KMeans

from app.pipeline.safety import safe_function

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoModel, AutoTokenizer
except ImportError:
    torch = None
    AutoModel = None
    AutoTokenizer = None


class TransformerPatternDetector:
    """
    Use transformer models for advanced pattern detection.

    Features:
    - Document embedding using BERT/SciBERT
    - Semantic similarity detection
    - Advanced clustering
    - Transfer learning from scientific literature
    """

    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased", device: str = "cpu"):
        """
        Initialize transformer-based pattern detector.

        Args:
            model_name: HuggingFace model name (default: SciBERT)
            device: Device to use (cpu/cuda)
        """
        self.device = device
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return

        self._initialized = True
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            logger.info(f"Loading transformer model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)  # nosec
            self.model = AutoModel.from_pretrained(self.model_name).to(self.device)  # nosec
            self.model.eval()
            logger.info("Transformer model loaded successfully")
        except ImportError:
            logger.warning("TransformerPatternDetector: torch/transformers unavailable; running in fallback mode.")
        except Exception as e:
            logger.warning(
                "Failed to load transformer model %s: %s. Falling back to zero embeddings.",
                self.model_name,
                e,
            )
            self.tokenizer = None
            self.model = None

        self.embeddings_cache = {}
        self.clusters = None
        self.cluster_centers = None

    @safe_function(fallback_value=np.zeros(768), error_message="TransformerPatternDetector.encode_document")
    def encode_document(self, text: str, max_length: int = 512) -> np.ndarray:
        """
        Encode document to embedding vector.

        Args:
            text: Document text
            max_length: Maximum sequence length

        Returns:
            Document embedding vector
        """
        # Check cache
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        if self.tokenizer is None or self.model is None or torch is None:
            return np.zeros(768)

        try:
            # Tokenize
            inputs = self.tokenizer(text, max_length=max_length, truncation=True, padding=True, return_tensors="pt").to(
                self.device
            )

            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use [CLS] token embedding
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]

            # Cache
            self.embeddings_cache[text] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return np.zeros(768)  # Default BERT embedding size

    @safe_function(fallback_value={"patterns": [], "clusters": {}, "confidence": 0.0})
    def detect_patterns(self, document_text: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect semantic patterns across document sections."""
        self._ensure_initialized()
        if not document_text or not sections:
            return {"patterns": [], "clusters": {}, "confidence": 0.0}

    @safe_function(fallback_value=np.zeros(768), error_message="TransformerPatternDetector.encode_metadata")
    def encode_metadata(self, metadata: dict[str, Any]) -> np.ndarray:
        """
        Encode document metadata to text and then to embedding.

        Args:
            metadata: Document metadata

        Returns:
            Metadata embedding
        """
        # Convert metadata to text
        text_parts = []

        if "title" in metadata:
            text_parts.append(f"Title: {metadata['title']}")

        if "authors" in metadata:
            authors = ", ".join(metadata["authors"][:5])
            text_parts.append(f"Authors: {authors}")

        if "abstract" in metadata:
            text_parts.append(f"Abstract: {metadata['abstract'][:500]}")

        if "venue" in metadata:
            text_parts.append(f"Venue: {metadata['venue']}")

        text = " ".join(text_parts)
        return self.encode_document(text)

    @safe_function(fallback_value=False, error_message="TransformerPatternDetector.fit_clusters")
    def fit_clusters(self, embeddings: list[np.ndarray], n_clusters: int = 5) -> bool:
        """
        Cluster document embeddings.

        Args:
            embeddings: List of document embeddings
            n_clusters: Number of clusters

        Returns:
            True if clustering succeeded
        """
        if len(embeddings) < n_clusters:
            logger.warning(f"Insufficient embeddings: {len(embeddings)} < {n_clusters}")
            return False

        try:
            embeddings_array = np.array(embeddings)

            # Perform clustering
            self.clusters = KMeans(n_clusters=n_clusters, random_state=42)
            self.clusters.fit(embeddings_array)
            self.cluster_centers = self.clusters.cluster_centers_

            logger.info(f"Clustered {len(embeddings)} documents into {n_clusters} clusters")
            return True

        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return False

    @safe_function(fallback_value=-1, error_message="TransformerPatternDetector.predict_cluster")
    def predict_cluster(self, embedding: np.ndarray) -> int:
        """
        Predict cluster for an embedding.

        Args:
            embedding: Document embedding

        Returns:
            Cluster ID
        """
        if self.clusters is None:
            return -1

        return int(self.clusters.predict([embedding])[0])

    @safe_function(fallback_value=0.0, error_message="TransformerPatternDetector.compute_similarity")
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between embeddings.
        """
        from numpy.linalg import norm

        try:
            similarity = np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2))
            return float(similarity)
        except Exception:
            return 0.0

    @safe_function(fallback_value=[], error_message="TransformerPatternDetector.find_similar_documents")
    def find_similar_documents(
        self, query_embedding: np.ndarray, document_embeddings: list[tuple[str, np.ndarray]], top_k: int = 5
    ) -> list[tuple[str, float]]:
        """
        Find similar documents using semantic similarity.
        """
        similarities = []

        for doc_id, embedding in document_embeddings:
            similarity = self.compute_similarity(query_embedding, embedding)
            similarities.append((doc_id, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    @safe_function(fallback_value=(False, 0.0), error_message="TransformerPatternDetector.detect_anomaly_semantic")
    def detect_anomaly_semantic(self, embedding: np.ndarray, threshold: float = 0.5) -> tuple[bool, float]:
        """
        Detect anomaly based on semantic distance from cluster centers.

        Args:
            embedding: Document embedding
            threshold: Similarity threshold

        Returns:
            (is_anomaly, max_similarity)
        """
        if self.cluster_centers is None:
            return False, 0.0

        # Compute similarity to all cluster centers
        max_similarity = 0.0
        for center in self.cluster_centers:
            similarity = self.compute_similarity(embedding, center)
            max_similarity = max(max_similarity, similarity)

        is_anomaly = bool(max_similarity < threshold)
        return is_anomaly, float(max_similarity)

    @safe_function(fallback_value=None, error_message="TransformerPatternDetector.save_model")
    def save_model(self, filepath: str):
        """Save embeddings cache and clusters."""
        data = {
            "model_name": self.model_name,
            "cluster_centers": self.cluster_centers.tolist() if self.cluster_centers is not None else None,
            "embeddings_cache_keys": list(self.embeddings_cache.keys()),
        }

        with open(filepath, "w") as f:
            json.dump(data, f)

        # Save embeddings separately (binary)
        if self.embeddings_cache:
            np.save(filepath + ".embeddings.npy", np.array(list(self.embeddings_cache.values())))

    def _get_embeddings(self, texts: list[str]) -> np.ndarray | None:
        """Get BERT embeddings for texts."""
        self._ensure_initialized()
        if not self.model or not self.tokenizer:
            return None

    def get_summary(self) -> dict[str, Any]:
        """Get model summary."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "cached_embeddings": len(self.embeddings_cache),
            "clusters_trained": self.clusters is not None,
            "n_clusters": len(self.cluster_centers) if self.cluster_centers is not None else 0,
        }
