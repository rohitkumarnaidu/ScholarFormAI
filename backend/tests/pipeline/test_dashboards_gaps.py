# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ==============================================================================
# AdvancedAnalyticsDashboard — app.pipeline.agents.advanced_dashboard
# ==============================================================================

class TestAdvancedAnalyticsDashboard:
    def test_all_none(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        d = AdvancedAnalyticsDashboard()
        html = d._build_html()
        assert "Not initialized" in html
        assert "ML Pattern Detection" in html
        assert "Multi-Document Learning" in html
        assert "Adaptive Strategies" in html
        assert "Distributed Processing" in html

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 2, "patterns": [], "trained": True}
        ml.patterns = []
        mdoc = MagicMock()
        mdoc.get_insights_summary.return_value = {
            "total_authors": 1, "total_venues": 1, "document_types": 1,
            "quality_trend_count": 1, "top_authors": [], "top_venues": []
        }
        adaptive = MagicMock()
        adaptive.get_config.return_value = {"max_retries": 3, "timeout_seconds": 30, "fallback_threshold": 0.5, "enable_caching": True}
        dist = MagicMock()
        dist.get_statistics.return_value = {"total_tasks": 10, "specialists": {}}
        d = AdvancedAnalyticsDashboard(ml_detector=ml, multi_doc_learner=mdoc, adaptive_strategy=adaptive, distributed_coord=dist)
        path = d.generate_html(str(tmp_path / "dash.html"))
        assert path.endswith("dash.html")
        content = tmp_path.joinpath("dash.html").read_text()
        assert "Advanced Agent Analytics" in content

    def test_generate_json_report(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 0, "patterns": [], "trained": False}
        mdoc = MagicMock()
        mdoc.get_insights_summary.return_value = {"total_authors": 0, "total_venues": 0, "document_types": 0, "quality_trend_count": 0, "top_authors": [], "top_venues": []}
        adaptive = MagicMock()
        adaptive.get_config.return_value = {"max_retries": 3, "timeout_seconds": 30, "fallback_threshold": 0.5, "enable_caching": True}
        dist = MagicMock()
        dist.get_statistics.return_value = {"total_tasks": 0, "specialists": {}}
        d = AdvancedAnalyticsDashboard(ml_detector=ml, multi_doc_learner=mdoc, adaptive_strategy=adaptive, distributed_coord=dist)
        path = d.generate_json_report(str(tmp_path / "report.json"))
        assert path.endswith("report.json")

    def test_build_insights_section_best_pattern(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 1, "patterns": [], "trained": True}
        ml.patterns = [{"cluster_id": 0, "success_rate": 0.95, "sample_count": 20, "avg_duration": 5.0}]
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_html()
        assert "95.0%" in html or "95" in html

    def test_partial_init(self, tmp_path):
        from app.pipeline.agents.advanced_dashboard import AdvancedAnalyticsDashboard
        ml = MagicMock()
        ml.get_pattern_summary.return_value = {"pattern_count": 0, "patterns": [], "trained": False}
        ml.patterns = []
        d = AdvancedAnalyticsDashboard(ml_detector=ml)
        html = d._build_html()
        assert "ML Pattern Detection" in html


# ==============================================================================
# NextGenDashboard — app.pipeline.agents.nextgen_dashboard
# ==============================================================================

class TestNextGenDashboard:
    def test_all_none(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        d = NextGenDashboard()
        html = d._build_html()
        assert "Not initialized" in html
        assert "Deep Learning" in html
        assert "Federated Learning" in html
        assert "Real-Time Adaptation" in html
        assert "Auto-Scaling" in html
        assert "Tool Marketplace" in html

    def test_generate_html(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        tf = MagicMock()
        tf.get_summary.return_value = {"model_name": "bert", "device": "cpu", "cached_embeddings": 0, "clusters_trained": False, "n_clusters": 0}
        fed = MagicMock()
        fed.get_status.return_value = {"node_id": "n1", "local_updates": 0, "global_model_version": 0, "coordinator_connected": False}
        d = NextGenDashboard(transformer_detector=tf, federated_node=fed)
        path = d.generate_html(str(tmp_path / "ng_dash.html"))
        assert path.endswith("ng_dash.html")
        content = tmp_path.joinpath("ng_dash.html").read_text(encoding="utf-8")
        assert "Next-Gen AI Agent Dashboard" in content

    def test_partial_transformer_only(self, tmp_path):
        from app.pipeline.agents.nextgen_dashboard import NextGenDashboard
        tf = MagicMock()
        tf.get_summary.return_value = {"model_name": "scibert", "device": "cuda", "cached_embeddings": 100, "clusters_trained": True, "n_clusters": 5}
        d = NextGenDashboard(transformer_detector=tf)
        html = d._build_html()
        assert "scibert" in html
        assert "Trained" in html
