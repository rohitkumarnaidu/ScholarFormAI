# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Adaptive strategies that auto-tune based on metrics.
"""

import logging
from typing import Any

from app.pipeline.agents.metrics import PerformanceTracker
from app.pipeline.agents.ml_patterns import MLPatternDetector

logger = logging.getLogger(__name__)

# Configuration bounds
_MIN_RETRIES = 1
_MAX_RETRIES = 10
_MIN_TIMEOUT = 10
_MAX_TIMEOUT = 600
_MIN_FALLBACK = 0.1
_MAX_FALLBACK = 0.9


class AdaptiveStrategy:
    """
    Auto-tune agent behavior based on performance metrics.

    Adjusts:
    - Tool selection
    - Retry counts
    - Timeout values
    - Fallback thresholds
    """

    def __init__(
        self,
        tracker: PerformanceTracker,
        ml_detector: MLPatternDetector | None = None,
    ):
        """
        Initialize adaptive strategy.

        Args:
            tracker: Performance tracker (required)
            ml_detector: Optional ML pattern detector
        """
        if tracker is None:
            raise ValueError("tracker must not be None")
        self.tracker = tracker
        self.ml_detector = ml_detector
        self.config = self._default_config()

    def _default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "max_retries": 3,
            "timeout_seconds": 60,
            "fallback_threshold": 0.5,
            "enable_caching": True,
            "tool_priority": [
                "extract_metadata",
                "analyze_layout",
                "validate_document",
                "extract_references",
                "analyze_figures",
            ],
        }

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        """Clamp value between lo and hi."""
        return max(lo, min(hi, value))

    def adapt(self) -> dict[str, Any]:
        """
        Adapt configuration based on metrics.

        Returns:
            Updated configuration (always returns a valid dict)
        """
        try:
            summary = self.tracker.get_summary()
        except Exception as exc:
            logger.error("Failed to get tracker summary: %s", exc)
            return self.config.copy()

        if not summary or "agent" not in summary:
            return self.config.copy()

        agent_stats = summary.get("agent", {})

        try:
            # Adapt retry count based on success rate
            success_rate = float(agent_stats.get("success_rate", 1.0))
            if success_rate < 0.7:
                self.config["max_retries"] = int(
                    self._clamp(self.config["max_retries"] + 1, _MIN_RETRIES, _MAX_RETRIES)
                )
                logger.info(
                    "Increased max_retries to %d due to low success rate (%.2f)",
                    self.config["max_retries"],
                    success_rate,
                )
            elif success_rate > 0.95:
                self.config["max_retries"] = int(
                    self._clamp(self.config["max_retries"] - 1, _MIN_RETRIES, _MAX_RETRIES)
                )
                logger.info(
                    "Decreased max_retries to %d due to high success rate (%.2f)",
                    self.config["max_retries"],
                    success_rate,
                )

            # Adapt timeout based on average duration
            avg_duration = float(agent_stats.get("avg_duration", 60))
            new_timeout = avg_duration * 1.5
            self.config["timeout_seconds"] = int(self._clamp(new_timeout, _MIN_TIMEOUT, _MAX_TIMEOUT))

            # Adapt fallback threshold based on fallback rate
            fallback_rate = float(agent_stats.get("fallback_rate", 0))
            if fallback_rate > 0.3:
                self.config["fallback_threshold"] = round(
                    self._clamp(self.config["fallback_threshold"] + 0.1, _MIN_FALLBACK, _MAX_FALLBACK),
                    3,
                )
                logger.info("Increased fallback_threshold to %.3f", self.config["fallback_threshold"])
            elif fallback_rate < 0.1:
                self.config["fallback_threshold"] = round(
                    self._clamp(self.config["fallback_threshold"] - 0.1, _MIN_FALLBACK, _MAX_FALLBACK),
                    3,
                )
                logger.info("Decreased fallback_threshold to %.3f", self.config["fallback_threshold"])

        except Exception as exc:
            logger.error("Error during metric-based adaptation: %s", exc)

        # Use ML patterns if available
        if self.ml_detector is not None:
            try:
                if self.ml_detector.patterns:
                    self._adapt_from_ml_patterns()
            except Exception as exc:
                logger.error("Error accessing ML detector patterns: %s", exc)

        return self.config.copy()

    def _adapt_from_ml_patterns(self) -> None:
        """Adapt based on ML-detected patterns. Safe – never raises."""
        try:
            patterns = self.ml_detector.get_pattern_summary()
            pattern_list = patterns.get("patterns", [])

            if not pattern_list:
                return

            # Find best performing pattern
            best_pattern = max(
                pattern_list,
                key=lambda p: p.get("success_rate", 0) if isinstance(p, dict) else 0,
            )

            # Adapt tool priority based on best pattern
            common_tools = best_pattern.get("common_tools")
            if common_tools and isinstance(common_tools, list):
                self.config["tool_priority"] = common_tools
                logger.info(
                    "Adapted tool priority from ML patterns: %s",
                    self.config["tool_priority"],
                )
        except Exception as exc:
            logger.error("Error in _adapt_from_ml_patterns: %s", exc)

    def get_config(self) -> dict[str, Any]:
        """Get a copy of the current configuration."""
        return self.config.copy()

    def recommend_strategy(self, document_metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend processing strategy for a document.

        Args:
            document_metadata: Document metadata (may be empty)

        Returns:
            Recommended strategy dict (always valid)
        """
        if not isinstance(document_metadata, dict):
            logger.warning("recommend_strategy received non-dict metadata: %s", type(document_metadata))

        # Check if we have ML patterns
        if self.ml_detector is not None:
            try:
                dummy_metrics: dict[str, Any] = {
                    "duration_seconds": 30,
                    "references_count": 20,
                    "figures_count": 5,
                    "validation_errors": 0,
                    "validation_warnings": 0,
                    "retry_count": 0,
                    "fallback_triggered": False,
                    "tools_used": [],
                }

                pattern = self.ml_detector.predict_pattern(dummy_metrics)
                if pattern and isinstance(pattern, dict):
                    return {
                        "strategy": "ml_guided",
                        "expected_duration": float(pattern.get("avg_duration", 30)),
                        "recommended_tools": list(pattern.get("common_tools", [])),
                        "confidence": float(pattern.get("success_rate", 0.5)),
                    }
            except Exception as exc:
                logger.error("Error in ML-guided strategy recommendation: %s", exc)

        # Default strategy
        return {
            "strategy": "default",
            "expected_duration": 30,
            "recommended_tools": list(self.config.get("tool_priority", [])),
            "confidence": 0.5,
        }
