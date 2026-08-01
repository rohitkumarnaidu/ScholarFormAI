from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

TEST_PROVIDER = "nvidia"
TEST_MODEL = "llama-70b"


class TestMetricsManager:
    def test_record_llm_cache_hit(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_cache_hit(TEST_PROVIDER, TEST_MODEL)

    def test_record_llm_cache_miss(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_cache_miss(TEST_PROVIDER, TEST_MODEL)

    def test_record_llm_request(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_request(TEST_PROVIDER, TEST_MODEL, True)

    def test_record_llm_duration(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_duration(TEST_PROVIDER, TEST_MODEL, 0.5)

    def test_record_llm_ttft(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_ttft(TEST_PROVIDER, TEST_MODEL, 0.1)

    def test_record_llm_failure(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_failure(TEST_PROVIDER)

    def test_record_clamav_scan_duration(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_clamav_scan_duration(0.3)

    def test_record_pipeline_start(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_pipeline_start()

    def test_record_pipeline_completion_success(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_pipeline_completion(1.5, success=True)

    def test_record_pipeline_completion_error(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_pipeline_completion(2.0, success=False)

    def test_record_step_duration(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_step_duration("parsing", 0.3)

    def test_record_pipeline_stage_duration(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_pipeline_stage_duration("ocr", 0.75)

    def test_record_upload_ack_duration(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_upload_ack_duration(0.2, route="documents")

    def test_record_tool_usage_success(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_tool_usage("extract_text", success=True)

    def test_record_tool_usage_error(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_tool_usage("extract_text", success=False)

    def test_record_llm_usage(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_llm_usage(TEST_PROVIDER, TEST_MODEL, 100, 50)

    def test_set_celery_queue_depth(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.set_celery_queue_depth("batch", 5)

    def test_sse_connection_open(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.sse_connection_open()

    def test_sse_connection_closed(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.sse_connection_closed()

    def test_ws_connection_open(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.ws_connection_open()

    def test_ws_connection_closed(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.ws_connection_closed()

    def test_record_user_activity(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_user_activity("user-abc")

    def test_record_user_activity_empty(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_user_activity("")

    def test_record_retry(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_retry()

    def test_record_provider_operation(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_provider_operation("test_key", "success")

    def test_record_provider_operation_error(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_provider_operation("test_key", "error")

    def test_record_persona_event(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_persona_event("researcher", "upload", "success")

    def test_record_persona_latency(self):
        from app.middleware.prometheus_metrics import MetricsManager
        MetricsManager.record_persona_latency("researcher", "upload", 0.5)


class TestPrometheusMetricsMiddleware:
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        with patch("app.middleware.prometheus_metrics.generate_latest") as mock_gen:
            mock_gen.return_value = b"# HELP ..."
            from app.middleware.prometheus_metrics import prometheus_metrics_middleware
            request = MagicMock()
            request.url.path = "/metrics"
            call_next = AsyncMock()
            response = await prometheus_metrics_middleware(request, call_next)
            assert response.status_code == 200
            assert "text/plain" in response.media_type
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_metrics_endpoint_passes(self):
        from app.middleware.prometheus_metrics import prometheus_metrics_middleware
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        call_next = AsyncMock(return_value="ok")
        response = await prometheus_metrics_middleware(request, call_next)
        assert response == "ok"
        call_next.assert_called_once_with(request)
