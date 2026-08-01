# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.pipeline]


class TestAdaptiveStrategyInit:
    def test_init_valid(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        strategy = AdaptiveStrategy(tracker)
        assert strategy.tracker is tracker
        assert strategy.ml_detector is None
        assert strategy.config["max_retries"] == 3

    def test_init_with_ml_detector(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        assert strategy.ml_detector is ml

    def test_init_none_tracker_raises(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        try:
            AdaptiveStrategy(None)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "tracker must not be None" in str(e)

    def test_default_config_structure(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        strategy = AdaptiveStrategy(tracker)
        config = strategy._default_config()
        assert "max_retries" in config
        assert "timeout_seconds" in config
        assert "fallback_threshold" in config
        assert "enable_caching" in config
        assert "tool_priority" in config
        assert config["max_retries"] == 3
        assert config["timeout_seconds"] == 60
        assert config["fallback_threshold"] == 0.5
        assert config["enable_caching"] is True
        assert len(config["tool_priority"]) == 5


class TestAdaptiveStrategyClamp:
    def test_clamp_within_bounds(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        assert strategy._clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamp_below_lo(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        assert strategy._clamp(-1.0, 0.0, 10.0) == 0.0

    def test_clamp_above_hi(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        assert strategy._clamp(15.0, 0.0, 10.0) == 10.0

    def test_clamp_edge_values(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        assert strategy._clamp(0.0, 0.0, 10.0) == 0.0
        assert strategy._clamp(10.0, 0.0, 10.0) == 10.0


class TestAdaptiveStrategyAdapt:
    def test_adapt_tracker_exception_returns_copy(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.side_effect = RuntimeError("boom")
        strategy = AdaptiveStrategy(tracker)
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_empty_summary_returns_copy(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {}
        strategy = AdaptiveStrategy(tracker)
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_no_agent_key_returns_copy(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {"other": {}}
        strategy = AdaptiveStrategy(tracker)
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_low_success_rate_increases_retries(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.5, "avg_duration": 30, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        initial = strategy.config["max_retries"]
        strategy.adapt()
        assert strategy.config["max_retries"] == initial + 1

    def test_adapt_high_success_rate_decreases_retries(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.99, "avg_duration": 30, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        initial = strategy.config["max_retries"]
        strategy.adapt()
        assert strategy.config["max_retries"] == max(initial - 1, 1)

    def test_adapt_timeout_based_on_duration(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 100, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.adapt()
        assert strategy.config["timeout_seconds"] == 150  # 100 * 1.5

    def test_adapt_high_fallback_rate_increases_threshold(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.5}
        }
        strategy = AdaptiveStrategy(tracker)
        initial = strategy.config["fallback_threshold"]
        strategy.adapt()
        assert strategy.config["fallback_threshold"] > initial

    def test_adapt_low_fallback_rate_decreases_threshold(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.0}
        }
        strategy = AdaptiveStrategy(tracker)
        initial = strategy.config["fallback_threshold"]
        strategy.adapt()
        assert strategy.config["fallback_threshold"] < initial

    def test_adapt_with_ml_detector_patterns(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.0}
        }
        ml = MagicMock()
        ml.patterns = [{"success_rate": 0.9}]
        ml.get_pattern_summary.return_value = {
            "patterns": [{"success_rate": 0.9, "common_tools": ["tool_a", "tool_b"]}]
        }
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        strategy.adapt()
        assert strategy.config["tool_priority"] == ["tool_a", "tool_b"]

    def test_adapt_ml_detector_patterns_exception(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.0}
        }
        ml = MagicMock()
        ml.patterns = [{"test": True}]
        ml.get_pattern_summary.side_effect = RuntimeError("ml error")
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        result = strategy.adapt()
        assert result is not None

    def test_adapt_retries_clamped_to_min(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.99, "avg_duration": 30, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.config["max_retries"] = 1
        strategy.adapt()
        assert strategy.config["max_retries"] >= 1

    def test_adapt_retries_clamped_to_max(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.0, "avg_duration": 30, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.config["max_retries"] = 10
        strategy.adapt()
        assert strategy.config["max_retries"] <= 10

    def test_adapt_fallback_clamped_to_max(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.9}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.config["fallback_threshold"] = 0.8
        strategy.adapt()
        assert strategy.config["fallback_threshold"] <= 0.9

    def test_adapt_fallback_clamped_to_min(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 30, "fallback_rate": 0.0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.config["fallback_threshold"] = 0.15
        strategy.adapt()
        assert strategy.config["fallback_threshold"] >= 0.1

    def test_adapt_timeout_clamped_to_min(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 1, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.adapt()
        assert strategy.config["timeout_seconds"] >= 10

    def test_adapt_timeout_clamped_to_max(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"success_rate": 0.8, "avg_duration": 500, "fallback_rate": 0}
        }
        strategy = AdaptiveStrategy(tracker)
        strategy.adapt()
        assert strategy.config["timeout_seconds"] <= 600


class TestAdaptiveStrategyGetConfig:
    def test_get_config_returns_copy(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        config = strategy.get_config()
        config["max_retries"] = 999
        assert strategy.config["max_retries"] == 3


class TestAdaptiveStrategyRecommendStrategy:
    def test_recommend_strategy_default(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        result = strategy.recommend_strategy({"type": "paper"})
        assert result["strategy"] == "default"
        assert result["confidence"] == 0.5
        assert result["expected_duration"] == 30

    def test_recommend_strategy_non_dict_metadata(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        strategy = AdaptiveStrategy(MagicMock())
        result = strategy.recommend_strategy(None)
        assert result["strategy"] == "default"

    def test_recommend_strategy_with_ml_pattern(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.return_value = {
            "avg_duration": 45,
            "common_tools": ["tool1", "tool2"],
            "success_rate": 0.85,
        }
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        result = strategy.recommend_strategy({"type": "paper"})
        assert result["strategy"] == "ml_guided"
        assert result["expected_duration"] == 45.0
        assert result["recommended_tools"] == ["tool1", "tool2"]
        assert result["confidence"] == 0.85

    def test_recommend_strategy_ml_returns_none(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.return_value = None
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        result = strategy.recommend_strategy({"type": "paper"})
        assert result["strategy"] == "default"

    def test_recommend_strategy_ml_exception(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.side_effect = RuntimeError("predict failed")
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        result = strategy.recommend_strategy({"type": "paper"})
        assert result["strategy"] == "default"

    def test_recommend_strategy_ml_returns_non_dict(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.return_value = "not_a_dict"
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        result = strategy.recommend_strategy({"type": "paper"})
        assert result["strategy"] == "default"


class TestAdaptiveStrategyAdaptFromMLPatterns:
    def test_adapt_from_empty_patterns(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"patterns": []}
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        strategy._adapt_from_ml_patterns()
        assert "extract_metadata" in strategy.config["tool_priority"]

    def test_adapt_from_ml_patterns_with_data(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {
            "patterns": [
                {"success_rate": 0.9, "common_tools": ["tool_x"]},
                {"success_rate": 0.7, "common_tools": ["tool_y"]},
            ]
        }
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        strategy._adapt_from_ml_patterns()
        assert strategy.config["tool_priority"] == ["tool_x"]

    def test_adapt_from_ml_patterns_exception_safe(self):
        from app.pipeline.agents.adaptive import AdaptiveStrategy
        tracker = MagicMock()
        ml = MagicMock()
        ml.get_pattern_summary.side_effect = RuntimeError("fail")
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        strategy._adapt_from_ml_patterns()
