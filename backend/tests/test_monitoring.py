# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Tests for monitoring middleware and Prometheus metrics.
"""

import contextlib

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.monitoring import MonitoringMiddleware
from app.middleware.prometheus_metrics import MetricsManager, prometheus_metrics_middleware

# Create a dummy app for testing
app = FastAPI()
app.add_middleware(MonitoringMiddleware)
app.middleware("http")(prometheus_metrics_middleware)


@app.get("/test")
async def test_endpoint():
    MetricsManager.record_pipeline_start()
    MetricsManager.record_pipeline_completion(1.5, True)
    return {"message": "ok"}


@app.get("/error")
async def error_endpoint():
    MetricsManager.record_pipeline_start()
    MetricsManager.record_pipeline_completion(0.5, False)
    raise ValueError("Oops")


client = TestClient(app)


def test_metrics_endpoint():
    """Test that /metrics endpoint returns Prometheus formatted metrics."""
    # Reset registry or use default (Prometheus client is global)

    # Make some requests to generate metrics
    client.get("/test")
    client.get("/test")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    content = response.text
    # Check for our custom metrics
    assert "pipeline_requests_total" in content
    assert 'status="active"' in content
    assert 'status="completed"' in content
    assert "pipeline_duration_seconds" in content
    assert "active_processing_jobs" in content


def test_monitoring_middleware_headers():
    """Test that monitoring middleware adds trace IDs and timing headers."""
    response = client.get("/test")
    assert response.status_code == 200

    # Check custom headers
    assert "X-Request-ID" in response.headers
    assert "X-Processing-Time" in response.headers

    # Check ID format (UUID)
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36  # Simple length check for UUID string


def test_metrics_logic():
    """Test specific metric recording logic."""
    # Record some explicit metrics via Manager
    MetricsManager.record_tool_usage("test_tool", True)
    MetricsManager.record_llm_usage("openai", "gpt-4", 100, 50)

    response = client.get("/metrics")
    content = response.text

    assert 'agent_tools_usage_total{status="success",tool_name="test_tool"}' in content
    assert 'agent_llm_tokens_total{model="gpt-4",provider="openai",type="input"}' in content


def test_monitoring_middleware_request_id_from_header():
    """Test that MonitoringMiddleware uses x-request-id from header when present."""
    response = client.get("/test", headers={"x-request-id": "custom-id-123"})
    assert response.headers["X-Request-ID"] == "custom-id-123"


def test_monitoring_middleware_error_logged():
    """Test that MonitoringMiddleware logs errors."""
    from unittest.mock import MagicMock, patch

    middleware = MonitoringMiddleware(app)
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/fail"
    request.headers.get.return_value = None

    async def failing_call_next(req):
        raise ValueError("Oops")

    with patch("app.middleware.monitoring.logger") as mock_log:
        import asyncio

        with contextlib.suppress(ValueError):
            asyncio.run(middleware.dispatch(request, failing_call_next))
        mock_log.error.assert_called_once()
        log_msg = mock_log.error.call_args[0][0]
        assert "Request failed" in log_msg
        assert "Oops" in log_msg
