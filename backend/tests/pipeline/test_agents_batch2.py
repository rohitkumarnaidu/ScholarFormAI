# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Tests for adaptive, autoscaling, realtime_adaptation, and streaming agents."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from app.pipeline.agents.adaptive import (
    _MAX_FALLBACK,
    _MAX_RETRIES,
    _MAX_TIMEOUT,
    _MIN_FALLBACK,
    _MIN_RETRIES,
    _MIN_TIMEOUT,
    AdaptiveStrategy,
)
from app.pipeline.agents.autoscaling import AutoScalingManager
from app.pipeline.agents.realtime_adaptation import (
    _MAX_ERRORS_BEFORE_STOP,
    RealTimeAdaptiveAgent,
)
from app.pipeline.agents.realtime_adaptation import (
    _MAX_TIMEOUT as RT_MAX_TIMEOUT,
)
from app.pipeline.agents.realtime_adaptation import (
    _MIN_TIMEOUT as RT_MIN_TIMEOUT,
)
from app.pipeline.agents.streaming import StreamingAgentCallback

# =============================================================================
# Helpers
# =============================================================================

def _make_tracker(summary: dict[str, Any]) -> MagicMock:
    """Build a mock PerformanceTracker that returns the given summary."""
    tracker = MagicMock()
    tracker.get_summary.return_value = summary
    return tracker


def _make_ml_detector(patterns: list | None = None, pattern_summary: dict | None = None) -> MagicMock:
    """Build a mock MLPatternDetector."""
    detector = MagicMock()
    detector.patterns = patterns or []
    detector.get_pattern_summary.return_value = pattern_summary or {"patterns": []}
    detector.predict_pattern.return_value = None
    return detector


# =============================================================================
# AdaptiveStrategy
# =============================================================================

class TestAdaptiveStrategy:
    """Tests for AdaptiveStrategy."""

    def test_constructor_requires_tracker(self):
        with pytest.raises(ValueError, match="tracker must not be None"):
            AdaptiveStrategy(tracker=None)

    def test_constructor_defaults(self):
        tracker = _make_tracker({})
        strategy = AdaptiveStrategy(tracker)
        assert strategy.tracker is tracker
        assert strategy.ml_detector is None
        cfg = strategy.config
        assert cfg["max_retries"] == 3
        assert cfg["timeout_seconds"] == 60
        assert cfg["fallback_threshold"] == 0.5
        assert cfg["enable_caching"] is True
        assert len(cfg["tool_priority"]) == 5

    def test_constructor_with_ml_detector(self):
        tracker = _make_tracker({})
        ml = _make_ml_detector()
        strategy = AdaptiveStrategy(tracker, ml_detector=ml)
        assert strategy.ml_detector is ml

    def test_get_config_returns_copy(self):
        tracker = _make_tracker({})
        strategy = AdaptiveStrategy(tracker)
        cfg1 = strategy.get_config()
        cfg2 = strategy.get_config()
        assert cfg1 == cfg2
        cfg1["max_retries"] = 99
        assert strategy.config["max_retries"] != 99

    def test_adapt_returns_copy_on_tracker_exception(self):
        tracker = MagicMock()
        tracker.get_summary.side_effect = RuntimeError("boom")
        strategy = AdaptiveStrategy(tracker)
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_returns_copy_on_empty_summary(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_returns_copy_when_summary_missing_agent_key(self):
        strategy = AdaptiveStrategy(_make_tracker({"other": {}}))
        result = strategy.adapt()
        assert result == strategy.config

    def test_adapt_increases_retries_on_low_success_rate(self):
        summary = {"agent": {"success_rate": 0.5, "avg_duration": 60, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        assert strategy.config["max_retries"] == 3
        strategy.adapt()
        assert strategy.config["max_retries"] == 4

    def test_adapt_decreases_retries_on_high_success_rate(self):
        summary = {"agent": {"success_rate": 0.99, "avg_duration": 60, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.config["max_retries"] = 5
        strategy.adapt()
        assert strategy.config["max_retries"] == 4

    def test_adapt_clamps_retries_to_minimum(self):
        summary = {"agent": {"success_rate": 0.99, "avg_duration": 60, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.config["max_retries"] = _MIN_RETRIES
        strategy.adapt()
        assert strategy.config["max_retries"] >= _MIN_RETRIES

    def test_adapt_clamps_retries_to_maximum(self):
        summary = {"agent": {"success_rate": 0.1, "avg_duration": 60, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.config["max_retries"] = _MAX_RETRIES
        strategy.adapt()
        assert strategy.config["max_retries"] <= _MAX_RETRIES

    def test_adapt_adjusts_timeout_based_on_avg_duration(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 200, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.adapt()
        assert strategy.config["timeout_seconds"] == 300  # 200 * 1.5

    def test_adapt_clamps_timeout_to_minimum(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 2, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.adapt()
        assert strategy.config["timeout_seconds"] >= _MIN_TIMEOUT

    def test_adapt_clamps_timeout_to_maximum(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 1000, "fallback_rate": 0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.adapt()
        assert strategy.config["timeout_seconds"] <= _MAX_TIMEOUT

    def test_adapt_increases_fallback_threshold_on_high_fallback_rate(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0.5}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        old = strategy.config["fallback_threshold"]
        strategy.adapt()
        assert strategy.config["fallback_threshold"] > old

    def test_adapt_decreases_fallback_threshold_on_low_fallback_rate(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0.0}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        old = strategy.config["fallback_threshold"]
        strategy.adapt()
        assert strategy.config["fallback_threshold"] < old

    def test_adapt_clamps_fallback_threshold(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0.5}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.config["fallback_threshold"] = _MAX_FALLBACK
        strategy.adapt()
        assert strategy.config["fallback_threshold"] <= _MAX_FALLBACK

        strategy2 = AdaptiveStrategy(_make_tracker(summary))
        strategy2.config["fallback_threshold"] = _MIN_FALLBACK
        strategy2.adapt()
        assert strategy2.config["fallback_threshold"] >= _MIN_FALLBACK

    def test_adapt_uses_ml_patterns_when_available(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0}}
        pattern_summary = {
            "patterns": [
                {"success_rate": 0.9, "common_tools": ["tool_a", "tool_b"]}
            ]
        }
        ml = _make_ml_detector(patterns=[{"dummy": True}], pattern_summary=pattern_summary)
        strategy = AdaptiveStrategy(_make_tracker(summary), ml_detector=ml)
        strategy.adapt()
        assert strategy.config["tool_priority"] == ["tool_a", "tool_b"]

    def test_adapt_survives_ml_detector_error(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0}}
        ml = MagicMock()
        type(ml).patterns = PropertyMock(side_effect=RuntimeError("ml fail"))
        strategy = AdaptiveStrategy(_make_tracker(summary), ml_detector=ml)
        result = strategy.adapt()
        assert isinstance(result, dict)

    def test_recommend_strategy_default(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        result = strategy.recommend_strategy({})
        assert result["strategy"] == "default"
        assert result["confidence"] == 0.5
        assert result["expected_duration"] == 30
        assert "recommended_tools" in result

    def test_recommend_strategy_handles_non_dict_metadata(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        result = strategy.recommend_strategy("not-a-dict")
        assert result["strategy"] == "default"

    def test_recommend_strategy_uses_ml_detector(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = _make_ml_detector(
            patterns=[{"dummy": True}],
            pattern_summary={"patterns": []},
        )
        ml.predict_pattern.return_value = {
            "avg_duration": 45,
            "common_tools": ["x", "y"],
            "success_rate": 0.85,
        }
        strategy.ml_detector = ml
        result = strategy.recommend_strategy({"size": "big"})
        assert result["strategy"] == "ml_guided"
        assert result["expected_duration"] == 45
        assert result["recommended_tools"] == ["x", "y"]
        assert result["confidence"] == 0.85

    def test_recommend_strategy_survives_ml_error(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = MagicMock()
        ml.patterns = [{"dummy": True}]
        ml.predict_pattern.side_effect = RuntimeError("predict fail")
        strategy.ml_detector = ml
        result = strategy.recommend_strategy({})
        assert result["strategy"] == "default"

    def test_recommend_strategy_survives_ml_non_dict_result(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = _make_ml_detector(patterns=[{"dummy": True}])
        ml.predict_pattern.return_value = None
        strategy.ml_detector = ml
        result = strategy.recommend_strategy({})
        assert result["strategy"] == "default"

    def test_clamp(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        assert strategy._clamp(5, 0, 10) == 5
        assert strategy._clamp(-1, 0, 10) == 0
        assert strategy._clamp(15, 0, 10) == 10

    def test_adapt_from_ml_patterns_empty_patterns(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = _make_ml_detector(patterns=[], pattern_summary={"patterns": []})
        strategy.ml_detector = ml
        old_priority = strategy.config["tool_priority"].copy()
        strategy._adapt_from_ml_patterns()
        assert strategy.config["tool_priority"] == old_priority

    def test_adapt_from_ml_patterns_no_common_tools(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = _make_ml_detector(
            patterns=[{"dummy": True}],
            pattern_summary={"patterns": [{"success_rate": 0.9}]},
        )
        strategy.ml_detector = ml
        strategy._adapt_from_ml_patterns()
        # No common_tools key -> priority unchanged
        assert strategy.config["tool_priority"] is not None

    def test_adapt_from_ml_patterns_returns_empty_list(self):
        strategy = AdaptiveStrategy(_make_tracker({}))
        ml = _make_ml_detector(
            patterns=[{"dummy": True}],
            pattern_summary={
                "patterns": [{"success_rate": 0.9, "common_tools": ["a", "b"]}]
            },
        )
        strategy.ml_detector = ml
        strategy._adapt_from_ml_patterns()
        assert strategy.config["tool_priority"] == ["a", "b"]

    def test_adapt_mid_range_success_rate_no_change(self):
        summary = {"agent": {"success_rate": 0.85, "avg_duration": 60, "fallback_rate": 0.15}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        strategy.config["max_retries"] = 5
        strategy.adapt()
        # success_rate 0.85 is between 0.7 and 0.95, so retries unchanged
        assert strategy.config["max_retries"] == 5

    def test_adapt_mid_range_fallback_rate_no_change(self):
        summary = {"agent": {"success_rate": 1.0, "avg_duration": 60, "fallback_rate": 0.15}}
        strategy = AdaptiveStrategy(_make_tracker(summary))
        old = strategy.config["fallback_threshold"]
        strategy.adapt()
        assert strategy.config["fallback_threshold"] == old


# =============================================================================
# AutoScalingManager
# =============================================================================

class TestAutoScalingManager:
    """Tests for AutoScalingManager."""

    def test_constructor_defaults(self):
        mgr = AutoScalingManager()
        assert mgr.min_workers == 2
        assert mgr.max_workers == 8
        assert mgr.target_cpu_percent == 70.0
        assert mgr.target_memory_percent == 80.0
        assert mgr.current_workers == 2
        assert mgr.executor._max_workers == 2
        assert mgr.metrics_history == []
        assert mgr.scaling_events == []

    def test_constructor_custom_values(self):
        mgr = AutoScalingManager(min_workers=1, max_workers=4, target_cpu_percent=50.0, target_memory_percent=90.0)
        assert mgr.min_workers == 1
        assert mgr.max_workers == 4
        assert mgr.target_cpu_percent == 50.0
        assert mgr.target_memory_percent == 90.0

    def test_constructor_rejects_min_workers_below_1(self):
        with pytest.raises(ValueError, match="min_workers must be >= 1"):
            AutoScalingManager(min_workers=0)

    def test_constructor_rejects_max_workers_below_min(self):
        with pytest.raises(ValueError, match="max_workers.*>=.*min_workers"):
            AutoScalingManager(min_workers=5, max_workers=3)

    def test_constructor_rejects_invalid_cpu_target(self):
        with pytest.raises(ValueError, match="target_cpu_percent"):
            AutoScalingManager(target_cpu_percent=0)
        with pytest.raises(ValueError, match="target_cpu_percent"):
            AutoScalingManager(target_cpu_percent=101)

    def test_constructor_rejects_invalid_memory_target(self):
        with pytest.raises(ValueError, match="target_memory_percent"):
            AutoScalingManager(target_memory_percent=0)
        with pytest.raises(ValueError, match="target_memory_percent"):
            AutoScalingManager(target_memory_percent=101)

    @patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", False)
    def test_get_system_metrics_fallback_when_psutil_unavailable(self):
        mgr = AutoScalingManager()
        metrics = mgr.get_system_metrics()
        assert metrics["cpu_percent"] == 0.0
        assert metrics["memory_percent"] == 0.0
        assert metrics["memory_available_gb"] == 0.0
        assert "timestamp" in metrics

    @patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", True)
    @patch("app.pipeline.agents.autoscaling.psutil")
    def test_get_system_metrics_with_psutil(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 45.0
        cpu_mem = MagicMock()
        cpu_mem.percent = 60.0
        cpu_mem.available = 4 * 1024 ** 3
        mock_psutil.virtual_memory.return_value = cpu_mem

        mgr = AutoScalingManager()
        metrics = mgr.get_system_metrics()
        assert metrics["cpu_percent"] == 45.0
        assert metrics["memory_percent"] == 60.0
        assert metrics["memory_available_gb"] == 4.0

    @patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", True)
    @patch("app.pipeline.agents.autoscaling.psutil")
    def test_get_system_metrics_fallback_on_exception(self, mock_psutil):
        mock_psutil.cpu_percent.side_effect = RuntimeError("cpu fail")
        mgr = AutoScalingManager()
        metrics = mgr.get_system_metrics()
        assert metrics["cpu_percent"] == 0.0
        assert metrics["memory_percent"] == 0.0

    def test_should_scale_up_cpu_above_target(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 4
        assert mgr.should_scale_up({"cpu_percent": 85, "memory_percent": 30}) is True

    def test_should_scale_up_cpu_high_memory_low(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8, target_cpu_percent=70, target_memory_percent=80)
        mgr.current_workers = 4
        assert mgr.should_scale_up({"cpu_percent": 55, "memory_percent": 30}) is True

    def test_should_scale_up_false_at_max_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=4)
        mgr.current_workers = 4
        assert mgr.should_scale_up({"cpu_percent": 90, "memory_percent": 30}) is False

    def test_should_scale_up_false_when_cpu_low(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 2
        assert mgr.should_scale_up({"cpu_percent": 30, "memory_percent": 30}) is False

    def test_should_scale_up_returns_false_on_exception(self):
        mgr = AutoScalingManager()
        result = mgr.should_scale_up(None)  # type: ignore
        assert result is False

    def test_should_scale_down_cpu_low(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 6
        assert mgr.should_scale_down({"cpu_percent": 20, "memory_percent": 30}) is True

    def test_should_scale_down_memory_high(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8, target_memory_percent=80)
        mgr.current_workers = 4
        assert mgr.should_scale_down({"cpu_percent": 50, "memory_percent": 90}) is True

    def test_should_scale_down_false_at_min_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 2
        assert mgr.should_scale_down({"cpu_percent": 20, "memory_percent": 90}) is False

    def test_should_scale_down_false_when_cpu_normal_and_memory_ok(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 4
        assert mgr.should_scale_down({"cpu_percent": 50, "memory_percent": 50}) is False

    def test_should_scale_down_returns_false_on_exception(self):
        mgr = AutoScalingManager()
        result = mgr.should_scale_down(None)  # type: ignore
        assert result is False

    def test_scale_up_increases_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 2
        mgr.scale_up()
        assert mgr.current_workers == 3
        assert len(mgr.scaling_events) == 1
        assert mgr.scaling_events[0]["type"] == "scale_up"
        assert mgr.scaling_events[0]["from"] == 2
        assert mgr.scaling_events[0]["to"] == 3

    def test_scale_up_at_max_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=4)
        mgr.current_workers = 4
        mgr.scale_up()
        assert mgr.current_workers == 4
        assert mgr.scaling_events == []

    def test_scale_down_decreases_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 5
        mgr.scale_down()
        assert mgr.current_workers == 4
        assert len(mgr.scaling_events) == 1
        assert mgr.scaling_events[0]["type"] == "scale_down"

    def test_scale_down_at_min_workers(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 2
        mgr.scale_down()
        assert mgr.current_workers == 2
        assert mgr.scaling_events == []

    def test_scale_down_waits_for_executor(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 4
        mgr.scale_down()
        assert mgr.current_workers == 3

    def test_scale_up_survives_exception(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.executor = None  # type: ignore
        mgr.scale_up()  # Should not raise

    def test_scale_down_survives_exception(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.executor = None  # type: ignore
        mgr.scale_down()  # Should not raise

    def test_auto_scale_scales_up(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 90, "memory_percent": 30}):
            mgr.auto_scale()
        assert mgr.current_workers == 3

    def test_auto_scale_scales_down(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 5
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 20, "memory_percent": 30}):
            mgr.auto_scale()
        assert mgr.current_workers == 4

    def test_auto_scale_no_action(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.current_workers = 4
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 50, "memory_percent": 50}):
            mgr.auto_scale()
        assert mgr.current_workers == 4

    def test_auto_scale_trims_history(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 50, "memory_percent": 50}):
            for _ in range(105):
                mgr.auto_scale()
        assert len(mgr.metrics_history) <= 100

    def test_auto_scale_survives_get_system_metrics_exception(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        with patch.object(mgr, "get_system_metrics", side_effect=RuntimeError("fail")):
            mgr.auto_scale()  # Should not raise

    def test_get_executor_triggers_auto_scale(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        with patch.object(mgr, "auto_scale") as mock_auto_scale:
            executor = mgr.get_executor()
            mock_auto_scale.assert_called_once()
            assert executor is mgr.executor

    def test_get_statistics_empty(self):
        mgr = AutoScalingManager()
        stats = mgr.get_statistics()
        assert stats["current_workers"] == 2
        assert stats["total_scaling_events"] == 0
        assert stats["avg_cpu_percent"] == 0.0
        assert stats["avg_memory_percent"] == 0.0

    def test_get_statistics_with_data(self):
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        mgr.scale_up()
        mgr.scale_up()
        with patch.object(mgr, "metrics_history", [
            {"cpu_percent": 50.0, "memory_percent": 60.0},
            {"cpu_percent": 70.0, "memory_percent": 80.0},
        ]):
            stats = mgr.get_statistics()
        assert stats["current_workers"] == 4
        assert stats["total_scaling_events"] == 2
        assert stats["scale_up_count"] == 2
        assert stats["scale_down_count"] == 0
        assert stats["avg_cpu_percent"] == 60.0
        assert stats["avg_memory_percent"] == 70.0

    def test_get_statistics_survives_exception(self):
        mgr = AutoScalingManager()
        mgr.metrics_history = None  # type: ignore
        stats = mgr.get_statistics()
        assert stats["current_workers"] == 2

    def test_shutdown(self):
        mgr = AutoScalingManager()
        mgr.shutdown()
        assert True  # No error

    def test_shutdown_survives_exception(self):
        mgr = AutoScalingManager()
        mgr.executor = None  # type: ignore
        mgr.shutdown()  # Should not raise


# =============================================================================
# RealTimeAdaptiveAgent
# =============================================================================

class TestRealTimeAdaptiveAgent:
    """Tests for RealTimeAdaptiveAgent."""

    def test_constructor_defaults(self):
        agent = RealTimeAdaptiveAgent()
        assert agent.base_timeout == 60.0
        assert agent.adaptation_callback is None
        assert agent.params["timeout"] == 60.0
        assert agent.params["retry_enabled"] is True
        assert agent.params["tool_priority"] == []
        assert agent.params["aggressive_mode"] is False
        assert agent.current_metrics["start_time"] is None

    def test_constructor_clamps_base_timeout(self):
        agent = RealTimeAdaptiveAgent(base_timeout=5.0)
        assert agent.base_timeout == RT_MIN_TIMEOUT

        agent2 = RealTimeAdaptiveAgent(base_timeout=2000.0)
        assert agent2.base_timeout == RT_MAX_TIMEOUT

    def test_constructor_rejects_non_positive_timeout(self):
        with pytest.raises(ValueError, match="base_timeout must be positive"):
            RealTimeAdaptiveAgent(base_timeout=0)
        with pytest.raises(ValueError, match="base_timeout must be positive"):
            RealTimeAdaptiveAgent(base_timeout=-10)

    def test_constructor_with_callback(self):
        callback = MagicMock()
        agent = RealTimeAdaptiveAgent(base_timeout=30.0, adaptation_callback=callback)
        assert agent.base_timeout == 30.0
        assert agent.adaptation_callback is callback

    def test_start_processing_sets_metrics(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_123")
        assert agent.current_metrics["document_id"] == "doc_123"
        assert agent.current_metrics["start_time"] is not None
        assert agent.current_metrics["elapsed_time"] == 0.0
        assert agent.current_metrics["tools_executed"] == []
        assert agent.current_metrics["errors_encountered"] == []
        assert agent.current_metrics["current_strategy"] == "default"

    def test_start_processing_resets_params(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.params["retry_enabled"] = False
        agent.params["aggressive_mode"] = True
        agent.start_processing("doc_2")
        assert agent.params["retry_enabled"] is True
        assert agent.params["aggressive_mode"] is False
        assert agent.params["timeout"] == agent.base_timeout

    def test_start_processing_with_empty_id_logs_warning(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("")
        assert agent.current_metrics["document_id"] == ""

    def test_record_tool_execution_skips_empty_name(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("", 1.0, True)
        assert agent.current_metrics["tools_executed"] == []

    def test_record_tool_execution_success(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("tool_a", 2.5, True)
        assert len(agent.current_metrics["tools_executed"]) == 1
        entry = agent.current_metrics["tools_executed"][0]
        assert entry["tool"] == "tool_a"
        assert entry["duration"] == 2.5
        assert entry["success"] is True
        assert "timestamp" in entry
        assert agent.current_metrics["errors_encountered"] == []

    def test_record_tool_execution_failure(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.record_tool_execution("tool_a", 1.0, False)
        assert len(agent.current_metrics["errors_encountered"]) == 1
        assert agent.current_metrics["errors_encountered"][0]["tool"] == "tool_a"

    def test_record_tool_execution_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        # Break current_metrics to cause an exception
        agent.current_metrics = None  # type: ignore
        agent.record_tool_execution("tool_a", 1.0, True)  # Should not raise

    def test_recommend_next_tool_returns_none_for_empty_list(self):
        agent = RealTimeAdaptiveAgent()
        assert agent.recommend_next_tool([]) is None

    def test_recommend_next_tool_returns_first_available(self):
        agent = RealTimeAdaptiveAgent()
        assert agent.recommend_next_tool(["a", "b", "c"]) == "a"

    def test_recommend_next_tool_follows_priority(self):
        agent = RealTimeAdaptiveAgent()
        agent.params["tool_priority"] = ["c", "a"]
        assert agent.recommend_next_tool(["a", "b", "c"]) == "c"

    def test_recommend_next_tool_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.params = None  # type: ignore
        result = agent.recommend_next_tool(["a"])
        assert result == "a"

    def test_should_continue_returns_false_on_timeout(self):
        agent = RealTimeAdaptiveAgent(base_timeout=10)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 11.0
        assert agent.should_continue() is False

    def test_should_continue_returns_false_on_too_many_errors(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        for i in range(_MAX_ERRORS_BEFORE_STOP + 1):
            agent.current_metrics["errors_encountered"].append({"tool": f"t{i}"})
        assert agent.should_continue() is False

    def test_should_continue_returns_true_when_ok(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        assert agent.should_continue() is True

    def test_should_continue_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None  # type: ignore
        assert agent.should_continue() is False

    def test_get_current_params(self):
        agent = RealTimeAdaptiveAgent()
        agent.params["retry_enabled"] = False
        params = agent.get_current_params()
        assert params["retry_enabled"] is False
        params["retry_enabled"] = True
        assert agent.params["retry_enabled"] is False  # should not mutate

    def test_get_current_params_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.params = None  # type: ignore
        result = agent.get_current_params()
        assert result == {}

    def test_get_metrics(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        metrics = agent.get_metrics()
        assert metrics["document_id"] == "doc_1"

    def test_get_metrics_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None  # type: ignore
        result = agent.get_metrics()
        assert result == {}

    def test_adapt_realtime_timeout_extended(self):
        agent = RealTimeAdaptiveAgent(base_timeout=60)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 50.0  # > 60 * 0.7
        assert agent.params["aggressive_mode"] is False
        assert agent.params["timeout"] == 60.0
        agent._adapt_realtime()
        assert agent.params["aggressive_mode"] is True
        assert agent.params["timeout"] == 90.0  # 60 * 1.5

    def test_adapt_realtime_timeout_clamped(self):
        agent = RealTimeAdaptiveAgent(base_timeout=RT_MAX_TIMEOUT)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = RT_MAX_TIMEOUT - 1
        agent._adapt_realtime()
        assert agent.params["timeout"] <= RT_MAX_TIMEOUT

    def test_adapt_realtime_strategy_fallback_on_errors(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["errors_encountered"] = [
            {"tool": "t1"}, {"tool": "t2"}
        ]
        agent._adapt_realtime()
        assert agent.current_metrics["current_strategy"] == "fallback"
        assert agent.params["retry_enabled"] is False

    def test_adapt_realtime_tool_priority_set(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["tools_executed"] = [
            {"tool": "tool_x", "success": True},
            {"tool": "tool_y", "success": False},
        ]
        agent._adapt_realtime()
        assert agent.params["tool_priority"] == ["tool_x"]

    def test_adapt_realtime_no_duplicate_fallback_switch(self):
        agent = RealTimeAdaptiveAgent()
        agent.start_processing("doc_1")
        agent.current_metrics["current_strategy"] = "fallback"
        agent.current_metrics["errors_encountered"] = [
            {"tool": "t1"}, {"tool": "t2"}
        ]
        agent._adapt_realtime()
        # Should not switch again
        assert agent.current_metrics["current_strategy"] == "fallback"

    def test_adapt_realtime_survives_exception(self):
        agent = RealTimeAdaptiveAgent()
        agent.current_metrics = None  # type: ignore
        agent._adapt_realtime()  # Should not raise

    def test_notify_adaptation_calls_callback(self):
        callback = MagicMock()
        agent = RealTimeAdaptiveAgent(adaptation_callback=callback)
        agent._notify_adaptation("test_event", {"key": "value"})
        callback.assert_called_once_with("test_event", {"key": "value"})

    def test_notify_adaptation_survives_callback_error(self):
        callback = MagicMock(side_effect=RuntimeError("callback fail"))
        agent = RealTimeAdaptiveAgent(adaptation_callback=callback)
        agent._notify_adaptation("test_event", {})  # Should not raise

    def test_notify_adaptation_no_callback(self):
        agent = RealTimeAdaptiveAgent()
        agent._notify_adaptation("test_event", {})  # Should not raise

    def test_adapt_realtime_triggers_callback_on_timeout(self):
        callback = MagicMock()
        agent = RealTimeAdaptiveAgent(base_timeout=60, adaptation_callback=callback)
        agent.start_processing("doc_1")
        agent.current_metrics["elapsed_time"] = 50.0
        agent._adapt_realtime()
        callback.assert_called()
        call_args = callback.call_args[0]
        assert call_args[0] == "timeout_extended"

    def test_adapt_realtime_triggers_callback_on_errors(self):
        callback = MagicMock()
        agent = RealTimeAdaptiveAgent(adaptation_callback=callback)
        agent.start_processing("doc_1")
        agent.current_metrics["errors_encountered"] = [{"tool": "t1"}, {"tool": "t2"}]
        agent._adapt_realtime()
        callback.assert_any_call(
            "strategy_changed",
            {"new_strategy": "fallback", "reason": "multiple_errors"},
        )

    def test_adapt_realtime_triggers_callback_on_tool_priority(self):
        callback = MagicMock()
        agent = RealTimeAdaptiveAgent(adaptation_callback=callback)
        agent.start_processing("doc_1")
        agent.current_metrics["tools_executed"] = [
            {"tool": "tool_x", "success": True},
        ]
        agent._adapt_realtime()
        callback.assert_any_call(
            "tool_priority_set",
            {"priority": ["tool_x"]},
        )


# =============================================================================
# StreamingAgentCallback
# =============================================================================

class _MockAgentAction:
    """Minimal mock for AgentAction."""
    def __init__(self, tool: str = "test_tool", tool_input: str = "", log: str = ""):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log


class _MockAgentFinish:
    """Minimal mock for AgentFinish."""
    def __init__(self, return_values: dict[str, Any] | None = None):
        self.return_values = return_values or {"output": "done"}


class _MockLLMResult:
    """Minimal mock for LLMResult."""
    def __init__(self, generations_count: int = 1):
        self.generations = [MagicMock() for _ in range(generations_count)]


class TestStreamingAgentCallback:
    """Tests for StreamingAgentCallback."""

    def test_constructor_with_callback(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        assert handler.callback_fn is cb
        assert handler.events == []

    def test_constructor_without_callback_uses_default(self):
        handler = StreamingAgentCallback()
        assert callable(handler.callback_fn)
        handler.callback_fn("test", {"msg": "hello"})
        assert len(handler.events) == 1
        assert handler.events[0]["type"] == "test"

    def test_default_callback_appends_to_events(self):
        handler = StreamingAgentCallback()
        handler._default_callback("evt_type", {"data": 1})
        assert len(handler.events) == 1
        assert handler.events[0]["type"] == "evt_type"
        assert handler.events[0]["data"] == {"data": 1}

    def test_on_llm_start(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_llm_start({"model": "test"}, ["prompt1", "prompt2"])
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "llm_start"
        assert data["prompt_count"] == 2

    def test_on_llm_end(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        response = _MockLLMResult(generations_count=3)
        handler.on_llm_end(response)
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "llm_end"
        assert data["generations"] == 3

    def test_on_llm_error(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_llm_error(ValueError("test error"))
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "llm_error"
        assert "test error" in data["error"]

    def test_on_tool_start(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_start({"name": "search_tool"}, "some input text")
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "tool_start"
        assert data["tool"] == "search_tool"
        assert data["input"] == "some input text"

    def test_on_tool_start_unknown_name(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_start({}, "input")
        cb.assert_called_once()
        data = cb.call_args[0][1]
        assert data["tool"] == "unknown"

    def test_on_tool_end(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_end("tool output here")
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "tool_end"
        assert "tool" in data["output_preview"]

    def test_on_tool_error(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_tool_error(RuntimeError("tool crash"))
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "tool_error"
        assert "tool crash" in data["error"]

    def test_on_agent_action(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        action = _MockAgentAction(tool="extract", tool_input="refs", log="log text")
        handler.on_agent_action(action)
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "agent_action"
        assert data["tool"] == "extract"
        assert data["tool_input"] == "refs"

    def test_on_agent_action_empty_log(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        action = _MockAgentAction(tool="tool_a", tool_input="in", log="")
        handler.on_agent_action(action)
        data = cb.call_args[0][1]
        assert data["log"] == ""

    def test_on_agent_finish(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        finish = _MockAgentFinish(return_values={"output": "completed"})
        handler.on_agent_finish(finish)
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "agent_finish"
        assert "completed" in data["output"]

    def test_on_chain_start(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_start({"name": "chain_1"}, {"input": "data"})
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "chain_start"
        assert data["chain"] == "chain_1"

    def test_on_chain_start_unknown_name(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_start({}, {"input": "data"})
        data = cb.call_args[0][1]
        assert data["chain"] == "unknown"

    def test_on_chain_end(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_end({"result": "ok"})
        cb.assert_called_once()
        event_type = cb.call_args[0][0]
        assert event_type == "chain_end"

    def test_on_chain_error(self):
        cb = MagicMock()
        handler = StreamingAgentCallback(callback_fn=cb)
        handler.on_chain_error(RuntimeError("chain fail"))
        cb.assert_called_once()
        event_type, data = cb.call_args[0]
        assert event_type == "chain_error"
        assert "chain fail" in data["error"]

    def test_get_events_returns_events_list(self):
        handler = StreamingAgentCallback()
        assert handler.get_events() == []
        handler.callback_fn("a", {})
        assert len(handler.get_events()) == 1

    def test_clear_events(self):
        handler = StreamingAgentCallback()
        handler.callback_fn("a", {})
        assert len(handler.events) == 1
        handler.clear_events()
        assert handler.events == []

    def test_callbacks_with_custom_function(self):
        received: list = []
        def my_cb(evt: str, data: dict) -> None:
            received.append((evt, data))

        handler = StreamingAgentCallback(callback_fn=my_cb)
        handler.on_llm_start({}, ["hi"])
        handler.on_tool_end("output")
        assert len(received) == 2
        assert received[0][0] == "llm_start"
        assert received[1][0] == "tool_end"
