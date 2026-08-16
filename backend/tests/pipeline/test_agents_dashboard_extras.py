# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.pipeline]


# =============================================================================
# ComparisonDashboard (dashboard.py)
# =============================================================================


class TestComparisonDashboard:
    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        tracker.get_summary.return_value = {
            "agent": {"count": 5, "avg_references": 12.3, "avg_figures": 4.5},
            "legacy": {"count": 3, "avg_references": 8.1, "avg_figures": 2.3},
            "total_runs": 8,
            "last_updated": "2026-01-01",
        }
        tracker.get_comparison.return_value = {
            "agent_vs_legacy": {
                "speed": {"agent_avg_duration": 15.2, "legacy_avg_duration": 30.5},
                "quality": {
                    "agent_success_rate": 0.95,
                    "legacy_success_rate": 0.80,
                    "agent_avg_errors": 0.5,
                    "legacy_avg_errors": 2.1,
                },
                "reliability": {"agent_fallback_rate": 0.1, "agent_runs": 5, "legacy_runs": 3},
            }
        }
        d = ComparisonDashboard(tracker)
        out = tmp_path / "dash.html"
        assert d.generate_html(str(out)) == str(out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Agent vs Legacy Performance Dashboard" in content
        assert "15.20" in content

    def test_generate_html_empty(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        tracker.get_summary.return_value = {}
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {}, "quality": {}, "reliability": {}}}
        d = ComparisonDashboard(tracker)
        out = tmp_path / "empty.html"
        assert d.generate_html(str(out)) == str(out)

    def test_generate_json_report(self, tmp_path):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        tracker.get_comparison.return_value = {"agent_vs_legacy": {"speed": {"agent_avg_duration": 1.0}}}
        d = ComparisonDashboard(tracker)
        out = tmp_path / "report.json"
        assert d.generate_json_report(str(out)) == str(out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["agent_vs_legacy"]["speed"]["agent_avg_duration"] == 1.0

    def test_build_html_happy_path(self):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        d = ComparisonDashboard(tracker)
        html = d._build_html({"agent": {}, "legacy": {}, "total_runs": 0}, {"agent_vs_legacy": {}})
        assert "<!DOCTYPE html>" in html
        assert "Performance Dashboard" in html

    def test_build_html_with_data(self):
        from app.pipeline.agents.dashboard import ComparisonDashboard

        tracker = MagicMock()
        d = ComparisonDashboard(tracker)
        summary = {
            "agent": {"count": 10, "avg_references": 15, "avg_figures": 5},
            "legacy": {"count": 8, "avg_references": 10, "avg_figures": 3},
            "total_runs": 18,
            "last_updated": "2026-06-01",
        }
        comp = {
            "agent_vs_legacy": {
                "speed": {"agent_avg_duration": 12.5, "legacy_avg_duration": 25.0},
                "quality": {
                    "agent_success_rate": 0.9,
                    "legacy_success_rate": 0.7,
                    "agent_avg_errors": 1.0,
                    "legacy_avg_errors": 3.0,
                },
                "reliability": {"agent_fallback_rate": 0.05},
            }
        }
        html = d._build_html(summary, comp)
        assert "10" in html
        assert "8" in html
        assert "12.50" in html
        assert "90.0%" in html or "90%" in html


# =============================================================================
# AdvancedAnalyticsDashboard (advanced_dashboard.py)
# =============================================================================


class TestAdvancedAnalyticsDashboard:
    def test_init_none(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        assert d.ml_detector is None
        assert d.multi_doc_learner is None
        assert d.adaptive_strategy is None
        assert d.distributed_coord is None

    def test_init_with_deps(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ml = MagicMock()
        mdl = MagicMock()
        ads = MagicMock()
        dc = MagicMock()
        d = AdvancedAnalyticsDashboard(ml, mdl, ads, dc)
        assert d.ml_detector is ml
        assert d.multi_doc_learner is mdl
        assert d.adaptive_strategy is ads
        assert d.distributed_coord is dc

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        out = tmp_path / "adv.html"
        assert d.generate_html(str(out)) == str(out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Advanced Agent Analytics" in content

    def test_generate_html_with_deps(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 3, "patterns": [], "trained": True}
        ml.patterns = [{"cluster_id": 0, "success_rate": 0.9, "sample_count": 10, "avg_duration": 5.0}]
        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "total_authors": 5,
            "total_venues": 3,
            "document_types": 2,
            "quality_trend_count": 10,
            "top_authors": [("Author A", {"document_count": 3, "avg_references": 15})],
            "top_venues": [],
        }
        ads = MagicMock()
        ads.get_config.return_value = {
            "max_retries": 3,
            "timeout_seconds": 60,
            "fallback_threshold": 0.5,
            "enable_caching": True,
        }
        dc = MagicMock()
        dc.get_statistics.return_value = {"total_tasks": 100, "specialists": {"parser": {"task_count": 50}}}
        d = AdvancedAnalyticsDashboard(ml, mdl, ads, dc)
        out = tmp_path / "adv_full.html"
        assert d.generate_html(str(out)) == str(out)
        content = out.read_text(encoding="utf-8")
        assert "ML Pattern Detection" in content
        assert "Multi-Document Learning" in content
        assert "Adaptive Strategies" in content
        assert "Distributed Processing" in content

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
            "patterns": [
                {"cluster_id": 1, "sample_count": 10, "avg_duration": 5.0, "success_rate": 0.9},
                {"cluster_id": 2, "sample_count": 5, "avg_duration": 3.0, "success_rate": 0.8},
            ],
        }
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_ml_patterns_section()
        assert "Patterns Detected" in html
        assert "Trained" in html

    def test_build_ml_patterns_section_not_trained(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 0, "trained": False, "patterns": []}
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_ml_patterns_section()
        assert "Not Trained" in html

    def test_build_multi_doc_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        html = d._build_multi_doc_section()
        assert "Not initialized" in html

    def test_build_multi_doc_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "total_authors": 5,
            "total_venues": 3,
            "document_types": 2,
            "quality_trend_count": 10,
            "top_authors": [("Author A", {"document_count": 3, "avg_references": 15})],
            "top_venues": [],
        }
        d = AdvancedAnalyticsDashboard(multi_doc_learner=mdl)
        html = d._build_multi_doc_section()
        assert "Total Authors" in html
        assert "Author A" in html

    def test_build_adaptive_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        html = d._build_adaptive_section()
        assert "Not initialized" in html

    def test_build_adaptive_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ads = MagicMock()
        ads.get_config.return_value = {
            "max_retries": 5,
            "timeout_seconds": 120,
            "fallback_threshold": 0.3,
            "enable_caching": False,
        }
        d = AdvancedAnalyticsDashboard(adaptive_strategy=ads)
        html = d._build_adaptive_section()
        assert "5" in html
        assert "Disabled" in html

    def test_build_distributed_section_not_initialized(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        html = d._build_distributed_section()
        assert "Not initialized" in html

    def test_build_distributed_section_with_data(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        dc = MagicMock()
        dc.get_statistics.return_value = {
            "total_tasks": 200,
            "specialists": {"formatter": {"task_count": 80}, "parser": {"task_count": 120}},
        }
        d = AdvancedAnalyticsDashboard(distributed_coord=dc)
        html = d._build_distributed_section()
        assert "200" in html
        assert "Formatter" in html or "formatter" in html
        assert "Parser" in html or "parser" in html

    def test_build_insights_section_empty(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        html = d._build_insights_section()
        assert html == ""

    def test_build_insights_section_with_ml_pattern(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ml = MagicMock()
        ml.patterns = [{"cluster_id": 0, "success_rate": 0.95, "sample_count": 20, "avg_duration": 3.5}]
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_insights_section()
        assert "Best Performing Pattern" in html
        assert "95.0%" in html or "95%" in html

    def test_build_insights_section_with_author(self):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "total_authors": 1,
            "total_venues": 1,
            "document_types": 1,
            "quality_trend_count": 1,
            "top_authors": [("Dr. Smith", {"document_count": 5, "avg_references": 20})],
            "top_venues": [],
        }
        d = AdvancedAnalyticsDashboard(multi_doc_learner=mdl)
        html = d._build_insights_section()
        assert "Most Prolific Author" in html
        assert "Dr. Smith" in html

    def test_generate_json_report_no_deps(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        d = AdvancedAnalyticsDashboard()
        out = tmp_path / "report.json"
        assert d.generate_json_report(str(out)) == str(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["ml_patterns"] is None
        assert data["multi_doc_insights"] is None

    def test_generate_json_report_with_deps(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard

        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 1, "patterns": [], "trained": True}
        mdl = MagicMock()
        mdl.get_insights_summary.return_value = {
            "total_authors": 0,
            "total_venues": 0,
            "document_types": 0,
            "quality_trend_count": 0,
            "top_authors": [],
            "top_venues": [],
        }
        ads = MagicMock()
        ads.get_config.return_value = {
            "max_retries": 3,
            "timeout_seconds": 60,
            "fallback_threshold": 0.5,
            "enable_caching": True,
        }
        dc = MagicMock()
        dc.get_statistics.return_value = {"total_tasks": 0, "specialists": {}}
        d = AdvancedAnalyticsDashboard(ml, mdl, ads, dc)
        out = tmp_path / "full_report.json"
        d.generate_json_report(str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["ml_patterns"]["pattern_count"] == 1
        assert data["multi_doc_insights"] is not None
        assert data["adaptive_config"]["max_retries"] == 3
        assert data["distributed_stats"]["total_tasks"] == 0


# =============================================================================
# NextGenDashboard (nextgen_dashboard.py)
# =============================================================================


class TestNextGenDashboard:
    def test_init_none(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        assert d.transformer_detector is None
        assert d.federated_node is None
        assert d.realtime_agent is None
        assert d.autoscaling_manager is None
        assert d.tool_marketplace is None

    def test_init_with_deps(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        td = MagicMock()
        fn = MagicMock()
        rt = MagicMock()
        am = MagicMock()
        tm = MagicMock()
        d = NextGenDashboard(td, fn, rt, am, tm)
        assert d.transformer_detector is td
        assert d.federated_node is fn
        assert d.realtime_agent is rt
        assert d.autoscaling_manager is am
        assert d.tool_marketplace is tm

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        out = tmp_path / "nextgen.html"
        assert d.generate_html(str(out)) == str(out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "Next-Gen AI Agent Dashboard" in content

    def test_generate_html_with_deps(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        td = MagicMock()
        td.get_summary.return_value = {
            "model_name": "scibert",
            "device": "cpu",
            "cached_embeddings": 50,
            "n_clusters": 3,
            "clusters_trained": True,
        }
        fn = MagicMock()
        fn.get_status.return_value = {
            "node_id": "node-1",
            "local_updates": 10,
            "global_model_version": 2,
            "coordinator_connected": True,
        }
        rt = MagicMock()
        rt.get_current_params.return_value = {"timeout": 30.0, "retry_enabled": True, "aggressive_mode": False}
        am = MagicMock()
        am.get_statistics.return_value = {
            "current_workers": 5,
            "min_workers": 2,
            "max_workers": 10,
            "avg_cpu_percent": 45.3,
            "total_scaling_events": 3,
        }
        tm = MagicMock()
        tm.get_installed_tools.return_value = [
            {"name": "formatter", "version": "1.0.0"},
            {"name": "extractor", "version": "2.1.0"},
        ]
        d = NextGenDashboard(td, fn, rt, am, tm)
        out = tmp_path / "nextgen_full.html"
        d.generate_html(str(out))
        content = out.read_text(encoding="utf-8")
        assert "Deep Learning" in content
        assert "Federated Learning" in content
        assert "Real-Time Adaptation" in content
        assert "Auto-Scaling" in content
        assert "Tool Marketplace" in content

    def test_build_transformer_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_transformer_section()
        assert "Not initialized" in html

    def test_build_transformer_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        td = MagicMock()
        td.get_summary.return_value = {
            "model_name": "bert-base",
            "device": "cuda",
            "cached_embeddings": 100,
            "n_clusters": 5,
            "clusters_trained": True,
        }
        d = NextGenDashboard(transformer_detector=td)
        html = d._build_transformer_section()
        assert "bert-base" in html
        assert "CUDA" in html or "cuda" in html

    def test_build_transformer_section_not_trained(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        td = MagicMock()
        td.get_summary.return_value = {
            "model_name": "test",
            "device": "cpu",
            "cached_embeddings": 0,
            "n_clusters": 0,
            "clusters_trained": False,
        }
        d = NextGenDashboard(transformer_detector=td)
        html = d._build_transformer_section()
        assert "Not Trained" in html

    def test_build_federated_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_federated_section()
        assert "Not initialized" in html

    def test_build_federated_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        fn = MagicMock()
        fn.get_status.return_value = {
            "node_id": "abc-123",
            "local_updates": 25,
            "global_model_version": 3,
            "coordinator_connected": True,
        }
        d = NextGenDashboard(federated_node=fn)
        html = d._build_federated_section()
        assert "abc-123" in html
        assert "Connected" in html

    def test_build_federated_section_offline(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        fn = MagicMock()
        fn.get_status.return_value = {
            "node_id": "x",
            "local_updates": 0,
            "global_model_version": 1,
            "coordinator_connected": False,
        }
        d = NextGenDashboard(federated_node=fn)
        html = d._build_federated_section()
        assert "Offline" in html

    def test_build_realtime_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_realtime_section()
        assert "Not initialized" in html

    def test_build_realtime_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        rt = MagicMock()
        rt.get_current_params.return_value = {"timeout": 60.0, "retry_enabled": True, "aggressive_mode": False}
        d = NextGenDashboard(realtime_agent=rt)
        html = d._build_realtime_section()
        assert "60.0" in html
        assert "Normal" in html

    def test_build_realtime_section_aggressive(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        rt = MagicMock()
        rt.get_current_params.return_value = {"timeout": 30.0, "retry_enabled": False, "aggressive_mode": True}
        d = NextGenDashboard(realtime_agent=rt)
        html = d._build_realtime_section()
        assert "Active" in html
        assert "No" in html

    def test_build_autoscaling_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_autoscaling_section()
        assert "Not initialized" in html

    def test_build_autoscaling_section_with_data(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        am = MagicMock()
        am.get_statistics.return_value = {
            "current_workers": 3,
            "min_workers": 1,
            "max_workers": 8,
            "avg_cpu_percent": 62.5,
            "total_scaling_events": 7,
        }
        d = NextGenDashboard(autoscaling_manager=am)
        html = d._build_autoscaling_section()
        assert "3" in html
        assert "1 - 8" in html or "1" in html

    def test_build_marketplace_section_not_initialized(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_marketplace_section()
        assert "Not initialized" in html

    def test_build_marketplace_section_empty(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        tm = MagicMock()
        tm.get_installed_tools.return_value = []
        d = NextGenDashboard(tool_marketplace=tm)
        html = d._build_marketplace_section()
        assert "0" in html

    def test_build_marketplace_section_with_tools(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        tm = MagicMock()
        tm.get_installed_tools.return_value = [
            {"name": "tool-a", "version": "1.0.0"},
            {"name": "tool-b", "version": "2.0.0"},
        ]
        d = NextGenDashboard(tool_marketplace=tm)
        html = d._build_marketplace_section()
        assert "tool-a" in html
        assert "2" in html

    def test_build_insights_section(self):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard

        d = NextGenDashboard()
        html = d._build_insights_section()
        assert "Next-Generation Capabilities" in html
        assert "Transformer Models" in html
        assert "Federated Learning" in html
        assert "Real-Time Adaptation" in html
        assert "Auto-Scaling" in html
