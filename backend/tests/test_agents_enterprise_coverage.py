# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest


# ─── AdaptiveStrategy ──────────────────────────────────────────────────────────

_adaptive_strategy_cls = None

def _get_adaptive():
    global _adaptive_strategy_cls
    if _adaptive_strategy_cls is not None:
        return _adaptive_strategy_cls
    try:
        from app.pipeline.agents.adaptive import AdaptiveStrategy as _cls
        _adaptive_strategy_cls = _cls
        return _cls
    except TypeError:
        pytest.skip("sklearn/scipy version conflict with Python 3.14")


class TestAdaptiveStrategy:
    def test_init_with_tracker(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        assert ap.tracker is tracker
        assert ap.config["max_retries"] == 3

    def test_init_raises_on_none_tracker(self):
        AdaptiveStrategy = _get_adaptive()
        with pytest.raises(ValueError, match="tracker must not be None"):
            AdaptiveStrategy(None)

    def test_init_with_ml_detector(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        assert ap.ml_detector is ml

    def test_default_config_values(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        cfg = ap._default_config()
        assert cfg["max_retries"] == 3
        assert cfg["timeout_seconds"] == 60
        assert cfg["fallback_threshold"] == 0.5
        assert cfg["enable_caching"] is True
        assert len(cfg["tool_priority"]) == 5

    def test_clamp_within_bounds(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        assert ap._clamp(5.0, 1.0, 10.0) == 5.0

    def test_clamp_below_min(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        assert ap._clamp(0.0, 1.0, 10.0) == 1.0

    def test_clamp_above_max(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        assert ap._clamp(15.0, 1.0, 10.0) == 10.0

    def test_adapt_increases_retries_on_low_success(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.5, "avg_duration": 60, "fallback_rate": 0.0}}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["max_retries"] > 3

    def test_adapt_decreases_retries_on_high_success(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.98, "avg_duration": 60, "fallback_rate": 0.0}}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["max_retries"] == 2

    def test_adapt_increases_fallback_on_high_fallback_rate(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.9, "avg_duration": 60, "fallback_rate": 0.5}}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["fallback_threshold"] > 0.5

    def test_adapt_decreases_fallback_on_low_fallback_rate(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.9, "avg_duration": 60, "fallback_rate": 0.0}}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["fallback_threshold"] < 0.5

    def test_adapt_handles_tracker_exception(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.side_effect = RuntimeError("tracker fail")
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["max_retries"] == 3

    def test_adapt_empty_summary_returns_default(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["max_retries"] == 3

    def test_adapt_uses_ml_patterns_when_available(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.9, "avg_duration": 60, "fallback_rate": 0.0}}
        ml = MagicMock()
        ml.patterns = [{"success_rate": 0.9, "cluster_id": 1, "sample_count": 10, "avg_duration": 30, "common_tools": ["tool_a"]}]
        ml.get_pattern_summary.return_value = {"patterns": [{"success_rate": 0.9, "common_tools": ["tool_a"]}]}
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        result = ap.adapt()
        assert "tool_a" in result["tool_priority"]

    def test_adapt_ml_patterns_empty(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.9, "avg_duration": 60, "fallback_rate": 0.0}}
        ml = MagicMock()
        ml.patterns = [{"success_rate": 0.9, "cluster_id": 1}]
        ml.get_pattern_summary.return_value = {"patterns": []}
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        result = ap.adapt()
        assert result["max_retries"] == 3

    def test_adapt_adjusts_timeout_based_on_duration(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"success_rate": 0.9, "avg_duration": 200, "fallback_rate": 0.0}}
        ap = AdaptiveStrategy(tracker)
        result = ap.adapt()
        assert result["timeout_seconds"] >= 300

    def test_get_config_returns_copy(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        cfg = ap.get_config()
        cfg["max_retries"] = 99
        assert ap.config["max_retries"] == 3

    def test_recommend_strategy_default_with_non_dict(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ap = AdaptiveStrategy(tracker)
        result = ap.recommend_strategy(None)
        assert result["strategy"] == "default"

    def test_recommend_strategy_ml_guided(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.return_value = {"avg_duration": 45, "common_tools": ["x"], "success_rate": 0.8}
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        result = ap.recommend_strategy({"title": "test"})
        assert result["strategy"] == "ml_guided"

    def test_recommend_strategy_ml_returns_none(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.return_value = None
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        result = ap.recommend_strategy({"title": "test"})
        assert result["strategy"] == "default"

    def test_recommend_strategy_ml_exception(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ml.predict_pattern.side_effect = RuntimeError("predict failed")
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        result = ap.recommend_strategy({"title": "test"})
        assert result["strategy"] == "default"

    def test_adapt_from_ml_patterns_no_patterns_returns_early(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"patterns": []}
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        ap._adapt_from_ml_patterns()
        assert ap.config["tool_priority"] == ap._default_config()["tool_priority"]

    def test_adapt_from_ml_patterns_exception_handled(self):
        AdaptiveStrategy = _get_adaptive()
        tracker = MagicMock()
        ml = MagicMock()
        ml.get_pattern_summary.side_effect = RuntimeError("fail")
        ap = AdaptiveStrategy(tracker, ml_detector=ml)
        ap._adapt_from_ml_patterns()


# ─── ComparisonDashboard ───────────────────────────────────────────────────────

class TestComparisonDashboard:
    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"count": 5}, "legacy": {"count": 3}, "total_runs": 8, "last_updated": "2026-01-01"}
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}}
        d = ComparisonDashboard(tracker)
        assert d.generate_html(str(tmp_path / "dash.html")) == str(tmp_path / "dash.html")

    def test_generate_html_empty_summary(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard
        tracker = MagicMock()
        tracker.get_summary.return_value = {}
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}}
        d = ComparisonDashboard(tracker)
        result = d.generate_html(str(tmp_path / "dash2.html"))
        assert result == str(tmp_path / "dash2.html")

    def test_generate_json_report(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard
        tracker = MagicMock()
        tracker.get_comparison.return_value = {"agent_vs_legacy": {}}
        d = ComparisonDashboard(tracker)
        assert d.generate_json_report(str(tmp_path / "report.json")) == str(tmp_path / "report.json")

    def test_build_html_contains_title(self):
        from app.pipeline.agents.dashboard import ComparisonDashboard
        tracker = MagicMock()
        tracker.get_summary.return_value = {"agent": {"count": 1}, "legacy": {"count": 1}, "total_runs": 2, "last_updated": "now"}
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}}
        d = ComparisonDashboard(tracker)
        html = d._build_html({"agent": {}, "legacy": {}, "total_runs": 0}, {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}})
        assert "Performance Dashboard" in html


# ─── PerformanceTracker ────────────────────────────────────────────────────────

class TestPerformanceTracker:
    def test_init(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics"))
        assert t.current_run is None

    def test_start_tracking(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics2"))
        run = t.start_tracking("doc1", "agent")
        assert run["document_id"] == "doc1"
        assert run["orchestrator_type"] == "agent"

    def test_record_tool_use(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics3"))
        t.start_tracking("doc1", "agent")
        t.record_tool_use("tool1")
        assert "tool1" in t.current_run["tools_used"]

    def test_record_tool_use_no_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics4"))
        t.record_tool_use("tool1")

    def test_record_retry(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics5"))
        t.start_tracking("doc1", "agent")
        t.record_retry()
        assert t.current_run["retry_count"] == 1

    def test_end_tracking_no_run(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics6"))
        with pytest.raises(ValueError, match="No active tracking run"):
            t.end_tracking(success=True)

    def test_end_tracking_success(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics7"))
        t.start_tracking("doc1", "agent")
        m = t.end_tracking(success=True)
        assert m.document_id == "doc1"
        assert m.success is True

    def test_end_tracking_with_document(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        doc = MagicMock()
        doc.metadata.title = "Test Title"
        doc.blocks = [MagicMock()]
        doc.references = [MagicMock()]
        doc.figures = [MagicMock()]
        doc.validation_errors = []
        doc.validation_warnings = ["warn"]
        t = PerformanceTracker(str(tmp_path / ".metrics8"))
        t.start_tracking("doc1", "agent")
        m = t.end_tracking(success=True, document=doc)
        assert m.metadata_extracted is True

    def test_end_tracking_fallback(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics9"))
        t.start_tracking("doc1", "agent")
        m = t.end_tracking(success=False, fallback_triggered=True)
        assert m.fallback_triggered is True

    def test_get_summary_empty(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics10"))
        assert t.get_summary() == {}

    def test_get_comparison_insufficient_data(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics11"))
        comp = t.get_comparison()
        assert "error" in comp

    def test_load_all_metrics_empty(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics12"))
        assert t.load_all_metrics() == []

    def test_calculate_stats_empty(self, tmp_path):
        from app.pipeline.agents.metrics import PerformanceTracker
        t = PerformanceTracker(str(tmp_path / ".metrics13"))
        stats = t._calculate_stats([])
        assert stats["count"] == 0


# ─── AgentMemory ───────────────────────────────────────────────────────────────

class TestAgentMemory:
    def test_init(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem"))
        assert m.patterns == {}

    def test_remember_pattern_new(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem2"))
        m.remember_pattern("test_type", {"document_type": "paper"}, True)
        assert "test_type" in m.patterns

    def test_remember_pattern_similar_dedup(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem3"))
        m.remember_pattern("test_type", {"document_type": "paper"}, True)
        m.remember_pattern("test_type", {"document_type": "paper"}, True)
        assert len(m.patterns["test_type"]["successful"]) == 1

    def test_remember_pattern_failed(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem4"))
        m.remember_pattern("test_type", {"document_type": "paper"}, False)
        assert len(m.patterns["test_type"]["failed"]) == 1

    def test_remember_error_new(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem5"))
        m.remember_error("err_type", "err_msg", "solution")
        assert len(m.errors) == 1

    def test_remember_error_duplicate(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem6"))
        m.remember_error("err_type", "err_msg")
        m.remember_error("err_type", "err_msg")
        assert m.errors[0]["occurrences"] == 2

    def test_remember_error_with_solution(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem7"))
        m.remember_error("err_type", "err_msg", "fix")
        assert m.errors[0]["solution"] == "fix"

    def test_record_metric(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem8"))
        m.record_metric("speed", 42.0)
        assert m.metrics["speed"]["count"] == 1

    def test_record_metric_multiple(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem9"))
        m.record_metric("speed", 10.0)
        m.record_metric("speed", 20.0)
        assert m.metrics["speed"]["average"] == 15.0

    def test_get_best_pattern_no_type(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem10"))
        assert m.get_best_pattern("nonexistent", {}) is None

    def test_get_best_pattern_no_successful(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem11"))
        m.patterns["t"] = {"successful": [], "failed": []}
        assert m.get_best_pattern("t", {}) is None

    def test_get_best_pattern_finds_match(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem12"))
        m.remember_pattern("t", {"document_type": "paper"}, True)
        result = m.get_best_pattern("t", {"document_type": "paper"})
        assert result is not None

    def test_get_best_pattern_returns_most_common(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem13"))
        m.patterns["t"] = {"successful": [{"context": {"document_type": "other"}, "count": 5}], "failed": []}
        result = m.get_best_pattern("t", {"document_type": "paper"})
        assert result["count"] == 5

    def test_get_error_solution_found(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem14"))
        m.remember_error("e_type", "e_message", "solve")
        assert m.get_error_solution("e_type", "e_message") == "solve"

    def test_get_error_solution_not_found(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem15"))
        assert m.get_error_solution("none", "none") is None

    def test_get_metric_summary(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem16"))
        m.record_metric("m1", 1.0)
        s = m.get_metric_summary("m1")
        assert s["count"] == 1

    def test_get_metric_summary_missing(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem17"))
        assert m.get_metric_summary("none") is None

    def test_remember_correction(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem18"))
        m.remember_correction("doc1", "title", "old", "new")
        assert len(m.corrections) == 1

    def test_get_memory_summary(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem19"))
        s = m.get_memory_summary()
        assert "patterns" in s
        assert "errors" in s

    def test_format_memory_summary(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem20"))
        result = m.format_memory_summary()
        assert "Patterns:" in result

    def test_load_json_file_missing(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        m = AgentMemory(str(tmp_path / ".mem21"))
        assert m._load_json(m.memory_dir / "nonexistent.json", []) == []

    def test_load_json_corrupt_file(self, tmp_path):
        from app.pipeline.agents.memory import AgentMemory
        f = tmp_path / ".mem22" / "corrupt.json"
        f.parent.mkdir(exist_ok=True)
        f.write_text("{invalid json")
        m = AgentMemory(str(tmp_path / ".mem22"))
        val = m._load_json(f, "default_val")
        assert val == "default_val"


# ─── MLPatternDetector ─────────────────────────────────────────────────────────

class TestMLPatternDetector:
    def test_init(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=3)
        assert d.min_samples == 3

    def test_extract_features(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        metrics = {"duration_seconds": 30, "references_count": 20, "figures_count": 5,
                   "validation_errors": 0, "validation_warnings": 1, "retry_count": 0,
                   "fallback_triggered": False, "tools_used": ["a", "b"]}
        features = d.extract_features(metrics)
        assert features.shape == (8,)

    def test_fit_insufficient_data(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=10)
        assert d.fit([]) is False

    def test_fit_success(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=2)
        data = [
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 30, "references_count": 15, "figures_count": 3,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": True, "tools_used": ["a", "b"], "success": False},
            {"duration_seconds": 30, "references_count": 15, "figures_count": 3,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": True, "tools_used": ["a", "b"], "success": False},
        ]
        assert d.fit(data) is True
        assert len(d.patterns) > 0

    def test_predict_pattern_no_patterns(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        assert d.predict_pattern({}) is None

    def test_predict_pattern_after_fit(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=2)
        data = [
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
        ]
        d.fit(data)
        pred = d.predict_pattern({"duration_seconds": 15, "references_count": 7, "figures_count": 1,
                                   "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
                                   "fallback_triggered": False, "tools_used": ["a"]})
        assert pred is not None

    def test_detect_anomaly_no_fit(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        is_anom, score = d.detect_anomaly({"duration_seconds": 100, "references_count": 0, "figures_count": 0,
                                            "validation_errors": 0, "validation_warnings": 0,
                                            "retry_count": 0, "fallback_triggered": False, "tools_used": []})
        assert isinstance(is_anom, bool)

    def test_get_pattern_summary_default(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        s = d.get_pattern_summary()
        assert s["pattern_count"] == 0
        assert s["trained"] is False

    def test_get_pattern_summary_after_fit(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=2)
        data = [
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
        ]
        d.fit(data)
        s = d.get_pattern_summary()
        assert s["trained"] is True

    def test_save_and_load(self, tmp_path):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector(min_samples=2)
        data = [
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
            {"duration_seconds": 10, "references_count": 5, "figures_count": 1,
             "validation_errors": 0, "validation_warnings": 0, "retry_count": 0,
             "fallback_triggered": False, "tools_used": ["a"], "success": True},
        ]
        d.fit(data)
        f = str(tmp_path / "model.pkl")
        d.save(f)
        d2 = MLPatternDetector()
        d2.load(f)
        assert len(d2.patterns) > 0

    def test_most_common_tools(self):
        from app.pipeline.agents.ml_patterns import MLPatternDetector
        d = MLPatternDetector()
        metrics_list = [
            {"tools_used": ["a", "b", "c"]},
            {"tools_used": ["a", "b"]},
            {"tools_used": ["a"]},
        ]
        tools = d._most_common_tools(metrics_list)
        assert "a" in tools


# ─── AutoScalingManager ────────────────────────────────────────────────────────

class TestAutoScalingManager:
    def test_init_default(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        assert m.min_workers == 2
        assert m.max_workers == 8

    def test_init_invalid_min_workers(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        with pytest.raises(ValueError, match="min_workers must be >= 1"):
            AutoScalingManager(min_workers=0)

    def test_init_max_less_than_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        with pytest.raises(ValueError, match="max_workers"):
            AutoScalingManager(min_workers=5, max_workers=3)

    def test_init_invalid_cpu_target(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        with pytest.raises(ValueError, match="target_cpu_percent"):
            AutoScalingManager(target_cpu_percent=0.0)

    def test_init_invalid_memory_target(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        with pytest.raises(ValueError, match="target_memory_percent"):
            AutoScalingManager(target_memory_percent=150.0)

    def test_get_system_metrics_psutil_unavailable(self):
        with patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", False):
            from app.pipeline.agents.autoscaling import AutoScalingManager
            m = AutoScalingManager()
            metrics = m.get_system_metrics()
            assert metrics["cpu_percent"] == 0.0

    def test_should_scale_up_true(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        assert m.should_scale_up({"cpu_percent": 85.0, "memory_percent": 50.0}) is True

    def test_should_scale_up_false_at_max(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(max_workers=2, min_workers=2)
        m.current_workers = 2
        assert m.should_scale_up({"cpu_percent": 85.0, "memory_percent": 50.0}) is False

    def test_should_scale_up_moderate_cpu_low_mem(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        assert m.should_scale_up({"cpu_percent": 60.0, "memory_percent": 30.0}) is True

    def test_should_scale_down_cpu_low(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=1, max_workers=4)
        m.current_workers = 3
        assert m.should_scale_down({"cpu_percent": 20.0, "memory_percent": 50.0}) is True

    def test_should_scale_down_mem_high(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=1, max_workers=4)
        m.current_workers = 3
        assert m.should_scale_down({"cpu_percent": 50.0, "memory_percent": 90.0}) is True

    def test_should_scale_down_false_at_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=2, max_workers=4)
        m.current_workers = 2
        assert m.should_scale_down({"cpu_percent": 20.0, "memory_percent": 50.0}) is False

    def test_scale_up_increases_workers(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(max_workers=5)
        old = m.current_workers
        m.scale_up()
        assert m.current_workers == old + 1

    def test_scale_up_at_max_no_change(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=4, max_workers=4)
        m.current_workers = 4
        m.scale_up()
        assert m.current_workers == 4

    def test_scale_down_decreases_workers(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=1, max_workers=5)
        m.current_workers = 3
        m.scale_down()
        assert m.current_workers == 2

    def test_scale_down_at_min_no_change(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager(min_workers=2, max_workers=5)
        m.current_workers = 2
        m.scale_down()
        assert m.current_workers == 2

    def test_auto_scale(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        m.auto_scale()
        assert len(m.metrics_history) == 1

    def test_get_executor(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        exec_ = m.get_executor()
        assert exec_ is m.executor

    def test_get_statistics(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        stats = m.get_statistics()
        assert stats["current_workers"] == 2
        assert stats["total_scaling_events"] == 0

    def test_shutdown(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        m = AutoScalingManager()
        m.shutdown()


# ─── DistributedCoordinator ────────────────────────────────────────────────────

class TestDistributedCoordinator:
    def test_init(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        assert dc.max_workers == 4

    def test_init_invalid_workers(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        with pytest.raises(ValueError, match="max_workers must be >= 1"):
            DistributedCoordinator(max_workers=0)

    def test_initialization_creates_specialists(self):
        from app.pipeline.agents.distributed import DistributedCoordinator, AgentRole
        dc = DistributedCoordinator()
        assert AgentRole.METADATA_SPECIALIST in dc.specialists
        assert AgentRole.REFERENCE_SPECIALIST in dc.specialists

    def test_process_document_empty_path(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        result = dc.process_document("")
        assert result["success"] is False

    def test_process_document_success(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        result = dc.process_document("/path/to/doc.pdf")
        assert result["success"] is True
        assert len(result["specialist_results"]) == 4

    def test_get_statistics(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        stats = dc.get_statistics()
        assert "specialists" in stats
        assert stats["total_tasks"] == 0

    def test_process_document_after_one_processing(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        dc.process_document("/path/doc.pdf")
        stats = dc.get_statistics()
        assert stats["total_tasks"] == 4


class TestSpecialistAgent:
    def test_init_invalid_role(self):
        from app.pipeline.agents.distributed import SpecialistAgent
        with pytest.raises(ValueError, match="role must be an AgentRole"):
            SpecialistAgent(role="not_a_role", tools=[])

    def test_init_valid(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, [])
        assert agent.role == AgentRole.METADATA_SPECIALIST

    def test_process_none_task(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, [])
        result = agent.process(None)
        assert "error" in result

    def test_process_metadata(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, [])
        task = AgentTask(task_id="t1", role=AgentRole.METADATA_SPECIALIST, document_path="/p.pdf")
        result = agent.process(task)
        assert result["result"] == "metadata_extracted"

    def test_process_layout(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.LAYOUT_SPECIALIST, [])
        task = AgentTask(task_id="t2", role=AgentRole.LAYOUT_SPECIALIST, document_path="/p.pdf")
        result = agent.process(task)
        assert result["result"] == "layout_analyzed"

    def test_process_validation(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.VALIDATION_SPECIALIST, [])
        task = AgentTask(task_id="t3", role=AgentRole.VALIDATION_SPECIALIST, document_path="/p.pdf")
        result = agent.process(task)
        assert result["result"] == "validation_complete"

    def test_process_references(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.REFERENCE_SPECIALIST, [])
        task = AgentTask(task_id="t4", role=AgentRole.REFERENCE_SPECIALIST, document_path="/p.pdf")
        result = agent.process(task)
        assert result["result"] == "references_extracted"

    def test_process_unknown_role(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.COORDINATOR, [])
        task = AgentTask(task_id="t5", role=AgentRole.COORDINATOR, document_path="/p.pdf")
        result = agent.process(task)
        assert "Unknown role" in result.get("error", "")

    def test_task_count_increments(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, [])
        task = AgentTask(task_id="t1", role=AgentRole.METADATA_SPECIALIST, document_path="/p.pdf")
        agent.process(task)
        assert agent.task_count == 1

    def test_process_exception_handling(self):
        from app.pipeline.agents.distributed import SpecialistAgent, AgentRole, AgentTask
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, [])
        agent._process_metadata = MagicMock(side_effect=RuntimeError("fail"))
        task = AgentTask(task_id="t1", role=AgentRole.METADATA_SPECIALIST, document_path="/p.pdf")
        result = agent.process(task)
        assert "error" in result


# ─── TransformerPatternDetector ────────────────────────────────────────────────

class TestTransformerPatternDetector:
    def test_init_fallback_mode(self):
        with patch("app.pipeline.agents.deep_learning.torch", None):
            from app.pipeline.agents.deep_learning import TransformerPatternDetector
            d = TransformerPatternDetector()
            assert d.tokenizer is None
            assert d.model is None

    def test_encode_document_no_model_returns_zeros(self):
        with patch("app.pipeline.agents.deep_learning.torch", None):
            from app.pipeline.agents.deep_learning import TransformerPatternDetector
            d = TransformerPatternDetector()
            emb = d.encode_document("hello")
            assert emb.shape == (768,)

    def test_encode_document_cache_hit(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        d.embeddings_cache["test"] = np.array([1.0, 2.0])
        result = d.encode_document("test")
        assert result[0] == 1.0

    def test_encode_metadata(self):
        with patch("app.pipeline.agents.deep_learning.torch", None):
            from app.pipeline.agents.deep_learning import TransformerPatternDetector
            d = TransformerPatternDetector()
            metadata = {"title": "Test", "authors": ["A1", "A2"], "abstract": "Test abstract", "venue": "Venue"}
            emb = d.encode_metadata(metadata)
            assert emb.shape == (768,)

    def test_encode_metadata_partial(self):
        with patch("app.pipeline.agents.deep_learning.torch", None):
            from app.pipeline.agents.deep_learning import TransformerPatternDetector
            d = TransformerPatternDetector()
            emb = d.encode_metadata({"title": "Test"})
            assert emb.shape == (768,)

    def test_fit_clusters_insufficient(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        result = d.fit_clusters([], n_clusters=5)
        assert result is False

    def test_fit_clusters_success(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        embeddings = [np.random.rand(768) for _ in range(10)]
        result = d.fit_clusters(embeddings, n_clusters=2)
        assert result is True

    def test_predict_cluster_no_clusters(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        result = d.predict_cluster(np.random.rand(768))
        assert result == -1

    def test_compute_similarity_identical(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        v = np.array([1.0, 0.0, 0.0])
        sim = d.compute_similarity(v, v)
        assert abs(sim - 1.0) < 0.001

    def test_compute_similarity_orthogonal(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        sim = d.compute_similarity(v1, v2)
        assert abs(sim) < 0.001

    def test_find_similar_documents(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        query = np.array([1.0, 0.0])
        docs = [("doc1", np.array([0.9, 0.1])), ("doc2", np.array([0.1, 0.9]))]
        result = d.find_similar_documents(query, docs, top_k=1)
        assert len(result) == 1
        assert result[0][0] == "doc1"

    def test_detect_anomaly_semantic_no_clusters(self):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        is_anom, score = d.detect_anomaly_semantic(np.random.rand(768))
        assert is_anom is False

    def test_get_summary(self):
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        s = d.get_summary()
        assert s["cached_embeddings"] == 0

    def test_save_model(self, tmp_path):
        import numpy as np
        from app.pipeline.agents.deep_learning import TransformerPatternDetector
        d = TransformerPatternDetector()
        d.embeddings_cache["test"] = np.array([1.0, 2.0])
        fp = str(tmp_path / "model.json")
        d.save_model(fp)


# ─── MultiDocumentLearner ──────────────────────────────────────────────────────

class TestMultiDocumentLearner:
    def test_init(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl"))
        assert l.insights is not None

    def test_init_storage_failure(self):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("permission denied")
            with pytest.raises(Exception):
                MultiDocumentLearner("/some/path")

    def test_record_document_empty_id(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl2"))
        l.record_document("", {}, {})
        assert len(l.insights["author_patterns"]) == 0

    def test_record_document_non_dict_metadata(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl3"))
        l.record_document("d1", None, {})
        assert len(l.insights["author_patterns"]) == 0

    def test_record_document_non_dict_metrics(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl4"))
        l.record_document("d1", {}, None)
        assert len(l.insights["author_patterns"]) == 0

    def test_record_document_updates_author_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl5"))
        l.record_document("d1", {"authors": ["Alice"]}, {"references_count": 10, "figures_count": 2, "duration_seconds": 30, "success": True, "validation_errors": 0})
        assert "Alice" in l.insights["author_patterns"]
        assert l.insights["author_patterns"]["Alice"]["document_count"] == 1

    def test_record_document_updates_venue_patterns(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl6"))
        l.record_document("d1", {"venue": "CVPR"}, {"references_count": 15, "figures_count": 5, "duration_seconds": 40, "success": True, "validation_errors": 0})
        assert "CVPR" in l.insights["venue_patterns"]

    def test_record_document_updates_doc_types(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl7"))
        l.record_document("d1", {"document_type": "paper"}, {"references_count": 10, "figures_count": 2, "duration_seconds": 30, "success": True, "validation_errors": 0})
        assert "paper" in l.insights["document_types"]

    def test_record_document_quality_trends(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl8"))
        l.record_document("d1", {}, {"success": True, "validation_errors": 0})
        assert len(l.insights["quality_trends"]) == 1

    def test_get_author_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl9"))
        l.record_document("d1", {"authors": ["Bob"]}, {"references_count": 5, "figures_count": 1, "duration_seconds": 20, "success": True, "validation_errors": 0})
        ins = l.get_author_insights("Bob")
        assert ins is not None
        assert ins["document_count"] == 1

    def test_get_author_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl10"))
        assert l.get_author_insights("") is None

    def test_get_author_insights_nonexistent(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl11"))
        assert l.get_author_insights("Nobody") is None

    def test_get_venue_insights(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl12"))
        l.record_document("d1", {"venue": "NeurIPS"}, {"references_count": 10, "figures_count": 3, "duration_seconds": 25, "success": True, "validation_errors": 0})
        ins = l.get_venue_insights("NeurIPS")
        assert ins is not None

    def test_get_venue_insights_empty(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl13"))
        assert l.get_venue_insights("") is None

    def test_get_similar_documents_non_dict_metadata(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl14"))
        assert l.get_similar_documents(None) == []

    def test_get_similar_documents_no_db(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl15"))
        assert l.get_similar_documents({"authors": ["Alice"]}) == []

    def test_get_insights_summary(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl16"))
        s = l.get_insights_summary()
        assert s["total_authors"] == 0

    def test_get_insights_summary_with_data(self, tmp_path):
        from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
        l = MultiDocumentLearner(str(tmp_path / ".mdl17"))
        l.record_document("d1", {"authors": ["Alice"], "venue": "ICLR"}, {"references_count": 10, "figures_count": 2, "duration_seconds": 30, "success": True, "validation_errors": 0})
        s = l.get_insights_summary()
        assert s["total_authors"] == 1
        assert s["total_venues"] == 1


# ─── RealTimeAdaptiveAgent ─────────────────────────────────────────────────────

class TestRealTimeAdaptiveAgent:
    def test_init(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        assert a.base_timeout == 60.0

    def test_init_negative_timeout(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        with pytest.raises(ValueError, match="base_timeout must be positive"):
            RealTimeAdaptiveAgent(base_timeout=-1)

    def test_init_zero_timeout(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        with pytest.raises(ValueError, match="base_timeout must be positive"):
            RealTimeAdaptiveAgent(base_timeout=0)

    def test_init_clamps_timeout(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent(base_timeout=99999)
        assert a.base_timeout <= 1800.0

    def test_start_processing_empty_id(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("")
        assert a.current_metrics["document_id"] == ""

    def test_start_processing_resets_params(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        assert a.params["retry_enabled"] is True

    def test_record_tool_execution_empty_name(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("", 1.0, True)
        assert len(a.current_metrics["tools_executed"]) == 0

    def test_record_tool_execution_success(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("tool1", 5.0, True)
        assert len(a.current_metrics["tools_executed"]) == 1

    def test_record_tool_execution_failure_adds_error(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("tool1", 5.0, False)
        assert len(a.current_metrics["errors_encountered"]) == 1

    def test_adapt_realtime_extends_timeout(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent(base_timeout=10)
        a.start_processing("doc1")
        a.current_metrics["elapsed_time"] = 8.0
        a._adapt_realtime()
        assert a.params["aggressive_mode"] is True
        assert a.params["timeout"] > 10

    def test_adapt_realtime_switches_to_fallback_on_errors(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("t1", 1.0, False)
        a.record_tool_execution("t2", 1.0, False)
        assert a.current_metrics["current_strategy"] == "fallback"
        assert a.params["retry_enabled"] is False

    def test_adapt_realtime_sets_tool_priority(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("tool_a", 1.0, True)
        assert "tool_a" in a.params.get("tool_priority", [])

    def test_should_continue_timeout_exceeded(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent(base_timeout=10)
        a.start_processing("doc1")
        a.current_metrics["elapsed_time"] = 15.0
        assert a.should_continue() is False

    def test_should_continue_too_many_errors(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        for _ in range(6):
            a.record_tool_execution("t", 1.0, False)
        assert a.should_continue() is False

    def test_should_continue_ok(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.start_processing("doc1")
        a.record_tool_execution("t", 1.0, True)
        assert a.should_continue() is True

    def test_get_current_params(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        params = a.get_current_params()
        assert params["timeout"] == 60.0

    def test_get_metrics(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        metrics = a.get_metrics()
        assert "start_time" in metrics

    def test_recommend_next_tool_empty(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        assert a.recommend_next_tool([]) is None

    def test_recommend_next_tool_uses_priority(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        a.params["tool_priority"] = ["preferred_tool", "other"]
        assert a.recommend_next_tool(["other", "preferred_tool"]) == "preferred_tool"

    def test_recommend_next_tool_fallback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        a = RealTimeAdaptiveAgent()
        assert a.recommend_next_tool(["a", "b"]) == "a"

    def test_notify_adaptation_callback(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        cb = MagicMock()
        a = RealTimeAdaptiveAgent(adaptation_callback=cb)
        a._notify_adaptation("test_event", {"key": "value"})
        cb.assert_called_once_with("test_event", {"key": "value"})

    def test_notify_adaptation_callback_raises(self):
        from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
        cb = MagicMock(side_effect=RuntimeError("cb fail"))
        a = RealTimeAdaptiveAgent(adaptation_callback=cb)
        a._notify_adaptation("test_event", {})


# ─── DocumentAgent ─────────────────────────────────────────────────────────────

class TestDocumentAgent:
    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI", None)
    @patch("app.pipeline.agents.document_agent.CustomLLMFactory")
    def test_init_basic(self, mock_factory, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_llm = MagicMock()
        mock_factory.create_llm.return_value = mock_llm
        agent = DocumentAgent(llm_provider="openai", llm_model="gpt-4")
        assert agent.max_retries == 3

    @patch("app.pipeline.agents.document_agent.settings")
    @patch("app.pipeline.agents.document_agent.ChatOpenAI", MagicMock)
    def test_init_with_chatopenai(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        ChatOpenAI = MagicMock()
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", ChatOpenAI):
            agent = DocumentAgent(llm_provider="openai", llm_model="gpt-4")
            assert agent.tools is not None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_enable_memory(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent(enable_memory=True)
                assert agent.memory is not None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_disable_memory(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent(enable_memory=False)
                assert agent.memory is None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_init_enable_streaming(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent(enable_streaming=True, streaming_callback=lambda x, y: None)
                assert agent.streaming_callback is not None

    @patch("app.pipeline.agents.document_agent.settings")
    def test_process_document(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent()
                agent._execute_with_retry = MagicMock(return_value={"output": "done", "intermediate_steps": []})
                result = agent.process_document("/path/doc.pdf")
                assert result["success"] is True

    @patch("app.pipeline.agents.document_agent.settings")
    def test_process_document_fallback(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent()
                agent._execute_with_retry = MagicMock(return_value={"output": "", "intermediate_steps": [("t", "ERROR: fail")]})
                result = agent.process_document("/path/doc.pdf")
                assert result["should_fallback"] is True

    @patch("app.pipeline.agents.document_agent.settings")
    def test_should_fallback_true(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        result = agent._should_fallback({"intermediate_steps": [("t1", "ERROR: x"), ("t2", "ERROR: y"), ("t3", "OK")]})
        assert result is True

    @patch("app.pipeline.agents.document_agent.settings")
    def test_should_fallback_false(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        result = agent._should_fallback({"intermediate_steps": [("t1", "OK"), ("t2", "OK")]})
        assert result is False

    @patch("app.pipeline.agents.document_agent.settings")
    def test_should_fallback_empty_steps(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        result = agent._should_fallback({"intermediate_steps": []})
        assert result is False

    @patch("app.pipeline.agents.document_agent.settings")
    async def test_run_executor_none_direct_fallback(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent()
                agent.executor = None
                doc = MagicMock()
                doc.filename = "test.pdf"
                doc.document_id = "doc1"
                with patch.object(agent, "_run_direct_fallback") as mock_fb:
                    mock_fb.return_value = {"success": False, "error": "fallback", "should_fallback": True}
                    result = await agent.run(doc, "job1")
                    assert result["success"] is False

    @patch("app.pipeline.agents.document_agent.settings")
    async def test_run_with_executor(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent()
                agent.executor = MagicMock()
                agent.executor.invoke.return_value = {"output": "result", "intermediate_steps": []}
                doc = MagicMock()
                doc.filename = "test.pdf"
                doc.document_id = "doc1"
                result = await agent.run(doc, "job1")
                assert result["success"] is True

    @patch("app.pipeline.agents.document_agent.settings")
    async def test_run_exception_handling(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        mock_settings.GROBID_URL = "http://grobid:8070"
        mock_settings.OPENAI_API_KEY = "sk-test"
        with patch("app.pipeline.agents.document_agent.ChatOpenAI", None):
            with patch("app.pipeline.agents.document_agent.CustomLLMFactory") as mf:
                mf.create_llm.return_value = MagicMock()
                agent = DocumentAgent()
                agent.executor = MagicMock()
                agent.executor.invoke.side_effect = RuntimeError("exec fail")
                doc = MagicMock()
                doc.filename = "test.pdf"
                doc.document_id = "doc1"
                result = await agent.run(doc, "job1")
                assert result["success"] is False

    @patch("app.pipeline.agents.document_agent.settings")
    def test_direct_fallback_all_tools_available(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.tools = []
        for tool_cls_name in ["MetadataExtractionTool", "LayoutAnalysisTool", "ReferenceExtractionTool", "FigureAnalysisTool", "ValidationTool"]:
            t = MagicMock()
            t.name = tool_cls_name
            t._run.return_value = "OK"
            agent.tools.append(t)
        doc = MagicMock()
        doc.document_id = "doc1"
        result = agent._run_direct_fallback(document=doc, doc_path="/p.pdf")
        assert result["success"] is True

    @patch("app.pipeline.agents.document_agent.settings")
    def test_direct_fallback_exception(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        agent = DocumentAgent.__new__(DocumentAgent)
        with patch.object(LayoutAnalysisTool, "__instancecheck__", return_value=True):
            t = MagicMock(spec=LayoutAnalysisTool)
            t.name = "analyze_layout"
            t._run.side_effect = RuntimeError("tool fail")
            agent.tools = [t]
            doc = MagicMock()
            doc.document_id = "doc1"
            result = agent._run_direct_fallback(document=doc, doc_path="/p.pdf")
            assert result["success"] is False

    @patch("app.pipeline.agents.document_agent.settings")
    def test_execute_with_retry_success(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.executor = MagicMock()
        agent.executor.invoke.return_value = {"output": "done"}
        agent.streaming_callback = None
        agent.max_retries = 3
        result = agent._execute_with_retry("input")
        assert result["output"] == "done"

    @patch("app.pipeline.agents.document_agent.settings")
    def test_execute_with_retry_fails_then_succeeds(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = [RuntimeError("first fail"), {"output": "success"}]
        agent.streaming_callback = None
        agent.max_retries = 3
        agent.memory = None
        result = agent._execute_with_retry("input")
        assert result["output"] == "success"

    @patch("app.pipeline.agents.document_agent.settings")
    def test_execute_with_retry_all_fail(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.executor = MagicMock()
        agent.executor.invoke.side_effect = RuntimeError("always fail")
        agent.streaming_callback = None
        agent.max_retries = 2
        agent.memory = None
        with pytest.raises(RuntimeError):
            agent._execute_with_retry("input")

    @patch("app.pipeline.agents.document_agent.settings")
    def test_execute_with_retry_executor_none(self, mock_settings):
        from app.pipeline.agents.document_agent import DocumentAgent
        agent = DocumentAgent.__new__(DocumentAgent)
        agent.executor = None
        agent._agent_import_error = "no langchain"
        agent.max_retries = 1
        agent.streaming_callback = None
        agent.memory = None
        with pytest.raises(RuntimeError, match="no langchain"):
            agent._execute_with_retry("input")


# ─── CustomLLMFactory ──────────────────────────────────────────────────────────

class TestCustomLLMFactory:
    def test_create_llm_litellm(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                llm = CustomLLMFactory.create_llm("openai", "gpt-4", 0.0)
                assert llm is not None

    def test_create_llm_litellm_anthropic(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                llm = CustomLLMFactory.create_llm("anthropic", "claude-3-opus-20240229", 0.0)
                assert llm is not None

    def test_create_llm_litellm_ollama(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                llm = CustomLLMFactory.create_llm("ollama", "llama2", 0.0)
                assert llm is not None

    def test_create_llm_litellm_nvidia(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                llm = CustomLLMFactory.create_llm("nvidia", "meta/llama-3.3-70b-instruct", 0.0)
                assert llm is not None

    def test_create_llm_litellm_unsupported_provider(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", MagicMock()):
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                with pytest.raises(ValueError, match="Unsupported provider"):
                    CustomLLMFactory.create_llm("invalid_provider", "model", 0.0)

    def test_create_llm_langchain_openai_no_key(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            with patch("app.pipeline.agents.llm_factory.settings") as s:
                s.OPENAI_API_KEY = None
                from app.pipeline.agents.llm_factory import CustomLLMFactory
                with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
                    CustomLLMFactory.create_llm("openai", "gpt-4", 0.0)

    def test_create_llm_langchain_openai_with_key(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            with patch("app.pipeline.agents.llm_factory.settings") as s:
                s.OPENAI_API_KEY = "sk-test"
                with patch("app.pipeline.agents.llm_factory.ChatOpenAI") as mock_co:
                    from app.pipeline.agents.llm_factory import CustomLLMFactory
                    CustomLLMFactory.create_llm("openai", "gpt-4", 0.0)
                    mock_co.assert_called_once()

    def test_create_llm_langchain_anthropic(self):
        import sys
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            with patch("app.pipeline.agents.llm_factory.settings") as s:
                s.ANTHROPIC_API_KEY = "sk-ant"
                with patch("app.pipeline.agents.llm_factory.sys.version_info", (3, 10)):
                    mock_ca = MagicMock()
                    fake_mod = MagicMock()
                    fake_mod.ChatAnthropic = mock_ca
                    old_mod = sys.modules.get("langchain_anthropic")
                    sys.modules["langchain_anthropic"] = fake_mod
                    try:
                        from app.pipeline.agents.llm_factory import CustomLLMFactory
                        CustomLLMFactory.create_llm("anthropic", "claude-3", 0.0)
                        mock_ca.assert_called_once()
                    finally:
                        if old_mod is not None:
                            sys.modules["langchain_anthropic"] = old_mod
                        else:
                            sys.modules.pop("langchain_anthropic", None)

    def test_create_llm_langchain_ollama(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            with patch("app.pipeline.agents.llm_factory.settings") as s:
                s.OLLAMA_BASE_URL = "http://localhost:11434"
                with patch("app.pipeline.agents.llm_factory.Ollama") as mock_ol:
                    from app.pipeline.agents.llm_factory import CustomLLMFactory
                    CustomLLMFactory.create_llm("ollama", "llama2", 0.0)
                    mock_ol.assert_called_once()

    def test_create_llm_custom_not_implemented(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(NotImplementedError, match="Custom LLM endpoints not yet implemented"):
                CustomLLMFactory.create_llm("custom", "model", 0.0)

    def test_create_llm_unsupported(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", False):
            from app.pipeline.agents.llm_factory import CustomLLMFactory
            with pytest.raises(ValueError, match="Unsupported provider"):
                CustomLLMFactory.create_llm("bad", "model", 0.0)

    def test_get_available_providers(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        provs = CustomLLMFactory.get_available_providers()
        assert isinstance(provs, list)

    def test_get_recommended_models(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        models = CustomLLMFactory.get_recommended_models("openai")
        assert "gpt-4" in models

    def test_get_recommended_models_unknown(self):
        from app.pipeline.agents.llm_factory import CustomLLMFactory
        models = CustomLLMFactory.get_recommended_models("unknown")
        assert models == []

    def test_litellm_shim_invoke(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", return_value="response text"):
                from app.pipeline.agents.llm_factory import _LiteLLMShim
                shim = _LiteLLMShim(model="gpt-4", temperature=0.0)
                result = shim.invoke("hello")
                assert result.content == "response text"

    def test_litellm_shim_call(self):
        with patch("app.pipeline.agents.llm_factory.LITELLM_AVAILABLE", True):
            with patch("app.pipeline.agents.llm_factory._llm_generate", return_value="response text"):
                from app.pipeline.agents.llm_factory import _LiteLLMShim
                shim = _LiteLLMShim(model="gpt-4", temperature=0.0)
                result = shim("hello")
                assert result == "response text"


# ─── StreamingAgentCallback ────────────────────────────────────────────────────

class TestStreamingAgentCallback:
    def test_init_default_callback(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        assert cb.callback_fn is not None

    def test_init_with_callback(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        assert cb.callback_fn is fn

    def test_on_llm_start(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_llm_start({}, ["prompt1"])
        fn.assert_called_once()

    def test_on_llm_end(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        response = MagicMock()
        response.generations = [MagicMock()]
        cb.on_llm_end(response)
        fn.assert_called_once()

    def test_on_llm_error(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_llm_error(RuntimeError("fail"))
        fn.assert_called_once()

    def test_on_tool_start(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_tool_start({"name": "test_tool"}, "input_str")
        fn.assert_called_once()

    def test_on_tool_end(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_tool_end("output text")
        fn.assert_called_once()

    def test_on_tool_error(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_tool_error(RuntimeError("fail"))
        fn.assert_called_once()

    def test_on_agent_action(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        action = MagicMock()
        action.tool = "test_tool"
        action.tool_input = "input"
        action.log = "log"
        cb.on_agent_action(action)
        fn.assert_called_once()

    def test_on_agent_finish(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        finish = MagicMock()
        finish.return_values = {"output": "done"}
        cb.on_agent_finish(finish)
        fn.assert_called_once()

    def test_on_chain_start(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_chain_start({"name": "chain"}, {})
        fn.assert_called_once()

    def test_on_chain_end(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_chain_end({})
        fn.assert_called_once()

    def test_on_chain_error(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        fn = MagicMock()
        cb = StreamingAgentCallback(callback_fn=fn)
        cb.on_chain_error(RuntimeError("fail"))
        fn.assert_called_once()

    def test_get_events(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        assert cb.get_events() == []

    def test_clear_events(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        cb.events.append({"type": "test"})
        cb.clear_events()
        assert cb.events == []

    def test_default_callback(self):
        from app.pipeline.agents.streaming import StreamingAgentCallback
        cb = StreamingAgentCallback()
        cb._default_callback("event_type", {"data": "value"})
        assert len(cb.events) == 1


# ─── ToolRegistry ──────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_init(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.tools == {}

    def test_register(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return f"result: {inputs}"
        tool_cls = r.register("my_tool", "A test tool", {"param1": (str, "desc")}, exec_fn)
        assert "my_tool" in r.tools
        assert tool_cls.name == "my_tool"

    def test_get_tool_existing(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return "ok"
        r.register("my_tool", "desc", {"p": (str, "d")}, exec_fn)
        cls = r.get_tool("my_tool")
        assert cls is not None

    def test_get_tool_missing(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.get_tool("nonexistent") is None

    def test_list_tools_empty(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.list_tools() == []

    def test_list_tools_with_entries(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return "ok"
        r.register("a", "d", {"p": (str, "d")}, exec_fn)
        r.register("b", "d2", {"p2": (int, "d")}, exec_fn)
        assert set(r.list_tools()) == {"a", "b"}

    def test_create_instance(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return "ok"
        r.register("my_tool", "desc", {"p": (str, "d")}, exec_fn)
        inst = r.create_instance("my_tool")
        assert inst is not None

    def test_create_instance_missing(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.create_instance("nonexistent") is None

    def test_tool_run_success(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return f"Processed: {inputs['query']}"
        r.register("query_tool", "desc", {"query": (str, "d")}, exec_fn)
        inst = r.create_instance("query_tool")
        result = inst._run(query="hello")
        assert "Processed" in result

    def test_tool_run_error(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            raise ValueError("fail")
        r.register("fail_tool", "desc", {"q": (str, "d")}, exec_fn)
        inst = r.create_instance("fail_tool")
        result = inst._run(q="test")
        assert "ERROR" in result

    async def test_tool_arun_raises(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def exec_fn(inputs):
            return "ok"
        r.register("arun_tool", "desc", {"p": (str, "d")}, exec_fn)
        inst = r.create_instance("arun_tool")
        with pytest.raises(NotImplementedError):
            await inst._arun(p="test")


# ─── Global custom_tools functions ─────────────────────────────────────────────

class TestCustomToolsGlobals:
    def test_register_custom_tool(self):
        from app.pipeline.agents.custom_tools import register_custom_tool
        def fn(inputs):
            return "ok"
        cls = register_custom_tool("global_tool", "desc", {"p": (str, "d")}, fn)
        assert cls.name == "global_tool"

    def test_get_custom_tool_existing(self):
        from app.pipeline.agents.custom_tools import register_custom_tool, get_custom_tool
        def fn(inputs):
            return "ok"
        register_custom_tool("get_tool_test", "desc", {"p": (str, "d")}, fn)
        inst = get_custom_tool("get_tool_test")
        assert inst is not None

    def test_get_custom_tool_missing(self):
        from app.pipeline.agents.custom_tools import get_custom_tool
        assert get_custom_tool("nonexistent") is None

    def test_list_custom_tools(self):
        from app.pipeline.agents.custom_tools import list_custom_tools
        tools = list_custom_tools()
        assert isinstance(tools, list)

    def test_create_citation_formatter_tool(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        cls = create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        assert inst is not None

    def test_citation_formatter_apa(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        result = inst._run(authors=["Smith, J.", "Doe, A."], title="Test Paper", year="2024", style="apa")
        assert "et al." not in result

    def test_citation_formatter_apa_many_authors(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        result = inst._run(authors=["A", "B", "C", "D"], title="Paper", year="2024", style="apa")
        assert "et al." in result

    def test_citation_formatter_mla(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        result = inst._run(authors=["Smith, J."], title="Test", year="2024", style="mla")
        assert "Smith" in result

    def test_citation_formatter_mla_no_author(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        result = inst._run(authors=[], title="Test", year="2024", style="mla")
        assert '"Test."' in result

    def test_citation_formatter_chicago(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, get_custom_tool
        create_citation_formatter_tool()
        inst = get_custom_tool("format_citation")
        result = inst._run(authors=["Smith"], title="Test", year="2024", style="chicago")
        assert "Smith" in result

    def test_create_keyword_extractor_tool(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool, get_custom_tool
        create_keyword_extractor_tool()
        inst = get_custom_tool("extract_keywords")
        assert inst is not None

    def test_keyword_extractor_empty_text(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool, get_custom_tool
        create_keyword_extractor_tool()
        inst = get_custom_tool("extract_keywords")
        result = inst._run(text="", max_keywords=5)
        import json
        data = json.loads(result)
        assert data["keywords"] == []

    def test_keyword_extractor_normal(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool, get_custom_tool
        create_keyword_extractor_tool()
        inst = get_custom_tool("extract_keywords")
        result = inst._run(text="machine learning deep learning artificial intelligence", max_keywords=3)
        import json
        data = json.loads(result)
        assert len(data["keywords"]) <= 3


# ─── FederatedLearningNode ─────────────────────────────────────────────────────

class TestFederatedLearningNode:
    def test_init(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("node1", str(tmp_path / ".fl"))
        assert n.node_id == "node1"

    def test_init_empty_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with pytest.raises(ValueError, match="node_id must be a non-empty string"):
            FederatedLearningNode("", str(tmp_path / ".fl2"))

    def test_init_blank_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with pytest.raises(ValueError, match="node_id must be a non-empty string"):
            FederatedLearningNode("   ", str(tmp_path / ".fl3"))

    def test_init_bad_storage(self):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("permission denied")
            with pytest.raises(Exception):
                FederatedLearningNode("n1", "/some/path")

    def test_record_local_update_empty_type(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl4"))
        n.record_local_update("", {"data": 1})
        assert len(n.local_updates) == 0

    def test_record_local_update_non_dict_data(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl5"))
        n.record_local_update("pattern", "not_a_dict")
        assert len(n.local_updates) == 0

    def test_record_local_update_success(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl6"))
        n.record_local_update("pattern", {"key": "val"})
        assert len(n.local_updates) == 1

    def test_get_local_updates_all(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl7"))
        n.record_local_update("a", {"v": 1})
        n.record_local_update("b", {"v": 2})
        assert len(n.get_local_updates()) == 2

    def test_get_local_updates_since_version(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl8"))
        n.global_model["version"] = 3
        n.record_local_update("a", {"v": 1})
        n.record_local_update("b", {"v": 2})
        result = n.get_local_updates(since_version=3)
        assert len(result) == 2

    def test_get_local_updates_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl9"))
        n.local_updates = None
        assert n.get_local_updates() == []

    def test_push_updates_no_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl10"))
        assert n.push_updates_to_coordinator() is False

    def test_push_updates_no_requests(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            from app.pipeline.agents.federated_learning import FederatedLearningNode
            n = FederatedLearningNode("n1", str(tmp_path / ".fl11"), coordinator_url="http://coord")
            assert n.push_updates_to_coordinator() is False

    def test_push_updates_success(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_req.post.return_value = mock_resp
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                n = FederatedLearningNode("n1", str(tmp_path / ".fl12"), coordinator_url="http://coord")
                assert n.push_updates_to_coordinator() is True

    def test_push_updates_http_error(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_req.post.return_value = mock_resp
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                n = FederatedLearningNode("n1", str(tmp_path / ".fl13"), coordinator_url="http://coord")
                assert n.push_updates_to_coordinator() is False

    def test_pull_global_model_no_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl14"))
        assert n.pull_global_model() is False

    def test_pull_global_model_no_requests(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            from app.pipeline.agents.federated_learning import FederatedLearningNode
            n = FederatedLearningNode("n1", str(tmp_path / ".fl15"), coordinator_url="http://coord")
            assert n.pull_global_model() is False

    def test_pull_global_model_success_new_version(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"version": 5, "patterns": []}
                mock_req.get.return_value = mock_resp
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                n = FederatedLearningNode("n1", str(tmp_path / ".fl16"), coordinator_url="http://coord")
                assert n.pull_global_model() is True
                assert n.global_model["version"] == 5

    def test_pull_global_model_same_version(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"version": 0, "patterns": []}
                mock_req.get.return_value = mock_resp
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                n = FederatedLearningNode("n1", str(tmp_path / ".fl17"), coordinator_url="http://coord")
                assert n.pull_global_model() is True

    def test_pull_global_model_http_error(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_req:
                mock_resp = MagicMock()
                mock_resp.status_code = 404
                mock_req.get.return_value = mock_resp
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                n = FederatedLearningNode("n1", str(tmp_path / ".fl18"), coordinator_url="http://coord")
                assert n.pull_global_model() is False

    def test_aggregate_updates_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl19"))
        result = n.aggregate_updates("not_a_list")
        assert result["version"] == 1

    def test_aggregate_updates_with_patterns(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl20"))
        updates = [
            {"node_id": "n1", "update_type": "pattern", "data": {"p": 1}},
            {"node_id": "n2", "update_type": "pattern", "data": {"p": 2}},
            {"node_id": "n1", "update_type": "metric", "data": {"document_count": 10, "avg_duration": 30.0, "success_rate": 0.9}},
        ]
        result = n.aggregate_updates(updates)
        assert result["contributing_nodes"] == 2

    def test_aggregate_updates_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl21"))
        result = n.aggregate_updates([])
        assert result["version"] == 1

    def test_sync_no_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl22"))
        assert n.sync() is False

    def test_get_status(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl23"))
        status = n.get_status()
        assert status["node_id"] == "n1"
        assert status["coordinator_connected"] is False

    def test_aggregate_patterns_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl24"))
        assert n._aggregate_patterns([]) == []

    def test_aggregate_patterns_with_data(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl25"))
        patterns = [{"p": i} for i in range(15)]
        result = n._aggregate_patterns(patterns)
        assert len(result) == 10

    def test_aggregate_metrics_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl26"))
        assert n._aggregate_metrics([]) == {}

    def test_aggregate_metrics_with_data(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        n = FederatedLearningNode("n1", str(tmp_path / ".fl27"))
        metrics = [
            {"document_count": 10, "avg_duration": 30.0, "success_rate": 0.9},
            {"document_count": 20, "avg_duration": 40.0, "success_rate": 0.8},
        ]
        result = n._aggregate_metrics(metrics)
        assert result["total_documents"] == 30
        assert result["avg_duration"] == 35.0
        assert result["contributing_nodes"] == 2


# ─── FederatedCoordinator ──────────────────────────────────────────────────────

class TestFederatedCoordinator:
    def test_init(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc"))
        assert c.registered_nodes == set()

    def test_receive_updates_empty_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc2"))
        assert c.receive_updates("", [{"data": 1}]) is False

    def test_receive_updates_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc3"))
        assert c.receive_updates("n1", "not_a_list") is False

    def test_receive_updates_success(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc4"))
        assert c.receive_updates("n1", [{"data": 1}]) is True
        assert "n1" in c.registered_nodes

    def test_aggregate_and_update(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc5"))
        c.receive_updates("n1", [{"update_type": "pattern", "data": {"p": 1}, "node_id": "n1"}])
        result = c.aggregate_and_update()
        assert result["version"] >= 1

    def test_get_global_model(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc6"))
        model = c.get_global_model()
        assert model["version"] == 0

    def test_get_statistics(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        c = FederatedCoordinator(str(tmp_path / ".fc7"))
        stats = c.get_statistics()
        assert stats["registered_nodes"] == 0


# ─── AdvancedAnalyticsDashboard ────────────────────────────────────────────────

class TestAdvancedAnalyticsDashboard:
    def test_init_all_none(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        assert d.ml_detector is None

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        result = d.generate_html(str(tmp_path / "adv.html"))
        assert result == str(tmp_path / "adv.html")

    def test_build_html(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_html()
        assert "Advanced Agent Analytics" in html

    def test_build_ml_patterns_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_ml_patterns_section()
        assert "Not initialized" in html

    def test_build_ml_patterns_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {
            "pattern_count": 2,
            "trained": True,
            "patterns": [{"cluster_id": 1, "sample_count": 10, "avg_duration": 30.5, "success_rate": 0.85}]
        }
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_ml_patterns_section()
        assert "85.0%" in html

    def test_build_multi_doc_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_multi_doc_section()
        assert "Not initialized" in html

    def test_build_multi_doc_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "total_authors": 3, "total_venues": 2, "document_types": 1,
            "top_authors": [("Alice", {"document_count": 5, "avg_references": 20})]
        }
        d = AdvancedAnalyticsDashboard(multi_doc_learner=mdl)
        html = d._build_multi_doc_section()
        assert "Total Authors" in html

    def test_build_adaptive_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_adaptive_section()
        assert "Not initialized" in html

    def test_build_adaptive_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ad = MagicMock()
        ad.get_config.return_value = {"max_retries": 5, "timeout_seconds": 120, "fallback_threshold": 0.3, "enable_caching": True}
        d = AdvancedAnalyticsDashboard(adaptive_strategy=ad)
        html = d._build_adaptive_section()
        assert "Max Retries" in html

    def test_build_distributed_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_distributed_section()
        assert "Not initialized" in html

    def test_build_distributed_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        dc = MagicMock()
        dc.get_statistics.return_value = {
            "specialists": {"metadata": {"task_count": 10}, "layout": {"task_count": 5}},
            "total_tasks": 15
        }
        d = AdvancedAnalyticsDashboard(distributed_coord=dc)
        html = d._build_distributed_section()
        assert "Distributed Processing" in html

    def test_build_insights_section_with_ml(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.patterns = [{"cluster_id": 1, "success_rate": 0.9, "sample_count": 20, "avg_duration": 25.0}]
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_insights_section()
        assert "Best Performing Pattern" in html

    def test_build_insights_section_with_multi_doc(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "top_authors": [("Bob", {"document_count": 3, "avg_references": 15})]
        }
        d = AdvancedAnalyticsDashboard(multi_doc_learner=mdl)
        html = d._build_insights_section()
        assert "Most Prolific Author" in html

    def test_build_insights_section_empty(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_insights_section()
        assert html == ""

    def test_generate_json_report(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        path = d.generate_json_report(str(tmp_path / "report.json"))
        assert path == str(tmp_path / "report.json")

    def test_generate_json_report_with_all_components(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 1, "patterns": [], "trained": True}
        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {"total_authors": 0, "total_venues": 0, "document_types": 0, "quality_trend_count": 0, "top_authors": [], "top_venues": []}
        ad = MagicMock()
        ad.get_config.return_value = {"max_retries": 3}
        dc = MagicMock()
        dc.get_statistics.return_value = {"specialists": {}, "total_tasks": 0}
        d = AdvancedAnalyticsDashboard(ml_detector=ml, multi_doc_learner=mdl, adaptive_strategy=ad, distributed_coord=dc)
        path = d.generate_json_report(str(tmp_path / "report2.json"))
        assert path == str(tmp_path / "report2.json")


# ─── NextGenDashboard ──────────────────────────────────────────────────────────

class TestNextGenDashboard:
    def test_init_all_none(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        assert d.transformer_detector is None

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        result = d.generate_html(str(tmp_path / "nextgen.html"))
        assert result == str(tmp_path / "nextgen.html")

    def test_build_transformer_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_transformer_section()
        assert "Not initialized" in html

    def test_build_transformer_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        td = MagicMock()
        td.get_summary.return_value = {"model_name": "scibert", "device": "cpu", "cached_embeddings": 50, "n_clusters": 3, "clusters_trained": True}
        d = NextGenDashboard(transformer_detector=td)
        html = d._build_transformer_section()
        assert "scibert" in html

    def test_build_federated_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_federated_section()
        assert "Not initialized" in html

    def test_build_federated_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        fn = MagicMock()
        fn.get_status.return_value = {"node_id": "node1", "local_updates": 10, "global_model_version": 3, "coordinator_connected": True}
        d = NextGenDashboard(federated_node=fn)
        html = d._build_federated_section()
        assert "node1" in html

    def test_build_realtime_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_realtime_section()
        assert "Not initialized" in html

    def test_build_realtime_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        rt = MagicMock()
        rt.get_current_params.return_value = {"timeout": 30.0, "retry_enabled": True, "aggressive_mode": False}
        d = NextGenDashboard(realtime_agent=rt)
        html = d._build_realtime_section()
        assert "30.0s" in html

    def test_build_autoscaling_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_autoscaling_section()
        assert "Not initialized" in html

    def test_build_autoscaling_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        am = MagicMock()
        am.get_statistics.return_value = {"current_workers": 4, "min_workers": 2, "max_workers": 8, "avg_cpu_percent": 45.0, "total_scaling_events": 3}
        d = NextGenDashboard(autoscaling_manager=am)
        html = d._build_autoscaling_section()
        assert "4" in html

    def test_build_marketplace_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_marketplace_section()
        assert "Not initialized" in html

    def test_build_marketplace_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        tm = MagicMock()
        tm.get_installed_tools.return_value = [{"name": "tool1", "version": "1.0"}, {"name": "tool2", "version": "2.0"}]
        d = NextGenDashboard(tool_marketplace=tm)
        html = d._build_marketplace_section()
        assert "Installed Tools" in html

    def test_build_insights_section(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_insights_section()
        assert "Next-Generation Capabilities" in html


# ─── ToolMarketplace ───────────────────────────────────────────────────────────

class TestToolMarketplace:
    def test_init(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm"))
        assert tm.installed_tools == {}

    def test_publish_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm2"))
        result = tm.publish_tool("my_tool", "print('hello')", "A test tool", "author1")
        assert result["success"] is True

    def test_publish_tool_with_tags(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm3"))
        result = tm.publish_tool("tagged_tool", "code", "desc", "author", tags=["tag1", "tag2"])
        assert result["success"] is True

    def test_search_tools_empty(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm4"))
        assert tm.search_tools() == []

    def test_search_tools_with_data(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm5"))
        tm.publish_tool("searchable_tool", "code", "desc", "author", tags=["ai"])
        results = tm.search_tools(query="searchable")
        assert len(results) == 1

    def test_search_tools_by_tags(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm6"))
        tm.publish_tool("tagged", "code", "desc", "author", tags=["ml"])
        results = tm.search_tools(tags=["ml"])
        assert len(results) >= 1

    def test_install_tool_not_found(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm7"))
        result = tm.install_tool("nonexistent")
        assert result["success"] is False

    def test_install_tool_success(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm8"))
        tm.publish_tool("installable", "code123", "desc", "author")
        result = tm.install_tool("installable")
        assert result["success"] is True
        assert "installable" in tm.installed_tools

    def test_install_tool_integrity_fail(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        import json
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm9"))
        tm.publish_tool("bad_hash", "code", "desc", "author")
        tool_file = tm.cache_dir / "bad_hash_v1.0.0.json"
        with open(tool_file, 'r') as f:
            data = json.load(f)
        data["code_hash"] = "tampered"
        with open(tool_file, 'w') as f:
            json.dump(data, f)
        result = tm.install_tool("bad_hash")
        assert result["success"] is False

    def test_uninstall_tool_existing(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm10"))
        tm.installed_tools["to_remove"] = {"version": "1.0", "installed_at": "now", "code": "", "description": ""}
        assert tm.uninstall_tool("to_remove") is True
        assert "to_remove" not in tm.installed_tools

    def test_uninstall_tool_missing(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm11"))
        assert tm.uninstall_tool("nonexistent") is False

    def test_get_installed_tools_empty(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm12"))
        assert tm.get_installed_tools() == []

    def test_get_installed_tools_with_data(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm13"))
        tm.installed_tools["t1"] = {"version": "1.0", "installed_at": "now", "description": "desc"}
        tools = tm.get_installed_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "t1"

    def test_rate_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm14"))
        assert tm.rate_tool("some_tool", 5) is True

    def test_get_tool_stats(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / ".tm15"))
        stats = tm.get_tool_stats("test_tool")
        assert stats["name"] == "test_tool"
        assert stats["total_installs"] == 0


# ─── Tools sub-modules ─────────────────────────────────────────────────────────

class TestFigureAnalysisTool:
    @patch("app.pipeline.agents.tools.figure_tool.DoclingClient")
    def test_init(self, mock_dc):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        t = FigureAnalysisTool()
        assert t.name == "analyze_figures"

    @patch("app.pipeline.agents.tools.figure_tool.DoclingClient")
    def test_run_success(self, mock_dc):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.return_value = {"blocks": [
            {"block_type": "figure", "text": "Fig 1 caption", "bbox": {"x": 0}, "page": 1}
        ]}
        t = FigureAnalysisTool()
        result = t._run("test.pdf")
        assert "success" in result

    @patch("app.pipeline.agents.tools.figure_tool.DoclingClient")
    def test_run_no_layout(self, mock_dc):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.return_value = None
        t = FigureAnalysisTool()
        result = t._run("test.pdf")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.figure_tool.DoclingClient")
    def test_run_exception(self, mock_dc):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.side_effect = RuntimeError("fail")
        t = FigureAnalysisTool()
        result = t._run("test.pdf")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.figure_tool.DoclingClient")
    async def test_arun_not_implemented(self, mock_dc):
        from app.pipeline.agents.tools.figure_tool import FigureAnalysisTool
        t = FigureAnalysisTool()
        with pytest.raises(NotImplementedError):
            await t._arun("test.pdf")


class TestLayoutAnalysisTool:
    @patch("app.pipeline.agents.tools.layout_tool.DoclingClient")
    def test_init(self, mock_dc):
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        t = LayoutAnalysisTool()
        assert t.name == "analyze_layout"

    @patch("app.pipeline.agents.tools.layout_tool.DoclingClient")
    def test_run_success(self, mock_dc):
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.return_value = {"blocks": [
            {"block_type": "heading_1", "text": "Intro", "font_size": 16},
            {"block_type": "paragraph", "text": "Content", "font_size": 12}
        ]}
        t = LayoutAnalysisTool()
        result = t._run("test.pdf")
        assert "success" in result

    @patch("app.pipeline.agents.tools.layout_tool.DoclingClient")
    def test_run_no_data(self, mock_dc):
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.return_value = None
        t = LayoutAnalysisTool()
        result = t._run("test.pdf")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.layout_tool.DoclingClient")
    def test_run_exception(self, mock_dc):
        from app.pipeline.agents.tools.layout_tool import LayoutAnalysisTool
        inst = mock_dc.return_value
        inst.analyze_layout.side_effect = RuntimeError("fail")
        t = LayoutAnalysisTool()
        result = t._run("test.pdf")
        assert "ERROR" in result


class TestMetadataExtractionTool:
    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_init(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        t = MetadataExtractionTool()
        assert t.name == "extract_metadata"

    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_run_success(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        with patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            inst = mock_gc.return_value
            inst.is_available.return_value = True
            inst.extract_metadata.return_value = {
                "title": "Test Paper", "authors": ["Author"], "abstract": "Abstract",
                "affiliations": [], "publication_date": "2024", "doi": "10.1234/test",
                "keywords": ["ml"], "references": []
            }
            t = MetadataExtractionTool()
            result = t._run("test.pdf")
            assert "success" in result

    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_run_cached_result(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        with patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = {"status": "success", "metadata": {"title": "Cached"}}
            t = MetadataExtractionTool()
            result = t._run("test.pdf")
            assert "Cached" in result

    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_run_grobid_unavailable(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        with patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            inst = mock_gc.return_value
            inst.is_available.return_value = False
            t = MetadataExtractionTool()
            result = t._run("test.pdf")
            assert "ERROR" in result

    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_run_no_metadata(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        with patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.return_value = None
            inst = mock_gc.return_value
            inst.is_available.return_value = True
            inst.extract_metadata.return_value = None
            t = MetadataExtractionTool()
            result = t._run("test.pdf")
            assert "ERROR" in result

    @patch("app.pipeline.agents.tools.metadata_tool.GROBIDClient")
    def test_run_exception(self, mock_gc):
        from app.pipeline.agents.tools.metadata_tool import MetadataExtractionTool
        with patch("app.cache.redis_cache.redis_cache") as mock_cache:
            mock_cache.get_grobid_result.side_effect = RuntimeError("fail")
            t = MetadataExtractionTool()
            result = t._run("test.pdf")
            assert "ERROR" in result


class TestReferenceExtractionTool:
    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    @patch("app.pipeline.agents.tools.reference_tool.ReferenceParser")
    def test_init(self, mock_rp, mock_gc):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        t = ReferenceExtractionTool()
        assert t.name == "extract_references"

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    @patch("app.pipeline.agents.tools.reference_tool.ReferenceParser")
    def test_run_success(self, mock_rp, mock_gc):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        inst = mock_gc.return_value
        inst.is_available.return_value = True
        inst.extract_metadata.return_value = {
            "references": [
                {"raw_text": "Ref 1", "title": "Paper 1", "authors": ["A"], "year": "2024", "doi": "10.1", "venue": "Venue"}
            ]
        }
        t = ReferenceExtractionTool()
        result = t._run("test.pdf")
        assert "success" in result

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    @patch("app.pipeline.agents.tools.reference_tool.ReferenceParser")
    def test_run_grobid_unavailable(self, mock_rp, mock_gc):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        inst = mock_gc.return_value
        inst.is_available.return_value = False
        t = ReferenceExtractionTool()
        result = t._run("test.pdf")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    @patch("app.pipeline.agents.tools.reference_tool.ReferenceParser")
    def test_run_no_references(self, mock_rp, mock_gc):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        inst = mock_gc.return_value
        inst.is_available.return_value = True
        inst.extract_metadata.return_value = {}
        t = ReferenceExtractionTool()
        result = t._run("test.pdf")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.reference_tool.GROBIDClient")
    @patch("app.pipeline.agents.tools.reference_tool.ReferenceParser")
    def test_run_exception(self, mock_rp, mock_gc):
        from app.pipeline.agents.tools.reference_tool import ReferenceExtractionTool
        inst = mock_gc.return_value
        inst.is_available.side_effect = RuntimeError("fail")
        t = ReferenceExtractionTool()
        result = t._run("test.pdf")
        assert "ERROR" in result


class TestValidationTool:
    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_init(self, mock_dv):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        t = ValidationTool()
        assert t.name == "validate_document"

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_set_document(self, mock_dv):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        t = ValidationTool()
        doc = MagicMock()
        t.set_document("doc1", doc)
        assert "doc1" in t._document_cache

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_run_success(self, mock_dv):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        t = ValidationTool()
        doc = MagicMock()
        meta = MagicMock()
        meta.title = "Test"
        meta.authors = ["A"]
        meta.abstract = "Abstract"
        doc.metadata = meta
        doc.validation_errors = []
        doc.validation_warnings = []
        doc.references = []
        doc.document_id = "doc1"
        vr = MagicMock()
        vr.is_valid = True
        vr.errors = []
        vr.warnings = []
        mock_dv.return_value.validate.return_value = vr
        t.set_document("doc1", doc)
        result = t._run("doc1")
        assert "success" in result

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_run_document_not_found(self, mock_dv):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        t = ValidationTool()
        result = t._run("nonexistent")
        assert "ERROR" in result

    @patch("app.pipeline.agents.tools.validation_tool.DocumentValidator")
    def test_run_exception(self, mock_dv):
        from app.pipeline.agents.tools.validation_tool import ValidationTool
        t = ValidationTool()
        doc = MagicMock()
        doc.metadata = MagicMock()
        doc.metadata.title = "Test"
        doc.metadata.authors = ["A"]
        doc.metadata.abstract = "Abstract"
        doc.validation_errors = ["bad"]
        doc.validation_warnings = []
        doc.references = []
        t.set_document("doc1", doc)
        mock_dv.return_value.validate.side_effect = RuntimeError("validation error")
        result = t._run("doc1")
        assert "ERROR" in result
