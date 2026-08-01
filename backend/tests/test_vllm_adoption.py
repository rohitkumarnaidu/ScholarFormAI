from unittest.mock import patch


class TestCounterTotal:
    def test_sums_matching_samples(self):
        from app.services.vllm_adoption import _counter_total

        class MockMetric:
            name = "test_metric_total"

        class MockSample:
            name = "test_metric_total"
            value = 42.0

        class MockCollector:
            def collect(self):
                return [type("M", (), {"samples": [MockSample()]})()]

        counter = MockCollector()
        result = _counter_total(counter)
        assert result == 42.0

    def test_ignores_non_matching(self):
        from app.services.vllm_adoption import _counter_total

        class MockSample:
            name = "other_metric"
            value = 99.0

        class MockCollector:
            def collect(self):
                return [type("M", (), {"samples": [MockSample()]})()]

        result = _counter_total(MockCollector())
        assert result == 0.0


class MockPromCollector:
    """Reusable mock prometheus-style counter collector."""

    def __init__(self, value):
        self._value = value

    def collect(self):
        class MockMetric:
            name = "mock_metric"
        mock = type("M", (), {"samples": [
            type("S", (), {"name": "mock_metric_total", "value": self._value})()
        ]})()
        return [mock]


class TestGetLlmRequestsTotal:
    def test_returns_total(self):
        from app.services.vllm_adoption import get_llm_requests_total
        mock_collector = MockPromCollector(1500.0)
        with patch("app.middleware.prometheus_metrics.LLM_REQUESTS_TOTAL", mock_collector):
            result = get_llm_requests_total()
        assert result == 1500.0


class TestGetLlmTokensTotal:
    def test_returns_total(self):
        from app.services.vllm_adoption import get_llm_tokens_total
        mock_collector = MockPromCollector(2500000.0)
        with patch("app.middleware.prometheus_metrics.AGENT_LLM_TOKENS_TOTAL", mock_collector):
            result = get_llm_tokens_total()
        assert result == 2500000.0


class TestBuildVllmAdoptionReport:
    def test_returns_report(self):
        from app.services.vllm_adoption import build_vllm_adoption_report
        with patch("app.services.vllm_adoption.settings") as mock_s:
            mock_s.VLLM_ADOPTION_ENABLED = True
            mock_s.VLLM_TARGET_MODEL = "test/model"
            mock_s.VLLM_TARGET_GPU = "A100"
            mock_s.VLLM_REQUESTS_PER_HOUR_THRESHOLD = 2000
            mock_s.VLLM_DAILY_TOKENS_THRESHOLD = 5000000
            with patch("app.services.vllm_adoption.get_llm_requests_total", return_value=3000.0):
                with patch("app.services.vllm_adoption.get_llm_tokens_total", return_value=6000000.0):
                    report = build_vllm_adoption_report()
        assert report["enabled"] is True
        assert report["target"]["model"] == "test/model"
        assert report["traffic"]["thresholds_met"]["requests_per_hour"] is True
        assert report["traffic"]["thresholds_met"]["daily_tokens"] is True
        assert report["traffic"]["traffic_justifies_phase4"] is True
        assert report["phase4_plan"]["status"] == "ready"

    def test_hold_when_thresholds_not_met(self):
        from app.services.vllm_adoption import build_vllm_adoption_report
        with patch("app.services.vllm_adoption.settings") as mock_s:
            mock_s.VLLM_ADOPTION_ENABLED = True
            mock_s.VLLM_TARGET_MODEL = "test/model"
            mock_s.VLLM_TARGET_GPU = "A100"
            mock_s.VLLM_REQUESTS_PER_HOUR_THRESHOLD = 2000
            mock_s.VLLM_DAILY_TOKENS_THRESHOLD = 5000000
            with patch("app.services.vllm_adoption.get_llm_requests_total", return_value=100.0):
                with patch("app.services.vllm_adoption.get_llm_tokens_total", return_value=50000.0):
                    report = build_vllm_adoption_report()
        assert report["phase4_plan"]["status"] == "hold"
        assert report["traffic"]["traffic_justifies_phase4"] is False
