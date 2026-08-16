from unittest.mock import mock_open, patch

import pytest


class TestRecordCall:
    @pytest.fixture
    def metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        return m

    def test_records_successful_call(self, metrics):
        metrics.record_call("nvidia", True, 0.5)
        assert metrics.metrics["nvidia"]["total_calls"] == 1
        assert metrics.metrics["nvidia"]["successful_calls"] == 1
        assert metrics.metrics["nvidia"]["total_latency"] == 0.5
        assert metrics.metrics["nvidia"]["last_used"] is not None

    def test_records_failed_call(self, metrics):
        metrics.record_call("deepseek", False, 1.0)
        assert metrics.metrics["deepseek"]["failed_calls"] == 1

    def test_ignores_unknown_model(self, metrics):
        metrics.record_call("unknown_model", True, 0.5)
        for model in metrics.metrics.values():
            assert model["total_calls"] == 0

    def test_calculates_avg_latency(self, metrics):
        metrics.record_call("nvidia", True, 1.0)
        metrics.record_call("nvidia", True, 3.0)
        assert metrics.metrics["nvidia"]["avg_latency"] == 2.0

    def test_appends_quality_score(self, metrics):
        metrics.record_call("nvidia", True, 0.5, quality_score=0.95)
        assert len(metrics.quality_scores) == 1
        assert metrics.quality_scores[0]["score"] == 0.95
        assert metrics.quality_scores[0]["model"] == "nvidia"


class TestRecordFallback:
    @pytest.fixture
    def metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        return m

    def test_appends_fallback(self, metrics):
        metrics.record_fallback("nvidia", "deepseek", "timeout")
        assert len(metrics.fallback_chain) == 1
        assert metrics.fallback_chain[0]["from"] == "nvidia"
        assert metrics.fallback_chain[0]["to"] == "deepseek"


class TestGetSummary:
    @pytest.fixture
    def metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        return m

    def test_returns_summary(self, metrics):
        metrics.record_call("nvidia", True, 0.5)
        summary = metrics.get_summary()
        assert "models" in summary
        assert "fallback_rate" in summary
        assert "total_fallbacks" in summary
        assert summary["total_fallbacks"] == 0

    def test_avg_quality_empty(self, metrics):
        summary = metrics.get_summary()
        assert summary["avg_quality_scores"]["nvidia"] == 0.0


class TestGetModelComparison:
    @pytest.fixture
    def metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        return m

    def test_returns_comparison(self, metrics):
        metrics.record_call("nvidia", True, 0.3)
        metrics.record_call("nvidia", True, 0.2)
        metrics.record_call("nvidia", True, 0.25)
        metrics.record_call("nvidia", True, 0.22)
        metrics.record_call("nvidia", True, 0.28)
        metrics.record_call("deepseek", True, 1.0)
        metrics.record_call("deepseek", True, 0.9)
        metrics.record_call("rules", True, 0.1)
        comp = metrics.get_model_comparison()
        assert "nvidia_vs_deepseek" in comp
        assert "agent_vs_legacy" in comp
        assert comp["nvidia_vs_deepseek"]["nvidia_faster"] is True
        assert comp["agent_vs_legacy"]["automation_level"] == "High"


class TestExportMetrics:
    @pytest.fixture
    def metrics(self):
        from app.services.model_metrics import ModelMetrics

        m = ModelMetrics()
        m._persistence_enabled = False
        return m

    def test_exports_to_json(self, metrics):
        with patch("builtins.open", mock_open()) as mock_f:
            metrics.export_metrics("/tmp/test.json")
        mock_f.assert_called_once_with("/tmp/test.json", "w")


class TestGetModelMetrics:
    def test_returns_global_instance(self):
        from app.services.model_metrics import get_model_metrics

        m1 = get_model_metrics()
        m2 = get_model_metrics()
        assert m1 is m2
