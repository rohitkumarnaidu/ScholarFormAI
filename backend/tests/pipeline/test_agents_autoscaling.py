# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch
import time
import pytest

pytestmark = [pytest.mark.pipeline]


class TestAutoScalingManagerInit:
    def test_init_defaults(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        assert mgr.min_workers == 2
        assert mgr.max_workers == 8
        assert mgr.target_cpu_percent == 70.0
        assert mgr.target_memory_percent == 80.0
        assert mgr.current_workers == 2
        assert mgr.metrics_history == []
        assert mgr.scaling_events == []

    def test_init_custom_values(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=3, max_workers=10, target_cpu_percent=50.0, target_memory_percent=90.0)
        assert mgr.min_workers == 3
        assert mgr.max_workers == 10
        assert mgr.target_cpu_percent == 50.0
        assert mgr.target_memory_percent == 90.0

    def test_init_min_workers_too_low(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(min_workers=0)
            assert False
        except ValueError as e:
            assert "min_workers" in str(e)

    def test_init_max_workers_less_than_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(min_workers=5, max_workers=3)
            assert False
        except ValueError as e:
            assert "max_workers" in str(e)

    def test_init_target_cpu_percent_zero(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(target_cpu_percent=0.0)
            assert False
        except ValueError as e:
            assert "target_cpu_percent" in str(e)

    def test_init_target_cpu_percent_over_100(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(target_cpu_percent=150.0)
            assert False
        except ValueError as e:
            assert "target_cpu_percent" in str(e)

    def test_init_target_memory_percent_zero(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(target_memory_percent=0.0)
            assert False
        except ValueError as e:
            assert "target_memory_percent" in str(e)

    def test_init_target_memory_percent_over_100(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        try:
            AutoScalingManager(target_memory_percent=120.0)
            assert False
        except ValueError as e:
            assert "target_memory_percent" in str(e)


class TestAutoScalingManagerSystemMetrics:
    def test_get_system_metrics_psutil_unavailable(self):
        with patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", False):
            from app.pipeline.agents.autoscaling import AutoScalingManager
            mgr = AutoScalingManager()
            metrics = mgr.get_system_metrics()
            assert metrics["cpu_percent"] == 0.0
            assert metrics["memory_percent"] == 0.0
            assert metrics["memory_available_gb"] == 0.0
            assert "timestamp" in metrics

    def test_get_system_metrics_psutil_available(self):
        with patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", True):
            with patch("app.pipeline.agents.autoscaling.psutil") as mock_psutil:
                mock_psutil.cpu_percent.return_value = 45.0
                mock_psutil.virtual_memory.return_value.percent = 60.0
                mock_psutil.virtual_memory.return_value.available = 2 * 1024 ** 3
                from app.pipeline.agents.autoscaling import AutoScalingManager
                mgr = AutoScalingManager()
                metrics = mgr.get_system_metrics()
                assert metrics["cpu_percent"] == 45.0
                assert metrics["memory_percent"] == 60.0
                assert metrics["memory_available_gb"] == 2.0
                assert "timestamp" in metrics

    def test_get_system_metrics_psutil_exception(self):
        with patch("app.pipeline.agents.autoscaling._PSUTIL_AVAILABLE", True):
            with patch("app.pipeline.agents.autoscaling.psutil") as mock_psutil:
                mock_psutil.cpu_percent.side_effect = RuntimeError("cpu fail")
                from app.pipeline.agents.autoscaling import AutoScalingManager
                mgr = AutoScalingManager()
                metrics = mgr.get_system_metrics()
                assert metrics["cpu_percent"] == 0.0


class TestAutoScalingManagerShouldScaleUp:
    def test_scale_up_cpu_high(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        assert mgr.should_scale_up({"cpu_percent": 85.0, "memory_percent": 50.0}) is True

    def test_scale_up_cpu_high_at_max(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=3)
        mgr.current_workers = 3
        assert mgr.should_scale_up({"cpu_percent": 85.0, "memory_percent": 50.0}) is False

    def test_scale_up_cpu_moderate_mem_low(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        assert mgr.should_scale_up({"cpu_percent": 60.0, "memory_percent": 40.0}) is True

    def test_scale_up_cpu_moderate_mem_high(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        assert mgr.should_scale_up({"cpu_percent": 60.0, "memory_percent": 90.0}) is False

    def test_scale_up_cpu_low(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        assert mgr.should_scale_up({"cpu_percent": 20.0, "memory_percent": 50.0}) is False

    def test_scale_up_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        result = mgr.should_scale_up(None)
        assert result is False


class TestAutoScalingManagerShouldScaleDown:
    def test_scale_down_cpu_low(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 3
        assert mgr.should_scale_down({"cpu_percent": 20.0, "memory_percent": 50.0}) is True

    def test_scale_down_cpu_low_at_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=2, max_workers=5)
        mgr.current_workers = 2
        assert mgr.should_scale_down({"cpu_percent": 20.0, "memory_percent": 50.0}) is False

    def test_scale_down_mem_high(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5, target_memory_percent=70.0)
        mgr.current_workers = 3
        assert mgr.should_scale_down({"cpu_percent": 50.0, "memory_percent": 85.0}) is True

    def test_scale_down_mem_high_at_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=2, max_workers=5, target_memory_percent=70.0)
        mgr.current_workers = 2
        assert mgr.should_scale_down({"cpu_percent": 50.0, "memory_percent": 85.0}) is False

    def test_scale_down_no_action(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 3
        assert mgr.should_scale_down({"cpu_percent": 50.0, "memory_percent": 50.0}) is False

    def test_scale_down_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        result = mgr.should_scale_down(None)
        assert result is False


class TestAutoScalingManagerScaleUp:
    def test_scale_up_normal(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        mgr.scale_up()
        assert mgr.current_workers == 3
        assert len(mgr.scaling_events) == 1
        assert mgr.scaling_events[0]["type"] == "scale_up"

    def test_scale_up_at_max(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=3)
        mgr.current_workers = 3
        mgr.scale_up()
        assert mgr.current_workers == 3
        assert len(mgr.scaling_events) == 0

    def test_scale_up_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        with patch.object(mgr.executor, "shutdown", side_effect=RuntimeError("shutdown fail")):
            mgr.scale_up()


class TestAutoScalingManagerScaleDown:
    def test_scale_down_normal(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 4
        mgr.scale_down()
        assert mgr.current_workers == 3
        assert len(mgr.scaling_events) == 1
        assert mgr.scaling_events[0]["type"] == "scale_down"

    def test_scale_down_at_min(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=2, max_workers=5)
        mgr.current_workers = 2
        mgr.scale_down()
        assert mgr.current_workers == 2
        assert len(mgr.scaling_events) == 0

    def test_scale_down_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 3
        with patch.object(mgr.executor, "shutdown", side_effect=RuntimeError("shutdown fail")):
            mgr.scale_down()


class TestAutoScalingManagerAutoScale:
    def test_auto_scale_triggers_scale_up(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 2
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 85.0, "memory_percent": 50.0, "timestamp": time.time()}):
            mgr.auto_scale()
            assert mgr.current_workers == 3

    def test_auto_scale_triggers_scale_down(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 4
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 20.0, "memory_percent": 50.0, "timestamp": time.time()}):
            mgr.auto_scale()
            assert mgr.current_workers == 3

    def test_auto_scale_no_action(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.current_workers = 3
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 50.0, "memory_percent": 50.0, "timestamp": time.time()}):
            mgr.auto_scale()
            assert mgr.current_workers == 3

    def test_auto_scale_trims_history(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        mgr.metrics_history = [{"cpu": i} for i in range(150)]
        with patch.object(mgr, "get_system_metrics", return_value={"cpu_percent": 50.0, "memory_percent": 50.0, "timestamp": time.time()}):
            mgr.auto_scale()
            assert len(mgr.metrics_history) <= 101

    def test_auto_scale_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.get_system_metrics = MagicMock(side_effect=RuntimeError("metrics fail"))
        mgr.auto_scale()


class TestAutoScalingManagerGetExecutor:
    def test_get_executor_triggers_auto_scale(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=1, max_workers=5)
        with patch.object(mgr, "auto_scale") as mock_as:
            executor = mgr.get_executor()
            mock_as.assert_called_once()
            assert executor is mgr.executor


class TestAutoScalingManagerGetStatistics:
    def test_get_statistics_empty_history(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager(min_workers=2, max_workers=8)
        stats = mgr.get_statistics()
        assert stats["current_workers"] == 2
        assert stats["min_workers"] == 2
        assert stats["max_workers"] == 8
        assert stats["avg_cpu_percent"] == 0.0
        assert stats["avg_memory_percent"] == 0.0
        assert stats["total_scaling_events"] == 0
        assert stats["scale_up_count"] == 0
        assert stats["scale_down_count"] == 0

    def test_get_statistics_with_history(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.metrics_history = [
            {"cpu_percent": 50.0, "memory_percent": 60.0},
            {"cpu_percent": 70.0, "memory_percent": 80.0},
        ]
        stats = mgr.get_statistics()
        assert stats["avg_cpu_percent"] == 60.0
        assert stats["avg_memory_percent"] == 70.0

    def test_get_statistics_with_scaling_events(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.scaling_events = [
            {"type": "scale_up", "from": 2, "to": 3},
            {"type": "scale_up", "from": 3, "to": 4},
            {"type": "scale_down", "from": 4, "to": 3},
        ]
        stats = mgr.get_statistics()
        assert stats["total_scaling_events"] == 3
        assert stats["scale_up_count"] == 2
        assert stats["scale_down_count"] == 1

    def test_get_statistics_history_over_10(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.metrics_history = [{"cpu_percent": float(i), "memory_percent": float(i * 2)} for i in range(20)]
        stats = mgr.get_statistics()
        assert stats["avg_cpu_percent"] == sum(range(10, 20)) / 10.0

    def test_get_statistics_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.metrics_history = [None]
        stats = mgr.get_statistics()
        assert "current_workers" in stats


class TestAutoScalingManagerShutdown:
    def test_shutdown_normal(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        mgr.shutdown()

    def test_shutdown_exception_safe(self):
        from app.pipeline.agents.autoscaling import AutoScalingManager
        mgr = AutoScalingManager()
        with patch.object(mgr.executor, "shutdown", side_effect=RuntimeError("shutdown fail")):
            mgr.shutdown()
