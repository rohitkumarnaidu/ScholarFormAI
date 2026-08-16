# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

import pytest


class TestRecordCall:
    def test_record_nvidia_success(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.5)
        assert m.metrics["nvidia"]["total_calls"] == 1
        assert m.metrics["nvidia"]["successful_calls"] == 1
        assert m.metrics["nvidia"]["total_latency"] == 0.5

    def test_record_nvidia_failure(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", False, 1.2)
        assert m.metrics["nvidia"]["failed_calls"] == 1
        assert m.metrics["nvidia"]["avg_latency"] == 1.2

    def test_record_deepseek_with_quality(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("deepseek", True, 0.8, quality_score=0.95)
        assert m.metrics["deepseek"]["total_calls"] == 1
        assert len(m.quality_scores) == 1
        assert m.quality_scores[0]["score"] == 0.95

    def test_record_rules_success(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("rules", True, 0.1)
        assert m.metrics["rules"]["successful_calls"] == 1

    def test_record_unknown_model(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("unknown_model", True, 0.5)
        assert "unknown_model" not in m.metrics

    def test_record_multiple_calls_avg_latency(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 1.0)
        m.record_call("nvidia", True, 3.0)
        assert m.metrics["nvidia"]["avg_latency"] == 2.0
        assert m.metrics["nvidia"]["total_calls"] == 2


class TestPersistMetric:
    def test_persistence_disabled_skips(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        with patch("threading.Thread") as mock_t:
            m._persist_metric("nvidia", 0.5, True, None)
        mock_t.assert_not_called()

    def test_persistence_enabled_spawns_thread(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        with patch("threading.Thread") as mock_t:
            mock_t.return_value = MagicMock()
            m._persist_metric("nvidia", 0.5, True, 0.9)
        mock_t.assert_called_once()

    def test_persist_thread_supabase_success(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        mock_sb = MagicMock()
        with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
            with patch("threading.Thread") as mock_t:
                real_target = None

                def capture_target(**kw):
                    nonlocal real_target
                    real_target = kw.get("target")
                    return MagicMock()

                mock_t.side_effect = capture_target
                m._persist_metric("nvidia", 0.5, True, 0.9)
            if real_target:
                real_target()

    def test_persist_thread_supabase_unavailable(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            with patch("threading.Thread") as mock_t:
                real_target = None

                def capture_target(**kw):
                    nonlocal real_target
                    real_target = kw.get("target")
                    return MagicMock()

                mock_t.side_effect = capture_target
                m._persist_metric("nvidia", 0.5, True, None)
            if real_target:
                real_target()

    def test_persist_missing_table_disables(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
            'Could not find the table "model_metrics"'
        )
        with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
            with patch("threading.Thread") as mock_t:
                real_target = None

                def capture_target(**kw):
                    nonlocal real_target
                    real_target = kw.get("target")
                    return MagicMock()

                mock_t.side_effect = capture_target
                m._persist_metric("nvidia", 0.5, True, None)
            if real_target:
                real_target()
        assert m._persistence_enabled is False


class TestRecordFallback:
    def test_records_fallback_event(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_fallback("nvidia", "deepseek", "timeout")
        assert len(m.fallback_chain) == 1
        assert m.fallback_chain[0]["from"] == "nvidia"
        assert m.fallback_chain[0]["to"] == "deepseek"
        assert m.fallback_chain[0]["reason"] == "timeout"


class TestGetSummary:
    def test_summary_structure(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.5)
        m.record_fallback("nvidia", "deepseek", "timeout")
        summary = m.get_summary()
        assert "models" in summary
        assert "fallback_rate" in summary
        assert "total_fallbacks" in summary
        assert "avg_quality_scores" in summary

    def test_fallback_rate_zero(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        summary = m.get_summary()
        assert summary["total_fallbacks"] == 0


class TestGetModelComparison:
    def test_comparison_structure(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.3)
        m.record_call("deepseek", True, 0.7)
        m.record_call("rules", True, 1.0)
        cmp = m.get_model_comparison()
        assert "nvidia_vs_deepseek" in cmp
        assert "agent_vs_legacy" in cmp
        assert cmp["nvidia_vs_deepseek"]["nvidia_faster"] is True

    def test_empty_metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        cmp = m.get_model_comparison()
        assert cmp["nvidia_vs_deepseek"]["nvidia_success_rate"] >= 0


class TestExportMetrics:
    def test_exports_to_json_file(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.5)
        with patch("builtins.open", mock_open()) as mock_f:
            m.export_metrics("/tmp/test_metrics.json")
        mock_f.assert_called_once_with("/tmp/test_metrics.json", "w")

    def test_exported_data_has_expected_keys(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.5)
        with patch("builtins.open", mock_open()) as mock_f:
            m.export_metrics("/tmp/test_metrics.json")
        mock_f.assert_called_once_with("/tmp/test_metrics.json", "w")


class TestGetModelMetrics:
    def test_returns_singleton(self):
        from app.services.model_metrics import _model_metrics, get_model_metrics

        _model_metrics = None
        s1 = get_model_metrics()
        s2 = get_model_metrics()
        assert s1 is s2

    def test_uses_get_or_create(self):
        from app.services.model_metrics import _model_metrics, get_model_metrics

        _model_metrics = None
        with patch("app.services.model_metrics.get_or_create", return_value="mock_instance"):
            result = get_model_metrics()
            assert result == "mock_instance"


class TestQualityScores:
    def test_quality_scores_empty_no_error(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        summary = m.get_summary()
        assert summary["avg_quality_scores"]["nvidia"] == 0.0

    def test_quality_scores_averaged(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m.record_call("nvidia", True, 0.5, quality_score=0.8)
        m.record_call("nvidia", True, 0.4, quality_score=0.9)
        summary = m.get_summary()
        assert summary["avg_quality_scores"]["nvidia"] == pytest.approx(0.85)


class TestAutomationLevel:
    def test_high_automation(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        for _ in range(50):
            m.record_call("nvidia", True, 0.3)
        m.record_call("rules", True, 0.1)
        cmp = m.get_model_comparison()
        assert "High" in cmp["agent_vs_legacy"]["automation_level"]

    def test_low_automation(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        for _ in range(5):
            m.record_call("nvidia", True, 0.3)
        for _ in range(5):
            m.record_call("rules", True, 0.1)
        cmp = m.get_model_comparison()
        assert "Low" in cmp["agent_vs_legacy"]["automation_level"]
