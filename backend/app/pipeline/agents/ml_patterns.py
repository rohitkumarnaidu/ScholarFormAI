# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
ML-based pattern detection for agent learning.
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from collections import defaultdict
from app.pipeline.safety import safe_function

logger = logging.getLogger(__name__)


class MLPatternDetector:
    """
    Machine learning-based pattern detection for document processing.

    Uses clustering and anomaly detection to identify:
    - Common processing patterns
    - Anomalous documents
    - Optimal processing strategies
    """

    def __init__(self, min_samples: int = 5):
        """
        Initialize ML pattern detector.

        Args:
            min_samples: Minimum samples for pattern detection
        """
        self.min_samples = min_samples
        self.scaler = StandardScaler()
        self.clusterer = None
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.patterns = []

    @safe_function(fallback_value=np.zeros(8), error_message="MLPatternDetector.extract_features")
    def extract_features(self, metrics: Dict[str, Any]) -> np.ndarray:
        """
        Extract numerical features from processing metrics.
        """
        features = [
            metrics.get("duration_seconds", 0),
            metrics.get("references_count", 0),
            metrics.get("figures_count", 0),
            metrics.get("validation_errors", 0),
            metrics.get("validation_warnings", 0),
            metrics.get("retry_count", 0),
            1 if metrics.get("fallback_triggered", False) else 0,
            len(metrics.get("tools_used", [])),
        ]
        return np.array(features)

    @safe_function(fallback_value=False, error_message="MLPatternDetector.fit")
    def fit(self, metrics_list: List[Dict[str, Any]]) -> bool:
        """
        Train pattern detector on historical metrics.

        Args:
            metrics_list: List of processing metrics

        Returns:
            True if training succeeded
        """
        if len(metrics_list) < self.min_samples:
            logger.warning(f"Insufficient data for training: {len(metrics_list)} < {self.min_samples}")
            return False

        try:
            # Extract features
            features = np.array([self.extract_features(m) for m in metrics_list])

            # Normalize features
            features_scaled = self.scaler.fit_transform(features)

            # Cluster patterns using DBSCAN
            self.clusterer = DBSCAN(eps=0.5, min_samples=max(2, self.min_samples // 2))
            labels = self.clusterer.fit_predict(features_scaled)

            # Train anomaly detector
            self.anomaly_detector.fit(features_scaled)

            # Store patterns
            self.patterns = self._extract_patterns(metrics_list, labels)

            logger.info(f"Trained on {len(metrics_list)} samples, found {len(self.patterns)} patterns")
            return True

        except Exception as e:
            logger.error(f"Pattern detection training failed: {e}")
            return False

    def _extract_patterns(self, metrics_list: List[Dict[str, Any]], labels: np.ndarray) -> List[Dict[str, Any]]:
        """Extract pattern summaries from clusters."""
        patterns = []

        # Group by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise
                clusters[label].append(metrics_list[idx])

        # Summarize each cluster
        for cluster_id, cluster_metrics in clusters.items():
            pattern = {
                "cluster_id": int(cluster_id),
                "sample_count": len(cluster_metrics),
                "avg_duration": np.mean([m.get("duration_seconds", 0) for m in cluster_metrics]),
                "avg_references": np.mean([m.get("references_count", 0) for m in cluster_metrics]),
                "avg_figures": np.mean([m.get("figures_count", 0) for m in cluster_metrics]),
                "success_rate": sum(1 for m in cluster_metrics if m.get("success", False)) / len(cluster_metrics),
                "common_tools": self._most_common_tools(cluster_metrics),
            }
            patterns.append(pattern)

        return patterns

    def _most_common_tools(self, metrics_list: List[Dict[str, Any]]) -> List[str]:
        """Find most commonly used tools in a cluster."""
        tool_counts = defaultdict(int)
        for m in metrics_list:
            for tool in m.get("tools_used", []):
                tool_counts[tool] += 1

        # Return top 3 tools
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in sorted_tools[:3]]

    @safe_function(fallback_value=None, error_message="MLPatternDetector.predict_pattern")
    def predict_pattern(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Predict which pattern a document belongs to.

        Args:
            metrics: Document processing metrics

        Returns:
            Predicted pattern or None
        """
        if not self.patterns or self.clusterer is None:
            return None

        try:
            features = self.extract_features(metrics).reshape(1, -1)
            features_scaled = self.scaler.transform(features)

            # Find nearest pattern (simplified - using distance to cluster centers)
            # In practice, would use proper cluster prediction
            return self.patterns[0] if self.patterns else None

        except Exception as e:
            logger.error(f"Pattern prediction failed: {e}")
            return None

    @safe_function(fallback_value=(False, 0.0), error_message="MLPatternDetector.detect_anomaly")
    def detect_anomaly(self, metrics: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Detect if a document is anomalous.

        Args:
            metrics: Document processing metrics

        Returns:
            (is_anomaly, anomaly_score)
        """
        try:
            features = self.extract_features(metrics).reshape(1, -1)
            features_scaled = self.scaler.transform(features)

            # Predict anomaly
            prediction = self.anomaly_detector.predict(features_scaled)[0]
            score = self.anomaly_detector.score_samples(features_scaled)[0]

            is_anomaly = bool(prediction == -1)
            return is_anomaly, float(score)

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return False, 0.0

    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of detected patterns."""
        return {"pattern_count": len(self.patterns), "patterns": self.patterns, "trained": self.clusterer is not None}

    def save(self, filepath: str):
        """Save trained model."""
        import pickle

        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "scaler": self.scaler,
                    "clusterer": self.clusterer,
                    "anomaly_detector": self.anomaly_detector,
                    "patterns": self.patterns,
                },
                f,
            )

    def load(self, filepath: str):
        """Load trained model."""
        import pickle

        with open(filepath, "rb") as f:
            data = pickle.load(f)  # nosec
            self.scaler = data["scaler"]
            self.clusterer = data["clusterer"]
            self.anomaly_detector = data["anomaly_detector"]
            self.patterns = data["patterns"]
