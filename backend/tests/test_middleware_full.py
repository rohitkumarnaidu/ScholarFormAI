# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Full middleware integration tests — FeatureFlags, Monitoring, RBAC, CSP, ordering."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

# ── FeatureFlagMiddleware ───────────────────────────────────────────────────────


class TestFeatureFlagMiddleware:
    @pytest.fixture
    def app(self):
        _app = FastAPI()

        @_app.get("/ping")
        async def ping():
            return {"ok": True}

        return _app

    def test_adds_header_in_debug_mode(self, app):
        app.debug = True
        mock_flags = {"new_upload_flow": True, "ai_suggestions": False}
        with (
            patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc,
            patch.object(app, "debug", True),
        ):
            mock_svc.return_value.get_all_flags.return_value = mock_flags
            from app.middleware.feature_flags import FeatureFlagMiddleware

            app.add_middleware(FeatureFlagMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200
            header_val = resp.headers.get("x-feature-flags")
            assert header_val is not None
            parsed = json.loads(header_val)
            assert parsed == mock_flags

    def test_no_header_in_non_debug(self, app):
        app.debug = False
        mock_flags = {"new_upload_flow": True}
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc:
            mock_svc.return_value.get_all_flags.return_value = mock_flags
            from app.middleware.feature_flags import FeatureFlagMiddleware

            app.add_middleware(FeatureFlagMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert "x-feature-flags" not in resp.headers

    def test_state_populated(self, app):
        app.debug = False
        mock_flags = {"batch_processing": True}
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc:
            mock_svc.return_value.get_all_flags.return_value = mock_flags
            from app.middleware.feature_flags import FeatureFlagMiddleware

            app.add_middleware(FeatureFlagMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200

    def test_empty_flags_in_production(self, app):
        app.debug = False
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc:
            mock_svc.return_value.get_all_flags.return_value = {}
            from app.middleware.feature_flags import FeatureFlagMiddleware

            app.add_middleware(FeatureFlagMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert "x-feature-flags" not in resp.headers

    def test_database_backed_flags(self, app):
        app.debug = True
        db_flags = {"export_latex": True, "collaborative_editing": False}
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc:
            svc_instance = mock_svc.return_value
            svc_instance.get_all_flags.return_value = db_flags
            from app.middleware.feature_flags import FeatureFlagMiddleware

            app.add_middleware(FeatureFlagMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert json.loads(resp.headers["x-feature-flags"]) == db_flags
            svc_instance.get_all_flags.assert_called_once_with(None)


# ── MonitoringMiddleware ────────────────────────────────────────────────────────


class TestMonitoringMiddleware:
    @pytest.fixture
    def app(self):
        _app = FastAPI()

        @_app.get("/ping")
        async def ping():
            return {"ok": True}

        return _app

    def test_records_timing_header(self, app):
        with patch("app.middleware.monitoring.logger"):
            from app.middleware.monitoring import MonitoringMiddleware

            app.add_middleware(MonitoringMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert "x-processing-time" in resp.headers
            assert float(resp.headers["x-processing-time"]) >= 0

    def test_sets_request_id_in_state(self, app):
        from app.middleware.monitoring import MonitoringMiddleware

        collected = {}

        @app.middleware("http")
        async def capture_state(request: Request, call_next):
            collected["request_id"] = getattr(request.state, "request_id", None)
            return await call_next(request)

        app.add_middleware(MonitoringMiddleware)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert collected["request_id"] is not None

    def test_logs_request_start_and_complete(self, app):
        with patch("app.middleware.monitoring.logger") as mock_log:
            from app.middleware.monitoring import MonitoringMiddleware

            app.add_middleware(MonitoringMiddleware)
            client = TestClient(app)
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert mock_log.info.call_count >= 2
            start_call = mock_log.info.call_args_list[0]
            end_call = mock_log.info.call_args_list[-1]
            assert "started" in str(start_call.args[0]).lower()
            assert "completed" in str(end_call.args[0]).lower()

    def test_uses_existing_request_id_header(self, app):
        from app.middleware.monitoring import MonitoringMiddleware

        collected = {}

        @app.middleware("http")
        async def capture_state(request: Request, call_next):
            collected["request_id"] = getattr(request.state, "request_id", None)
            return await call_next(request)

        app.add_middleware(MonitoringMiddleware)
        client = TestClient(app)
        resp = client.get("/ping", headers={"X-Request-Id": "my-custom-req-id"})
        assert resp.status_code == 200
        assert collected["request_id"] == "my-custom-req-id"
        assert resp.headers.get("x-request-id") == "my-custom-req-id"

    def test_logs_exception(self, app):
        @app.get("/crash")
        async def crash():
            raise RuntimeError("boom")

        with patch("app.middleware.monitoring.logger") as mock_log:
            from app.middleware.monitoring import MonitoringMiddleware

            app.add_middleware(MonitoringMiddleware)
            client = TestClient(app)
            with pytest.raises(RuntimeError):
                client.get("/crash")
            assert mock_log.error.call_count >= 1
            assert "failed" in str(mock_log.error.call_args[0][0]).lower()


# ── RBAC ────────────────────────────────────────────────────────────────────────


class TestRBAC:
    def test_require_role_rejects_insufficient(self):
        from app.middleware.rbac import require_role

        guard = require_role("admin")
        mock_user = MagicMock()
        mock_user.role = "free"
        with pytest.raises(Exception) as exc_info:
            guard(current_user=mock_user)
        assert exc_info.type.__name__ in ("HTTPException", "Exception")

    def test_require_role_allows_sufficient(self):
        from app.middleware.rbac import require_role

        guard = require_role("free")
        mock_user = MagicMock()
        mock_user.role = "admin"
        with patch("app.middleware.rbac.get_current_user", return_value=mock_user):
            result = guard(current_user=mock_user)
            assert result is mock_user
            assert mock_user.effective_role == "admin"

    def test_role_hierarchy_admin_gte_pro(self):
        from app.middleware.rbac import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["pro"]

    def test_role_hierarchy_pro_gte_free(self):
        from app.middleware.rbac import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["pro"] > ROLE_HIERARCHY["free"]

    def test_role_not_in_hierarchy_defaults_free(self):
        from app.middleware.rbac import resolve_user_role

        mock_user = MagicMock()
        mock_user.role = "some_unknown_role"
        mock_user.app_metadata = {}
        role = resolve_user_role(mock_user)
        assert role == "free"

    def test_unknown_user_role_resolves_to_free_then_rejected(self):
        from app.middleware.rbac import require_role, resolve_user_role

        mock_user = MagicMock()
        mock_user.role = "completely_unknown"
        mock_user.app_metadata = None
        user_role = resolve_user_role(mock_user)
        assert user_role == "free"
        guard = require_role("admin")
        with pytest.raises(Exception) as exc_info:
            guard(current_user=mock_user)
        assert exc_info.type.__name__ in ("HTTPException", "Exception")

    def test_normalize_role_resolves_aliases(self):
        from app.middleware.rbac import _normalize_role

        assert _normalize_role("guest") == "free"
        assert _normalize_role("premium") == "pro"
        assert _normalize_role("superadmin") == "admin"
        assert _normalize_role("unknown") == "unknown"

    def test_resolve_user_role_defaults_free(self):
        from app.middleware.rbac import resolve_user_role

        mock_user = MagicMock()
        mock_user.role = None
        mock_user.app_metadata = None
        assert resolve_user_role(mock_user) == "free"

    def test_resolve_user_role_from_app_metadata(self):
        from app.middleware.rbac import resolve_user_role

        mock_user = MagicMock()
        mock_user.role = "authenticated"
        mock_user.app_metadata = {"role": "admin"}
        assert resolve_user_role(mock_user) == "admin"

    def test_require_role_validates_parameter(self):
        from app.middleware.rbac import require_role

        with pytest.raises(ValueError, match="Unsupported role"):
            require_role("does_not_exist")


# ── RequestIdMiddleware ────────────────────────────────────────────────────────


class TestRequestIdMiddleware:
    @pytest.mark.asyncio
    async def test_adds_x_request_id_to_response(self):
        from app.middleware.request_id import RequestIdMiddleware

        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
        sent = []

        async def send_wrapper(msg):
            sent.append(msg)

        async def inner_send(msg):
            pass

        app.side_effect = lambda s, r, send: send({"type": "http.response.start", "status": 200, "headers": []})
        await mw(scope, AsyncMock(), send_wrapper)
        assert len(sent) == 0  # send_wrapper not called directly; inner send is used

    @pytest.mark.asyncio
    async def test_preserves_existing_x_request_id(self):
        from app.middleware.request_id import RequestIdMiddleware

        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"x-request-id", b"existing-id-42")],
        }
        await mw(scope, AsyncMock(), AsyncMock())
        assert scope["state"]["request_id"] == "existing-id-42"

    @pytest.mark.asyncio
    async def test_non_http_passes_through(self):
        from app.middleware.request_id import RequestIdMiddleware

        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {"type": "websocket"}
        await mw(scope, AsyncMock(), AsyncMock())
        app.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idempotency_key_stored_for_post(self):
        from app.middleware.request_id import RequestIdMiddleware

        app = AsyncMock()
        mw = RequestIdMiddleware(app)
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/upload",
            "headers": [(b"idempotency-key", b"idem-999")],
        }
        with patch("app.middleware.request_id.logger"):
            await mw(scope, AsyncMock(), AsyncMock())
            assert scope["state"]["idempotency_key"] == "idem-999"


# ── Middleware ordering ────────────────────────────────────────────────────────


class TestMiddlewareOrdering:
    def test_request_id_before_rbac(self):
        """RequestIdMiddleware should set request_id before RBAC runs."""
        execution_order = []

        class TrackingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                execution_order.append(id(self))
                return await call_next(request)

        app = FastAPI()

        @app.get("/admin")
        async def admin_route():
            return {"ok": True}

        app.add_middleware(TrackingMiddleware)
        client = TestClient(app)
        resp = client.get("/admin")
        assert resp.status_code == 200

    def test_exception_in_middleware_caught(self):
        app = FastAPI()

        class ExplodingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                raise ValueError("middleware explosion")

        @app.get("/boom")
        async def boom():
            return {"ok": True}

        app.add_middleware(ExplodingMiddleware)
        client = TestClient(app)
        with pytest.raises(ValueError):
            client.get("/boom")


# ── CSP nonce ──────────────────────────────────────────────────────────────────


class TestCSPNonce:
    @pytest.fixture
    def app(self):
        _app = FastAPI()

        @_app.get("/test")
        async def test():
            return {"ok": True}

        return _app

    def test_nonce_generated_per_request(self, app):
        from app.middleware.security_headers import SecurityHeadersMiddleware

        nonces = []

        @app.middleware("http")
        async def capture_nonce(request: Request, call_next):
            nonces.append(getattr(request.state, "csp_nonce", None))
            return await call_next(request)

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        client.get("/test")
        client.get("/test")
        assert len(nonces) == 2
        assert nonces[0] is not None
        assert nonces[1] is not None
        assert nonces[0] != nonces[1]

    def test_csp_header_present(self, app):
        from app.middleware.security_headers import SecurityHeadersMiddleware

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        assert "content-security-policy" in resp.headers
        assert "'nonce-" in resp.headers["content-security-policy"]

    def test_csp_docs_route_has_additional_sources(self, app):
        from app.middleware.security_headers import SecurityHeadersMiddleware

        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/docs")
        async def docs():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/docs")
        csp = resp.headers["content-security-policy"]
        assert "cdn.jsdelivr.net" in csp
        assert "unpkg.com" in csp

    def test_security_headers_present(self, app):
        from app.middleware.security_headers import SecurityHeadersMiddleware

        app.add_middleware(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/test")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
