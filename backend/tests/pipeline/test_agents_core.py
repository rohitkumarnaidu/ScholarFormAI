# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock


class TestComparisonDashboard:
    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"count": 5},
            "legacy": {"count": 3},
            "total_runs": 8,
            "last_updated": "2026-01-01",
        }
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}}
        d = ComparisonDashboard(tracker)
        assert d.generate_html(str(tmp_path / "dash.html")) == str(tmp_path / "dash.html")

    def test_generate_json_report(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        tracker.get_comparison.return_value = {"agent_vs_legacy": {}}
        d = ComparisonDashboard(tracker)
        assert d.generate_json_report(str(tmp_path / "report.json")) == str(tmp_path / "report.json")


class TestPerformanceTracker:
    def test_get_summary(self):
        from app.pipeline.agents.metrics import PerformanceTracker

        t = PerformanceTracker()
        assert isinstance(t.get_summary(), dict)


class TestDistributedCoordinator:
    def test_get_statistics(self):
        from app.pipeline.agents.distributed import DistributedCoordinator

        dc = DistributedCoordinator()
        assert isinstance(dc.get_statistics(), dict)


class TestAgentsInit:
    def test_import(self):
        from app.pipeline.agents import __all__

        assert "DocumentAgent" in __all__
