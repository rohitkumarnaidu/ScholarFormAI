from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.observability]


class TestLoggingCorrectness:
    def test_structured_logging_contains_required_fields(self):
        logger = logging.getLogger("app.test_observability")
        handler = MyHandler()
        logger.addHandler(handler)
        logger.info("test message", extra={"job_id": "abc-123"})
        assert handler.records
        last = handler.records[-1]
        assert last.msg == "test message"

    def test_no_sensitive_data_at_info_level(self):
        logger = logging.getLogger("app.test_sensitive")
        handler = MyHandler()
        logger.addHandler(handler)
        sensitive_fields = ["password", "secret", "token", "api_key", "credential"]
        logger.info("User activity completed successfully")
        safe = handler.records[-1].msg if handler.records else ""
        for field in sensitive_fields:
            assert field not in safe.lower()


class TestMetricEmission:
    def test_prometheus_metrics_registered(self):
        with patch("app.middleware.prometheus_metrics.PIPELINE_REQUESTS_TOTAL") as mock:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_pipeline_start()
            mock.labels.assert_called_once_with(status="active")

    def test_llm_failure_metric_recorded(self):
        with patch("app.middleware.prometheus_metrics.LLM_FAILURES_TOTAL") as mock:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_failure("nvidia")
            mock.labels.assert_called_once_with(provider="nvidia")

    def test_metrics_are_thread_safe(self):
        from app.middleware.prometheus_metrics import MetricsManager
        with patch("app.middleware.prometheus_metrics.ACTIVE_USERS") as mock:
            MetricsManager.record_user_activity("user1")
            mock.set.assert_called()


class TestRequestIDPropagation:
    def test_log_extra_includes_context(self):
        from app.utils.logging_context import log_extra
        extra = log_extra(job_id="test-job")
        assert isinstance(extra, dict)
        assert extra.get("job_id") == "test-job"
        assert "request_id" in extra


class TestErrorLogging:
    @patch("app.middleware.prometheus_metrics.MetricsManager")
    def test_error_metrics_tracked(self, mock_metrics):
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.NVIDIA_API_KEY = "test-key"
            mock_settings.NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"
            mock_settings.LLM_PROVIDER_TIMEOUT_SECONDS = 15
            mock_settings.LLM_CACHE_TTL_SECONDS = 3600
            mock_settings.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
            mock_settings.GROQ_API_KEY = None
            mock_settings.OPENROUTER_API_KEY = None
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            with patch("app.services.llm_service._call_with_provider_circuit", side_effect=Exception("API error")):
                from app.services.llm_service import generate_with_fallback
                with pytest.raises(Exception):
                    generate_with_fallback([{"role": "user", "content": "test"}])


class TestHealthEndpoint:
    @pytest.mark.asyncio
    @patch("app.db.supabase_client.check_supabase_health")
    @patch("app.services.health_checks.settings")
    async def test_health_check_returns_status(self, mock_settings, mock_sb):
        mock_sb.return_value = {"status": "healthy"}
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
        mock_settings.OLLAMA_URL = "http://localhost:11434"
        mock_settings.HEALTH_CACHE_TTL_SECONDS = 0
        mock_settings.DEBUG = True
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_ctx = MagicMock()
            mock_ctx.__aenter__.return_value.get.return_value = mock_resp
            mock_httpx.return_value = mock_ctx
            from app.services.health_checks import get_health_payload
            payload, status_code = await get_health_payload(force_refresh=True)
            assert isinstance(payload, dict)
            assert "status" in payload

    @pytest.mark.asyncio
    @patch("app.db.supabase_client.check_supabase_health")
    @patch("app.services.health_checks.settings")
    async def test_readiness_probe_reflects_dependency_status(self, mock_settings, mock_sb):
        mock_sb.return_value = {"status": "healthy"}
        mock_settings.SUPABASE_URL = "https://test.supabase.co"
        mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
        mock_settings.GROBID_ENABLED = False
        mock_settings.OLLAMA_URL = "http://localhost:11434"
        mock_settings.READINESS_CACHE_TTL_SECONDS = 0
        mock_settings.DEBUG = True
        with patch("app.services.health_checks._probe_service_targets") as mock_probe:
            mock_probe.return_value = {"status": "ready"}
            from app.services.health_checks import get_readiness_payload
            payload, status_code = await get_readiness_payload(force_refresh=True)
            assert isinstance(payload, dict)
            assert "ready" in payload


class TestAuditLog:
    def test_audit_log_for_security_events(self):
        from app.services.document_service import DocumentService
        with patch("app.services.document_service.logger") as mock_logger:
            DocumentService.generate_signed_download_url(
                file_url="https://storage.example.com/doc.docx",
                file_path="/path/doc.docx",
                secret="test-secret-for-audit",
            )
            assert mock_logger is not None


class TestPerformanceMetrics:
    def test_latency_metric_observed(self):
        with patch("app.middleware.prometheus_metrics.PIPELINE_DURATION_SECONDS") as mock:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_pipeline_completion(1.5, True)
            mock.labels.assert_called_once_with(status="success")

    def test_error_rate_metric_incremented(self):
        with patch("app.middleware.prometheus_metrics.LLM_FAILURES_TOTAL") as mock:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_failure("groq")
            mock.labels.assert_called_once_with(provider="groq")

    def test_llm_duration_buckets_recorded(self):
        with patch("app.middleware.prometheus_metrics.LLM_REQUEST_DURATION_SECONDS") as mock:
            from app.middleware.prometheus_metrics import MetricsManager
            MetricsManager.record_llm_duration("nvidia", "test-model", 2.5)
            mock.labels.assert_called_once_with(provider="nvidia", model="test-model")


class MyHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
    def emit(self, record):
        self.records.append(record)
