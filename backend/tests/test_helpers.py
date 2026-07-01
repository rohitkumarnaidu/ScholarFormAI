import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


class TestResolvePersona:
    def test_formatter_persona(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/documents/upload") == "formatter"

    def test_authoring_persona(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/generator/create") == "authoring"

    def test_synthesis_persona(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/synthesis/start") == "synthesis"

    def test_billing_persona(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/billing/plans") == "billing"

    def test_templates_persona(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/templates/list") == "templates"

    def test_unknown_persona_falls_to_platform(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/health") == "platform"

    def test_empty_path_falls_to_platform(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("") == "platform"

    def test_case_insensitive(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/API/V1/DOCUMENTS") == "formatter"


class TestMetricSafeLabel:
    def test_sanitizes_special_chars(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("hello-world!@#") == "hello_world"

    def test_strips_trailing_underscores(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("__hello__") == "hello"

    def test_fallback_on_pure_special(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("!!!") == "unknown"

    def test_lowercases(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("HELLO World") == "hello_world"


class TestBuildSuccessResponse:
    def test_returns_json_response(self):
        from app.routers.v1._helpers import build_success_response
        request = MagicMock()
        request.state.request_id = "req-1"
        resp = build_success_response(request, {"key": "val"})
        assert resp.status_code == 200
        body = resp.body.decode()
        assert "key" in body
        assert "val" in body

    def test_custom_status_code(self):
        from app.routers.v1._helpers import build_success_response
        request = MagicMock()
        request.state.request_id = "req-1"
        resp = build_success_response(request, None, status_code=201)
        assert resp.status_code == 201

    def test_includes_request_id(self):
        from app.routers.v1._helpers import build_success_response
        request = MagicMock()
        request.state.request_id = "req-123"
        resp = build_success_response(request, "data")
        body = resp.body.decode()
        assert "req-123" in body


class TestBuildErrorResponse:
    def test_returns_error_response(self):
        from app.routers.v1._helpers import build_error_response
        request = MagicMock()
        request.state.request_id = "req-1"
        resp = build_error_response(request, status_code=404, code="NOT_FOUND", message="Not found")
        assert resp.status_code == 404
        body = resp.body.decode()
        assert "NOT_FOUND" in body
        assert "Not found" in body

    def test_with_details(self):
        from app.routers.v1._helpers import build_error_response
        request = MagicMock()
        request.state.request_id = "req-1"
        resp = build_error_response(request, status_code=400, code="BAD", message="bad",
                                      details={"field": "error"})
        assert resp.status_code == 400
        body = resp.body.decode()
        assert "field" in body


class TestHttpExceptionToResponse:
    def test_converts_http_exception(self):
        from app.routers.v1._helpers import http_exception_to_response
        request = MagicMock()
        request.state.request_id = "req-1"
        exc = HTTPException(404, "Not found")
        resp = http_exception_to_response(request, exc)
        assert resp.status_code == 404
        body = resp.body.decode()
        assert "NOT_FOUND" in body

    def test_custom_code_map(self):
        from app.routers.v1._helpers import http_exception_to_response
        request = MagicMock()
        request.state.request_id = "req-1"
        exc = HTTPException(422, "Invalid")
        resp = http_exception_to_response(request, exc, code_map={422: "CUSTOM_CODE"})
        body = resp.body.decode()
        assert "CUSTOM_CODE" in body

    def test_with_detail_as_dict(self):
        from app.routers.v1._helpers import http_exception_to_response
        request = MagicMock()
        request.state.request_id = "req-1"
        exc = HTTPException(400, detail={"field": "error"})
        resp = http_exception_to_response(request, exc)
        body = resp.body.decode()
        assert "field" in body or "error" in body

    def test_default_error_code_fallback(self):
        from app.routers.v1._helpers import http_exception_to_response
        request = MagicMock()
        request.state.request_id = "req-1"
        exc = HTTPException(418, "I'm a teapot")
        resp = http_exception_to_response(request, exc)
        body = resp.body.decode()
        assert "API_ERROR" in body


class TestRecordPersonaKPIs:
    def test_successful_kpi_recording(self):
        with patch("app.middleware.prometheus_metrics.MetricsManager") as MockMM:
            from app.routers.v1._helpers import _record_persona_kpis
            request = MagicMock()
            request.url.path = "/api/v1/documents/upload"
            _record_persona_kpis(request, "test_op", True, 0.5)
            MockMM.record_persona_event.assert_called_once()
            MockMM.record_persona_latency.assert_called_once()

    def test_error_kpi_recording(self):
        with patch("app.middleware.prometheus_metrics.MetricsManager") as MockMM:
            from app.routers.v1._helpers import _record_persona_kpis
            request = MagicMock()
            request.url.path = "/api/v1/generator"
            _record_persona_kpis(request, "test_op", False, 1.0)
            MockMM.record_persona_event.assert_called_once()

    def test_silent_fail_on_exception(self):
        with patch("app.middleware.prometheus_metrics.MetricsManager.record_persona_event", side_effect=Exception("boom")):
            from app.routers.v1._helpers import _record_persona_kpis
            request = MagicMock()
            request.url.path = "/test"
            _record_persona_kpis(request, "test", True, 0.1)


class TestRunEnveloped:
    @pytest.fixture
    def request_mock(self):
        req = MagicMock()
        req.state.request_id = "req-1"
        req.url.path = "/api/v1/test"
        return req

    def test_successful_operation(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        result = run_enveloped(request_mock, AsyncMock(return_value={"ok": True}))
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 200

    def test_success_with_custom_status_code(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        result = run_enveloped(request_mock, AsyncMock(return_value={"ok": True}),
                                success_status_code=201)
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 201

    def test_http_exception_mapped(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        async def failing_op():
            raise HTTPException(404, "Not found")
        result = run_enveloped(request_mock, failing_op, code_map={404: "DOC_NOT_FOUND"})
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 404
        body = resp.body.decode()
        assert "DOC_NOT_FOUND" in body

    def test_http_exception_unmapped(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        async def failing_op():
            raise HTTPException(409, "Conflict")
        result = run_enveloped(request_mock, failing_op)
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 409

    def test_unhandled_exception_returns_500(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        async def crashing_op():
            raise ValueError("Unexpected error")
        result = run_enveloped(request_mock, crashing_op, logger=MagicMock())
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 500
        body = resp.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body

    def test_operation_returns_response_directly(self, request_mock):
        from app.routers.v1._helpers import run_enveloped
        from starlette.responses import JSONResponse
        direct_response = JSONResponse({"direct": True}, status_code=299)
        result = run_enveloped(request_mock, AsyncMock(return_value=direct_response))
        import asyncio
        resp = asyncio.run(result)
        assert resp.status_code == 299
        assert resp is direct_response
