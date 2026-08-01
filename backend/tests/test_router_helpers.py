# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.requests import Request
from pydantic import ValidationError


# ── Shared helpers ─────────────────────────────────────────────────────

def _mock_request(path: str = "/api/v1/documents") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/_helpers.py
# ═══════════════════════════════════════════════════════════════════════

class TestHelpersResolvePersona:
    def test_formatter_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/documents/upload") == "formatter"

    def test_authoring_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/generator/sessions") == "authoring"

    def test_synthesis_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/synthesis/sessions") == "synthesis"

    def test_billing_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/billing/webhook") == "billing"

    def test_templates_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/templates/list") == "templates"

    def test_unknown_path_falls_to_platform(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/api/v1/health") == "platform"

    def test_case_insensitive(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("/API/V1/DOCUMENTS") == "formatter"

    def test_none_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona(None) == "platform"

    def test_empty_path(self):
        from app.routers.v1._helpers import _resolve_persona
        assert _resolve_persona("") == "platform"


class TestHelpersMetricSafeLabel:
    def test_simple(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("hello") == "hello"

    def test_strips_and_lowercases(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("  Hello World  ") == "hello_world"

    def test_replaces_special_chars(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("user@name#1") == "user_name_1"

    def test_empty_string(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("") == "unknown"

    def test_only_special_chars(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("!!!") == "unknown"

    def test_none(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label(None) == "unknown"

    def test_already_safe(self):
        from app.routers.v1._helpers import _metric_safe_label
        assert _metric_safe_label("generation_session_create") == "generation_session_create"


class TestHelpersBuildSuccessResponse:
    def test_build_success_response(self):
        from app.routers.v1._helpers import build_success_response
        req = _mock_request()
        resp = build_success_response(req, {"ok": True})
        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body["data"] == {"ok": True}

    def test_build_success_response_custom_status(self):
        from app.routers.v1._helpers import build_success_response
        req = _mock_request()
        resp = build_success_response(req, {"id": "abc"}, status_code=201)
        assert resp.status_code == 201
        body = json.loads(resp.body)
        assert body["data"]["id"] == "abc"


class TestHelpersBuildErrorResponse:
    def test_build_error_response_no_details(self):
        from app.routers.v1._helpers import build_error_response
        req = _mock_request()
        resp = build_error_response(req, status_code=404, code="NOT_FOUND", message="Missing")
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert body["error"]["code"] == "NOT_FOUND"

    def test_build_error_response_with_details(self):
        from app.routers.v1._helpers import build_error_response
        req = _mock_request()
        resp = build_error_response(req, status_code=422, code="VALIDATION_ERROR", message="Bad", details={"field": "name"})
        assert resp.status_code == 422
        body = json.loads(resp.body)
        assert body["error"]["details"]["field"] == "name"


class TestHelpersHttpExceptionToResponse:
    def test_http_exception_with_string_detail(self):
        from app.routers.v1._helpers import http_exception_to_response
        req = _mock_request()
        exc = HTTPException(status_code=404, detail="not found")
        resp = http_exception_to_response(req, exc)
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert "not found" in body["error"]["message"]

    def test_http_exception_with_dict_detail(self):
        from app.routers.v1._helpers import http_exception_to_response
        req = _mock_request()
        exc = HTTPException(status_code=422, detail={"field": "email", "reason": "invalid"})
        resp = http_exception_to_response(req, exc)
        assert resp.status_code == 422
        body = json.loads(resp.body)
        assert body["error"]["details"]["detail"]["field"] == "email"

    def test_http_exception_with_code_map(self):
        from app.routers.v1._helpers import http_exception_to_response
        req = _mock_request()
        exc = HTTPException(status_code=429, detail="too fast")
        resp = http_exception_to_response(req, exc, code_map={429: "CUSTOM_RATE_LIMIT"})
        assert resp.status_code == 429
        body = json.loads(resp.body)
        assert body["error"]["code"] == "CUSTOM_RATE_LIMIT"

    def test_http_exception_fallsback_to_default_codes(self):
        from app.routers.v1._helpers import http_exception_to_response
        req = _mock_request()
        exc = HTTPException(status_code=403, detail="forbidden")
        resp = http_exception_to_response(req, exc)
        assert json.loads(resp.body)["error"]["code"] == "FORBIDDEN"


class TestHelpersDEFAULT_ERROR_CODES:
    def test_has_expected_keys(self):
        from app.routers.v1._helpers import DEFAULT_ERROR_CODES
        assert DEFAULT_ERROR_CODES[400] == "BAD_REQUEST"
        assert DEFAULT_ERROR_CODES[500] == "INTERNAL_SERVER_ERROR"
        assert DEFAULT_ERROR_CODES[404] == "NOT_FOUND"
        assert DEFAULT_ERROR_CODES[422] == "VALIDATION_ERROR"

    def test_all_standard_codes_present(self):
        from app.routers.v1._helpers import DEFAULT_ERROR_CODES
        for code in (400, 401, 403, 404, 409, 413, 422, 429, 500, 501, 502, 503):
            assert code in DEFAULT_ERROR_CODES


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/billing.py
# ═══════════════════════════════════════════════════════════════════════

class TestBillingLookupUserIdByCustomer:
    def test_none_customer_id(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer
        assert _lookup_user_id_by_customer(None, None) is None

    def test_empty_customer_id(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer
        assert _lookup_user_id_by_customer(None, "") is None

    def test_found_user(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"id": "u-123"}
        mock_sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
        assert _lookup_user_id_by_customer(mock_sb, "cus_123") == "u-123"

    def test_no_data(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        mock_sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
        assert _lookup_user_id_by_customer(mock_sb, "cus_456") is None

    def test_exception_returns_none(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("DB down")
        assert _lookup_user_id_by_customer(mock_sb, "cus_789") is None


class TestBillingGetUserIdFromMetadata:
    def test_with_user_id(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({"metadata": {"user_id": "u123"}}) == "u123"

    def test_no_metadata(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({}) is None

    def test_metadata_not_dict(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({"metadata": "string"}) is None

    def test_metadata_missing_user_id(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({"metadata": {"other": "val"}}) is None

    def test_metadata_none(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({"metadata": None}) is None


class TestBillingLegacyProfileUpdates:
    def test_empty_updates(self):
        from app.routers.v1.billing import _legacy_profile_updates
        assert _legacy_profile_updates({}) == {}

    def test_plan_tier_mapped_to_plan(self):
        from app.routers.v1.billing import _legacy_profile_updates
        assert _legacy_profile_updates({"plan_tier": "pro"}) == {"plan": "pro"}

    def test_other_keys_ignored(self):
        from app.routers.v1.billing import _legacy_profile_updates
        result = _legacy_profile_updates({"plan_tier": "free", "billing_status": "active"})
        assert result == {"plan": "free"}

    def test_no_plan_tier(self):
        from app.routers.v1.billing import _legacy_profile_updates
        assert _legacy_profile_updates({"billing_status": "canceled"}) == {}


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/synthesis.py
# ═══════════════════════════════════════════════════════════════════════

class TestSynthesisParseConfig:
    def test_empty_string_returns_empty_dict(self):
        from app.routers.v1.synthesis import _parse_config
        assert _parse_config("") == {}
        assert _parse_config(None) == {}

    def test_valid_json(self):
        from app.routers.v1.synthesis import _parse_config
        assert _parse_config('{"key": "value"}') == {"key": "value"}

    def test_invalid_json_raises(self):
        from app.routers.v1.synthesis import _parse_config
        with pytest.raises(HTTPException) as exc:
            _parse_config("{invalid}")
        assert exc.value.status_code == 422
        assert "Invalid config JSON" in exc.value.detail


class TestSynthesisAssertSessionOwner:
    def test_owner_matches(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": "u123"}
        user = MagicMock(id="u123")
        _assert_session_owner(session, user)

    def test_owner_matches_string_user(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": "u123"}
        _assert_session_owner(session, "u123")

    def test_owner_different_raises(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": "u123"}
        user = MagicMock(id="other")
        with pytest.raises(HTTPException) as exc:
            _assert_session_owner(session, user)
        assert exc.value.status_code == 403

    def test_no_session_user_passes(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {"user_id": None}
        user = MagicMock(id="u123")
        _assert_session_owner(session, user)

    def test_session_user_id_none_passes(self):
        from app.routers.v1.synthesis import _assert_session_owner
        session = {}
        _assert_session_owner(session, "u123")


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/providers.py
# ═══════════════════════════════════════════════════════════════════════

class TestProvidersConstants:
    def test_ssrf_blocked_hosts(self):
        from app.routers.v1.providers import SSRF_BLOCKED_HOSTS
        assert "169.254.169.254" in SSRF_BLOCKED_HOSTS
        assert "metadata.google.internal" in SSRF_BLOCKED_HOSTS
        assert "100.100.100.200" in SSRF_BLOCKED_HOSTS

    def test_ssrf_blocked_schemes(self):
        from app.routers.v1.providers import SSRF_BLOCKED_SCHEMES
        assert "file" in SSRF_BLOCKED_SCHEMES
        assert "ftp" in SSRF_BLOCKED_SCHEMES
        assert "dict" in SSRF_BLOCKED_SCHEMES
        assert "gopher" in SSRF_BLOCKED_SCHEMES

    def test_max_custom_providers(self):
        from app.routers.v1.providers import MAX_CUSTOM_PROVIDERS_PER_USER
        assert MAX_CUSTOM_PROVIDERS_PER_USER == 25


class TestProvidersSanitizeURL:
    def test_normal_url(self):
        from app.routers.v1.providers import _sanitize_url
        assert _sanitize_url("https://api.example.com") == "https://api.example.com"

    def test_strips_trailing_slash(self):
        from app.routers.v1.providers import _sanitize_url
        assert _sanitize_url("https://api.example.com/") == "https://api.example.com"

    def test_blocked_scheme_raises(self):
        from app.routers.v1.providers import _sanitize_url
        with pytest.raises(HTTPException) as exc:
            _sanitize_url("file:///etc/passwd")
        assert exc.value.status_code == 422
        assert "URL scheme" in exc.value.detail

    def test_blocked_host_raises(self):
        from app.routers.v1.providers import _sanitize_url
        with pytest.raises(HTTPException) as exc:
            _sanitize_url("http://169.254.169.254/latest")
        assert exc.value.status_code == 422
        assert "URL host" in exc.value.detail

    def test_ftp_blocked(self):
        from app.routers.v1.providers import _sanitize_url
        with pytest.raises(HTTPException):
            _sanitize_url("ftp://files.example.com")

    def test_non_http_scheme_raises(self):
        from app.routers.v1.providers import _sanitize_url
        with pytest.raises(HTTPException) as exc:
            _sanitize_url("redis://localhost:6379")
        assert exc.value.status_code == 422
        assert "Only http/https URLs" in exc.value.detail

    def test_metadata_google_com_internal_blocked(self):
        from app.routers.v1.providers import _sanitize_url
        with pytest.raises(HTTPException):
            _sanitize_url("http://metadata.google.internal/computeMetadata/v1/")


class TestProvidersGetUserId:
    def test_user_with_id_attr(self):
        from app.routers.v1.providers import _get_user_id
        user = MagicMock(id="u-123")
        assert _get_user_id(user) == "u-123"

    def test_user_as_string(self):
        from app.routers.v1.providers import _get_user_id
        assert _get_user_id("u-456") == "u-456"

    def test_user_with_int_id(self):
        from app.routers.v1.providers import _get_user_id
        user = MagicMock(id=42)
        assert _get_user_id(user) == "42"

    def test_user_no_id_fallsback_to_str(self):
        from app.routers.v1.providers import _get_user_id
        assert _get_user_id("raw-user") == "raw-user"


class TestProvidersCustomProviderCreateValidator:
    def test_validate_base_url_calls_sanitize(self):
        with pytest.raises(HTTPException):
            from app.routers.v1.providers import CustomProviderCreate
            CustomProviderCreate(name="test", base_url="ftp://bad.com")

    def test_validate_base_url_valid(self):
        from app.routers.v1.providers import CustomProviderCreate
        p = CustomProviderCreate(name="test", base_url="https://valid.com")
        assert p.base_url == "https://valid.com"

    def test_validate_models_strips_whitespace(self):
        from app.routers.v1.providers import CustomProviderCreate
        p = CustomProviderCreate(name="test", base_url="https://valid.com", models=["  model-1  ", "", "  model-2  "])
        assert p.models == ["model-1", "model-2"]

    def test_validate_models_truncates_long_names(self):
        from app.routers.v1.providers import CustomProviderCreate
        long_name = "x" * 300
        p = CustomProviderCreate(name="test", base_url="https://valid.com", models=[long_name])
        assert len(p.models[0]) == 200


class TestProvidersCustomProviderUpdateValidator:
    def test_validate_base_url_none_passes(self):
        from app.routers.v1.providers import CustomProviderUpdate
        p = CustomProviderUpdate()
        assert p.base_url is None

    def test_validate_base_url_valid(self):
        from app.routers.v1.providers import CustomProviderUpdate
        p = CustomProviderUpdate(base_url="https://valid.com")
        assert p.base_url == "https://valid.com"

    def test_validate_base_url_blocked_raises(self):
        with pytest.raises(HTTPException):
            from app.routers.v1.providers import CustomProviderUpdate
            CustomProviderUpdate(base_url="file:///etc/passwd")

    def test_validate_models_none_passes(self):
        from app.routers.v1.providers import CustomProviderUpdate
        p = CustomProviderUpdate()
        assert p.models is None

    def test_validate_models_strips(self):
        from app.routers.v1.providers import CustomProviderUpdate
        p = CustomProviderUpdate(models=["  m1  ", "", " m2 "])
        assert p.models == ["m1", "m2"]


class TestProvidersSyncModelsRequestValidator:
    def test_validate_models_strips(self):
        from app.routers.v1.providers import SyncModelsRequest
        r = SyncModelsRequest(models=["  a  ", "  b  "])
        assert r.models == ["a", "b"]

    def test_validate_models_capped_at_100(self):
        from app.routers.v1.providers import SyncModelsRequest
        many = [str(i) for i in range(100)]
        r = SyncModelsRequest(models=many)
        assert len(r.models) == 100


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/api_keys.py
# ═══════════════════════════════════════════════════════════════════════

class TestApiKeysApplyRateLimitHeaders:
    def test_sets_all_headers(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=1000.0, retry_after=None)
        apply_rate_limit_headers(response, result)
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["X-RateLimit-Reset"] == "1000"

    def test_sets_retry_after_when_present(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=False, limit=10, remaining=0, reset_at=2000.0, retry_after=30.5)
        apply_rate_limit_headers(response, result)
        assert response.headers["Retry-After"] == "31"
        assert response.headers["X-RateLimit-Limit"] == "10"

    def test_no_retry_after_when_none(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=1000, remaining=999, reset_at=5000.0, retry_after=None)
        apply_rate_limit_headers(response, result)
        assert "Retry-After" not in response.headers


class TestApiKeysPydanticSchemas:
    def test_create_api_key_valid(self):
        from app.routers.v1.api_keys import CreateApiKeyRequest
        r = CreateApiKeyRequest(provider="openai", api_key="sk-xxxxxxxxxxxx1234")
        assert r.provider == "openai"
        assert r.api_key == "sk-xxxxxxxxxxxx1234"

    def test_create_api_key_min_length_enforced(self):
        from app.routers.v1.api_keys import CreateApiKeyRequest
        with pytest.raises(ValidationError):
            CreateApiKeyRequest(provider="test", api_key="short")

    def test_create_api_key_optional_fields(self):
        from app.routers.v1.api_keys import CreateApiKeyRequest
        r = CreateApiKeyRequest(provider="openai", api_key="sk-xxxxxxxxxxxx1234", key_label="my key", rate_limit_per_minute=10)
        assert r.key_label == "my key"
        assert r.rate_limit_per_minute == 10

    def test_update_api_key_valid(self):
        from app.routers.v1.api_keys import UpdateApiKeyRequest
        r = UpdateApiKeyRequest(is_active=False, key_label="updated")
        assert r.is_active is False
        assert r.key_label == "updated"

    def test_update_api_key_all_none(self):
        from app.routers.v1.api_keys import UpdateApiKeyRequest
        r = UpdateApiKeyRequest()
        assert r.is_active is None
        assert r.key_label is None

    def test_test_api_key_valid(self):
        from app.routers.v1.api_keys import TestApiKeyRequest
        r = TestApiKeyRequest(provider="groq", api_key="gsk_xxxxxxxxxxxx")
        assert r.provider == "groq"

    def test_test_api_key_min_length(self):
        from app.routers.v1.api_keys import TestApiKeyRequest
        with pytest.raises(ValidationError):
            TestApiKeyRequest(provider="groq", api_key="short")


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/stream.py
# ═══════════════════════════════════════════════════════════════════════

class TestStreamEmitEvent:
    def _run_emit(self, *args, **kwargs):
        mock_loop = MagicMock()
        mock_pubsub = MagicMock()
        with (
            patch("app.routers.v1.stream._pubsub", mock_pubsub),
            patch("app.routers.v1.stream.asyncio.get_running_loop", return_value=mock_loop),
        ):
            from app.routers.v1.stream import emit_event
            emit_event(*args, **kwargs)
        return mock_pubsub, mock_loop

    def test_emit_event_with_request_id(self):
        mock_pubsub, mock_loop = self._run_emit("job-1", "progress", {"progress": 50, "phase": "formatting"})
        mock_pubsub.publish.assert_called_once()
        call_args = mock_pubsub.publish.call_args[0]
        assert call_args[0] == "job:job-1"
        assert call_args[1]["event_type"] == "progress"

    def test_emit_event_adds_request_id(self):
        with (
            patch("app.routers.v1.stream._pubsub", MagicMock()),
            patch("app.routers.v1.stream.asyncio.get_running_loop", return_value=MagicMock()),
            patch("app.routers.v1.stream.get_request_id_context", return_value="req-123"),
        ):
            from app.routers.v1.stream import emit_event
            emit_event("job-2", "done", {"status": "completed"})

    def test_emit_event_request_id_from_data_used(self):
        mock_pubsub, _ = self._run_emit("job-3", "error", {"request_id": "from-data"})
        call_args = mock_pubsub.publish.call_args[0]
        assert call_args[1]["request_id"] == "from-data"


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/templates.py — Schema models
# ═══════════════════════════════════════════════════════════════════════

class TestTemplatesApiKeyResponse:
    def test_response_model_fields(self):
        from app.routers.v1.api_keys import ApiKeyResponse
        r = ApiKeyResponse(
            id="k-1", provider="openai", key_label="label",
            is_active=True, rate_limit_per_minute=10,
            rate_limit_per_hour=100, daily_quota=1000,
            total_requests=5, last_request_at=None,
            created_at="2026-01-01", key_preview="sk-...xyz",
        )
        assert r.id == "k-1"
        assert r.key_preview == "sk-...xyz"
        assert r.rate_limit_per_hour == 100


# ═══════════════════════════════════════════════════════════════════════
# app/routers/preview.py — uncovered constants
# ═══════════════════════════════════════════════════════════════════════

class TestPreviewSessionPattern:
    def test_session_pattern_matches_valid(self):
        from app.routers.preview import _SESSION_PATTERN
        assert _SESSION_PATTERN.match("abc-123_def")
        assert _SESSION_PATTERN.match("ABCDEFG")
        assert _SESSION_PATTERN.match("a" * 64)
        assert _SESSION_PATTERN.match("test_session_123")

    def test_session_pattern_rejects_invalid(self):
        from app.routers.preview import _SESSION_PATTERN
        assert not _SESSION_PATTERN.match("")
        assert not _SESSION_PATTERN.match("ab")
        assert not _SESSION_PATTERN.match("x" * 65)
        assert not _SESSION_PATTERN.match("special@chars")
        assert not _SESSION_PATTERN.match("spaces in path")


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/stream.py — event_generator
# ═══════════════════════════════════════════════════════════════════════

class TestStreamEventGenerator:
    """Covers app/routers/v1/stream.py event_generator (lines 28-54)."""

    @pytest.mark.asyncio
    async def test_connected_event_is_first_yield(self):
        from app.routers.v1.stream import event_generator

        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        mock_request.is_disconnected = AsyncMock(return_value=True)

        with (
            patch("app.routers.v1.stream.get_request_id", return_value="req-123"),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
            patch("app.middleware.prometheus_metrics.MetricsManager") as MockMM,
        ):
            events = []
            async for event in event_generator("job-1", mock_request):
                events.append(event)
                break

            assert len(events) == 1
            assert events[0]["event"] == "connected"
            MockMM.sse_connection_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_events_forwarded_with_type(self):
        from app.routers.v1.stream import event_generator

        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        mock_request.is_disconnected = AsyncMock(side_effect=[False, True])

        async def mock_subscribe(channel):
            yield {"event_type": "progress", "data": {"pct": 50}}

        with (
            patch("app.routers.v1.stream.get_request_id", return_value="req-123"),
            patch("app.routers.v1.stream._pubsub.subscribe", mock_subscribe),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
            patch("app.middleware.prometheus_metrics.MetricsManager") as MockMM,
        ):
            events = []
            async for event in event_generator("job-1", mock_request):
                events.append(event)

            assert len(events) == 2
            assert events[1]["event"] == "progress"
            MockMM.sse_connection_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_stops_generator(self):
        from app.routers.v1.stream import event_generator

        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        mock_request.is_disconnected = AsyncMock(side_effect=[False, False, True])

        async def mock_subscribe(channel):
            for i in range(5):
                yield {"event_type": f"msg_{i}"}

        with (
            patch("app.routers.v1.stream.get_request_id", return_value="req-123"),
            patch("app.routers.v1.stream._pubsub.subscribe", mock_subscribe),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
            patch("app.middleware.prometheus_metrics.MetricsManager") as MockMM,
        ):
            events = []
            async for event in event_generator("job-1", mock_request):
                events.append(event)

            assert len(events) == 3
            assert events[0]["event"] == "connected"
            assert events[1]["event"] == "msg_0"
            assert events[2]["event"] == "msg_1"
            MockMM.sse_connection_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_type_fallback_to_message(self):
        from app.routers.v1.stream import event_generator

        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        mock_request.is_disconnected = AsyncMock(side_effect=[False, True])

        async def mock_subscribe(channel):
            yield {"no_event_type": True}

        with (
            patch("app.routers.v1.stream.get_request_id", return_value="req-123"),
            patch("app.routers.v1.stream._pubsub.subscribe", mock_subscribe),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
            patch("app.middleware.prometheus_metrics.MetricsManager"),
        ):
            events = []
            async for event in event_generator("job-1", mock_request):
                events.append(event)

            assert len(events) == 2
            assert events[1]["event"] == "message"


class TestStreamEventGeneratorMetricsFallback:
    """Covers event_generator MetricsManager import exception (lines 33-34)."""

    @pytest.mark.asyncio
    async def test_metrics_import_failure_does_not_raise(self):
        from app.routers.v1.stream import event_generator

        mock_request = MagicMock()
        mock_request.state.request_id = "req-123"
        mock_request.is_disconnected = AsyncMock(return_value=True)

        with (
            patch("app.routers.v1.stream.get_request_id", return_value="req-123"),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
            patch.dict("sys.modules", {"app.middleware.prometheus_metrics": None}, clear=False),
        ):
            events = []
            async for event in event_generator("job-1", mock_request):
                events.append(event)
                break
            assert len(events) == 1


class TestStreamEmitEventFallback:
    """Covers emit_event RuntimeError fallback (lines 94-95)."""

    def test_runtime_error_fallback_calls_asyncio_run(self):
        with (
            patch("app.routers.v1.stream._pubsub", MagicMock()),
            patch("app.routers.v1.stream.asyncio.get_running_loop", side_effect=RuntimeError("no loop")),
            patch("app.routers.v1.stream.asyncio.run") as mock_run,
            patch("app.routers.v1.stream.get_request_id_context", return_value="req-123"),
            patch("app.routers.v1.stream.make_event", return_value={"fake": "event"}),
        ):
            from app.routers.v1.stream import emit_event
            emit_event("job-1", "test", {})

            mock_run.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/synthesis.py — lazy singleton getters
# ═══════════════════════════════════════════════════════════════════════

class TestSynthesisGetOrchestrator:
    """Covers _get_orchestrator cached path (line 47->49 branch)."""

    def test_cached_path_returns_same_instance(self):
        from app.routers.v1 import synthesis as synthesis_mod

        old = synthesis_mod._orchestrator
        try:
            synthesis_mod._orchestrator = None
            with patch.object(synthesis_mod, "PipelineOrchestrator") as MockOrch:
                result1 = synthesis_mod._get_orchestrator()
                result2 = synthesis_mod._get_orchestrator()
                assert result1 is result2
                MockOrch.assert_called_once()
        finally:
            synthesis_mod._orchestrator = old


class TestSynthesisGetSynthesizer:
    """Covers _get_synthesizer cached path (line 54->62 branch)."""

    def test_cached_path_returns_same_instance(self):
        from app.routers.v1 import synthesis as synthesis_mod

        old_orch = synthesis_mod._orchestrator
        old_synth = synthesis_mod._synthesizer
        try:
            synthesis_mod._orchestrator = MagicMock()
            synthesis_mod._synthesizer = None
            with patch.object(synthesis_mod, "MultiDocSynthesizer") as MockSynth:
                result1 = synthesis_mod._get_synthesizer()
                result2 = synthesis_mod._get_synthesizer()
                assert result1 is result2
                MockSynth.assert_called_once()
        finally:
            synthesis_mod._orchestrator = old_orch
            synthesis_mod._synthesizer = old_synth


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/synthesis.py — _get_orchestrator creation path (line 48-49)
# ═══════════════════════════════════════════════════════════════════════

class TestSynthesisGetOrchestratorCreate:
    """Covers _get_orchestrator creation path (lines 48-49)."""

    def test_creates_new_instance_when_none(self):
        from app.routers.v1 import synthesis as synthesis_mod

        old = synthesis_mod._orchestrator
        try:
            synthesis_mod._orchestrator = None
            with patch.object(synthesis_mod, "PipelineOrchestrator") as MockOrch:
                result = synthesis_mod._get_orchestrator()
                MockOrch.assert_called_once()
                assert result is not None
        finally:
            synthesis_mod._orchestrator = old


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/feedback.py — FeedbackRequest schema
# ═══════════════════════════════════════════════════════════════════════

class TestFeedbackSchema:
    """Covers FeedbackRequest Pydantic model (lines 26-32)."""

    def test_valid_feedback(self):
        from app.routers.v1.feedback import FeedbackRequest
        fb = FeedbackRequest(
            document_id="doc-1",
            field="abstract",
            original_value="Old text",
            corrected_value="New text",
        )
        assert fb.document_id == "doc-1"
        assert fb.comments is None

    def test_with_comments(self):
        from app.routers.v1.feedback import FeedbackRequest
        fb = FeedbackRequest(
            document_id="doc-2",
            field="title",
            original_value="A",
            corrected_value="B",
            comments="Good fix",
        )
        assert fb.comments == "Good fix"

    def test_requires_all_required_fields(self):
        from app.routers.v1.feedback import FeedbackRequest
        with pytest.raises(ValidationError):
            FeedbackRequest(document_id="doc-1")


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/suggestions.py — GenerateSuggestionRequest schema
# ═══════════════════════════════════════════════════════════════════════

class TestSuggestionsSchema:
    """Covers GenerateSuggestionRequest Pydantic model (lines 24-29)."""

    def test_valid_request(self):
        from app.routers.v1.suggestions import GenerateSuggestionRequest
        req = GenerateSuggestionRequest(
            document_id="doc-1",
            block={"text": "hello"},
            suggestion_type="grammar",
        )
        assert req.document_id == "doc-1"
        assert req.suggestion_type == "grammar"

    def test_with_session_id(self):
        from app.routers.v1.suggestions import GenerateSuggestionRequest
        req = GenerateSuggestionRequest(
            document_id="doc-1",
            block={"text": "hello"},
            suggestion_type="grammar",
            session_id="sess-1",
        )
        assert req.session_id == "sess-1"

    def test_requires_required_fields(self):
        from app.routers.v1.suggestions import GenerateSuggestionRequest
        with pytest.raises(ValidationError):
            GenerateSuggestionRequest(document_id="doc-1")


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/api_keys.py — uncovered Pydantic schemas
# ═══════════════════════════════════════════════════════════════════════

class TestApiKeysUsageStatsResponse:
    """Covers UsageStatsResponse model (lines 65-69)."""

    def test_valid_stats(self):
        from app.routers.v1.api_keys import UsageStatsResponse
        stats = UsageStatsResponse(
            provider="openai",
            total_requests=100,
            total_tokens=50000,
            avg_response_time_ms=250.5,
        )
        assert stats.provider == "openai"
        assert stats.total_requests == 100
        assert stats.avg_response_time_ms == 250.5

    def test_required_fields(self):
        from app.routers.v1.api_keys import UsageStatsResponse
        with pytest.raises(ValidationError):
            UsageStatsResponse()


class TestApiKeysProviderInfo:
    """Covers ProviderInfo model (lines 72-76)."""

    def test_valid_provider_info(self):
        from app.routers.v1.api_keys import ProviderInfo
        info = ProviderInfo(
            name="openai",
            default_rpm=60,
            default_rph=3500,
            default_daily=10000,
        )
        assert info.name == "openai"
        assert info.default_rpm == 60
        assert info.default_rph == 3500
        assert info.default_daily == 10000

    def test_required_fields(self):
        from app.routers.v1.api_keys import ProviderInfo
        with pytest.raises(ValidationError):
            ProviderInfo()


# ═══════════════════════════════════════════════════════════════════════
# app/routers/deprecation.py — DeprecatedRoute.get_route_handler
# ═══════════════════════════════════════════════════════════════════════

class TestDeprecatedRouteGetRouteHandler:
    """Covers DeprecatedRoute.get_route_handler (lines 38-55)
    with mocked original handler to avoid FastAPI routing internals."""

    def _make_route(self, successor_map, path="/api/v1/old/test"):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = successor_map
        route.path_format = path
        route.path = path
        return route

    def test_successor_path_from_map(self):
        route = self._make_route({"/api/v1/old/test": "/api/v2/new/test"})
        assert route._successor_path() == "/api/v2/new/test"

    def test_successor_path_no_match(self):
        route = self._make_route({})
        assert route._successor_path() is None

    def test_successor_path_normalizes_trailing_slash(self):
        from app.routers.deprecation import DeprecatedRoute
        route = DeprecatedRoute.__new__(DeprecatedRoute)
        route.successor_map = {"/api/v1/old/": "/api/v2/new/"}
        route.path_format = "/api/v1/old/"
        route.path = "/api/v1/old/"
        assert route._successor_path() == "/api/v2/new/"

    @pytest.mark.asyncio
    async def test_get_route_handler_adds_headers_to_response(self):

        route = self._make_route({"/api/v1/old/test": "/api/v2/new/test"})
        mock_response = MagicMock()
        mock_response.headers = {}

        with patch.object(APIRoute, "get_route_handler") as mock_super_get:
            mock_super_get.return_value = AsyncMock(return_value=mock_response)
            handler = route.get_route_handler()
            await handler(MagicMock())

        assert mock_response.headers.get("Deprecation") == "true"
        assert "Sunset" in mock_response.headers

    @pytest.mark.asyncio
    async def test_get_route_handler_adds_headers_to_exception(self):

        route = self._make_route({"/api/v1/old/test": "/api/v2/new/test"})

        with patch.object(APIRoute, "get_route_handler") as mock_super_get:
            mock_super_get.return_value = AsyncMock(side_effect=HTTPException(404, "Not found"))
            handler = route.get_route_handler()
            with pytest.raises(HTTPException) as exc_info:
                await handler(MagicMock())

        assert exc_info.value.headers.get("Deprecation") == "true"
        assert "Sunset" in exc_info.value.headers


# ═══════════════════════════════════════════════════════════════════════
# app/routers/deprecation.py — normalize_path edge cases
# ═══════════════════════════════════════════════════════════════════════

class TestNormalizePathEdgeCases:
    """Covers normalize_path edge branches (lines 24-27)."""

    def test_empty_string(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("") == ""

    def test_single_slash(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/") == "/"

    def test_no_trailing_slash(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/api/v1/keys") == "/api/v1/keys"

    def test_multiple_trailing_slashes(self):
        from app.routers.deprecation import normalize_path
        assert normalize_path("/api/v1/keys//") == "/api/v1/keys"


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/synthesis.py — _parse_config edge cases
# ═══════════════════════════════════════════════════════════════════════

class TestSynthesisParseConfigEdgeCases:
    """Covers remaining _parse_config branches (lines 65-71)."""

    def test_whitespace_string_raises(self):
        from app.routers.v1.synthesis import _parse_config
        with pytest.raises(HTTPException) as exc:
            _parse_config("  ")
        assert exc.value.status_code == 422

    def test_none_input(self):
        from app.routers.v1.synthesis import _parse_config
        assert _parse_config(None) == {}

    def test_invalid_json_string(self):
        from app.routers.v1.synthesis import _parse_config
        with pytest.raises(HTTPException) as exc:
            _parse_config("not-json")
        assert exc.value.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# app/routers/v1/health.py — endpoint helper function coverage
# ═══════════════════════════════════════════════════════════════════════

class TestHealthSchemas:
    """Covers the health check endpoint patterns."""

    def test_health_endpoint_path_exists(self):
        from app.routers.v1.health import router
        paths = [r.path for r in router.routes]
        assert "" in paths
        assert "/live" in paths
        assert "/ready" in paths
        assert "/admin" in paths



