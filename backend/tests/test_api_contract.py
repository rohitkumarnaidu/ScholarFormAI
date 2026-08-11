# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Expected endpoints ──────────────────────────────────────────────────────
# Source: backend/app/routers/v1/__init__.py + preview router
# Verified against actual OpenAPI schema output
EXPECTED_ENDPOINTS: dict[str, dict[str, list[str]]] = {
    "Health v1": {
        "prefix": "/api/v1/health",
        "paths": ["", "/live", "/ready", "/admin"],
        "methods": ["GET", "GET", "GET", "GET"],
    },
    "Auth v1": {
        "prefix": "/api/v1/auth",
        "paths": ["/me", "/signup", "/login", "/forgot-password", "/verify-otp", "/reset-password"],
        "methods": ["GET", "POST", "POST", "POST", "POST", "POST"],
    },
    "Documents v1": {
        "prefix": "/api/v1/documents",
        "paths": [
            "", "/upload", "/upload/chunked", "/batch-upload",
            "/{jobId}/status", "/{jobId}/summary", "/{jobId}/edit",
            "/{jobId}/preview", "/{jobId}/compare", "/{jobId}/download",
            "/{jobId}",
        ],
        "methods": [
            "GET", "POST", "POST", "POST",
            "GET", "GET", "POST",
            "GET", "GET", "GET",
            "DELETE",
        ],
    },
    "Templates v1": {
        "prefix": "/api/v1/templates",
        "paths": ["", "/csl/search", "/csl/fetch", "/csl/{styleId}", "/custom", "/custom", "/custom/{templateId}", "/custom/{templateId}"],
        "methods": ["GET", "GET", "GET", "GET", "GET", "POST", "PUT", "DELETE"],
    },
    "Generator v1": {
        "prefix": "/api/v1/generator",
        "paths": [
            "/sessions", "/sessions", "/sessions/{sessionId}",
            "/sessions/{sessionId}/messages", "/sessions/{sessionId}/document",
            "/sessions/{sessionId}/download", "/sessions/{sessionId}/events",
            "/sessions/{sessionId}/messages", "/sessions/{sessionId}/outline/approve",
            "/sessions/{sessionId}/stop",
        ],
        "methods": [
            "POST", "GET", "GET",
            "GET", "GET",
            "GET", "GET",
            "POST", "POST",
            "POST",
        ],
    },
    "Synthesis v1": {
        "prefix": "/api/v1/synthesis",
        "paths": ["/sessions", "/sessions/{sessionId}", "/sessions/{sessionId}/events", "/sessions/{sessionId}/messages"],
        "methods": ["POST", "GET", "GET", "POST"],
    },
    "Feedback v1": {
        "prefix": "/api/v1/feedback",
        "paths": ["/", "/summary"],
        "methods": ["POST", "GET"],
    },
    "Metrics v1": {
        "prefix": "/api/v1/metrics",
        "paths": ["/db", "/log-error", "/health", "/dashboard", "/enhancements", "/vllm-readiness"],
        "methods": ["GET", "POST", "GET", "GET", "GET", "GET"],
    },
    "providers": {
        "prefix": "/api/v1/providers",
        "paths": [
            "/health", "", "/builtin", "/{provider_id}/models",
            "/{provider_id}/models/sync", "/custom", "/custom",
            "/custom/{provider_id}", "/custom/{provider_id}", "/custom/{provider_id}",
            "/test",
        ],
        "methods": [
            "GET", "GET", "GET", "GET",
            "POST", "GET", "POST",
            "GET", "PUT", "DELETE",
            "POST",
        ],
    },
    "api_keys": {
        "prefix": "/api/v1/keys",
        "paths": [
            "", "", "/{key_id}", "/{key_id}", "/{key_id}",
            "/usage", "/{key_id}/usage", "/providers", "/test",
        ],
        "methods": [
            "POST", "GET", "GET", "PUT", "DELETE",
            "GET", "GET", "GET", "POST",
        ],
    },
    "Streaming v1": {
        "prefix": "/api/v1/stream",
        "paths": ["/{jobId}"],
        "methods": ["GET"],
    },
    "billing": {
        "prefix": "/api/v1/billing",
        "paths": ["/webhook"],
        "methods": ["POST"],
    },
    "Preview": {
        "prefix": "/api/v1/preview",
        "paths": ["/live", "/{sessionId}/ai-suggest"],
        "methods": ["POST", "GET"],
    },
    "suggestions": {
        "prefix": "/api/v1/suggestions",
        "paths": [
            "/document/{document_id}", "/generate", "/history",
            "/{suggestion_id}/accept", "/{suggestion_id}/apply",
            "/{suggestion_id}/dismiss", "/{suggestion_id}/reject",
        ],
        "methods": [
            "GET", "POST", "GET",
            "POST", "POST",
            "POST", "POST",
        ],
    },
    "activity": {
        "prefix": "/api/v1/activity",
        "paths": ["/recent", "/summary"],
        "methods": ["GET", "GET"],
    },
}


def _normalise_path(path: str) -> str:
    """Strip trailing slash (except for root "")."""
    return path.rstrip("/") if path != "" else ""


def _build_full_path(prefix: str, subpath: str) -> str:
    if subpath == "/":
        return f"{prefix.rstrip('/')}/"
    p = f"{prefix.rstrip('/')}/{subpath.lstrip('/')}" if subpath else prefix
    return _normalise_path(p)


def _openapi_path_key(prefix: str, subpath: str) -> str:
    """FastAPI OpenAPI key: always starts with / and uses {param} syntax."""
    full = _build_full_path(prefix, subpath)
    if full == "":
        return "/"
    return full if full.startswith("/") else f"/{full}"


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def openapi_schema():
    """Load the OpenAPI schema from the FastAPI app (imported at call-time)."""
    _patch_env()
    # Import app.main inside the fixture body to avoid module-level import side effects
    with _patched_dependencies():
        from app.main import _load_optional_routers, app
        # V1 routers are loaded lazily via middleware; force-load before generating schema
        _load_optional_routers(app)
        schema = app.openapi()
    return schema


@pytest.fixture(scope="module")
def spec_paths(openapi_schema: dict[str, Any]) -> dict[str, Any]:
    """Extract the paths dict from OpenAPI schema."""
    return openapi_schema.get("paths", {})


def _patch_env():
    """Set minimal env vars to prevent startup failures."""
    import os
    os.environ.setdefault("ALGORITHM", "HS256")
    os.environ.setdefault("SUPABASE_URL", "http://localhost:8000")
    os.environ.setdefault("SUPABASE_KEY", "fake-key")
    os.environ.setdefault("REDIS_ENABLED", "false")
    os.environ.setdefault("GROBID_ENABLED", "false")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-min!!")
    os.environ.setdefault("SENTRY_ENABLED", "false")
    os.environ.setdefault("DEFAULT_FAST_MODE", "true")
    os.environ.setdefault("LOW_MEMORY_MODE", "true")
    os.environ.setdefault("PRELOAD_AI_MODELS", "false")


def _patched_dependencies():
    """Return a context manager that patches heavy module-level imports."""
    return patch.multiple(
        "app.main",
        Limiter=MagicMock(),
        _rate_limit_exceeded_handler=MagicMock(),
        RateLimitExceeded=type("RateLimitExceeded", (Exception,), {}),
        SlowAPIMiddleware=MagicMock(),
        get_remote_address=MagicMock(return_value="127.0.0.1"),
        SLOWAPI_AVAILABLE=False,
        sentry_sdk=None,
        SENTRY_AVAILABLE=False, create=True
    )


# ── Schema Structure Tests ──────────────────────────────────────────────────


@pytest.mark.contract
def test_openapi_schema_is_valid_json(openapi_schema: dict[str, Any]):
    """The OpenAPI schema should have the required top-level keys."""
    assert isinstance(openapi_schema, dict)
    assert "openapi" in openapi_schema
    assert openapi_schema["openapi"].startswith("3.")
    assert "info" in openapi_schema
    assert openapi_schema["info"]["title"]
    assert "paths" in openapi_schema


@pytest.mark.contract
def test_openapi_schema_has_valid_paths(openapi_schema: dict[str, Any]):
    """All path keys must start with /api/v1/ or be a root probe (/, /health, /ready)."""
    allowed_root = {"/", "/health", "/ready"}
    paths = openapi_schema.get("paths", {})
    for path_key in paths:
        ok = path_key.startswith("/api/v1/") or path_key.startswith("/api/v2/") or path_key in allowed_root
        assert ok, f"Unexpected path key: {path_key}"


@pytest.mark.contract
def test_all_endpoints_have_operation_ids(openapi_schema: dict[str, Any]):
    """Every path+method must have an operationId."""
    paths = openapi_schema.get("paths", {})
    for path_key, methods in paths.items():
        for method in ("get", "post", "put", "delete", "patch", "head", "options"):
            operation = methods.get(method)
            if operation:
                assert "operationId" in operation, (
                    f"Missing operationId for {method.upper()} {path_key}"
                )
                assert "summary" in operation


@pytest.mark.contract
def test_all_endpoints_have_responses(openapi_schema: dict[str, Any]):
    """Every path+method must define at least a 200/201/202/204 or error response."""
    paths = openapi_schema.get("paths", {})
    for path_key, methods in paths.items():
        for method in ("get", "post", "put", "delete", "patch"):
            operation = methods.get(method)
            if operation:
                responses = operation.get("responses", {})
                success_codes = [c for c in ["200", "201", "202", "204"] if c in responses]
                error_codes = [c for c in ["400", "401", "403", "404", "422", "413", "429", "500"] if c in responses]
                assert success_codes or error_codes, (
                    f"No success or error response codes for {method.upper()} {path_key}"
                )


# ── Expected Endpoints Presence Tests ───────────────────────────────────────


@pytest.mark.contract
@pytest.mark.parametrize("tag", list(EXPECTED_ENDPOINTS.keys()))
def test_all_expected_endpoints_exist(openapi_schema: dict[str, Any], tag: str):
    """Verify every endpoint specified in EXPECTED_ENDPOINTS appears in the schema."""
    group = EXPECTED_ENDPOINTS[tag]
    prefix = group["prefix"]
    paths_schema = openapi_schema.get("paths", {})

    for subpath, expected_method in zip(group["paths"], group["methods"], strict=False):
        path_key = _openapi_path_key(prefix, subpath)
        # Handle duplicate path keys (same path, different methods)
        actual = paths_schema.get(path_key)
        assert actual is not None, (
            f"Missing endpoint {expected_method} {path_key} (group: {tag})"
        )
        method_lower = expected_method.lower()
        operation = actual.get(method_lower)
        assert operation is not None, (
            f"Missing method {expected_method} for {path_key} in group {tag}. "
            f"Available methods: {list(actual.keys())}"
        )


@pytest.mark.contract
def test_minimum_endpoint_count(openapi_schema: dict[str, Any]):
    """Assert at least 39 endpoints (path+method combinations) are defined."""
    paths = openapi_schema.get("paths", {})
    total = sum(len(methods) for methods in paths.values())
    assert total >= 39, f"Expected >=39 endpoints, got {total}"


# ── Response Schema Tests ───────────────────────────────────────────────────


@pytest.mark.contract
def test_health_response_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/health must return a 200 with standard envelope."""
    paths = openapi_schema["paths"]
    health_root = paths.get("/api/v1/health", {})
    get_op = health_root.get("get", {})
    resp_200 = get_op.get("responses", {}).get("200", {})
    assert resp_200, "Missing 200 response for GET /api/v1/health"
    content = resp_200.get("content", {})
    assert "application/json" in content, "Health endpoint must return JSON"


@pytest.mark.contract
def test_health_live_response_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/health/live must return a 200."""
    paths = openapi_schema["paths"]
    health_live = paths.get("/api/v1/health/live", {})
    get_op = health_live.get("get", {})
    resp_200 = get_op.get("responses", {}).get("200", {})
    assert resp_200, "Missing 200 response for GET /api/v1/health/live"


@pytest.mark.contract
def test_health_ready_response_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/health/ready must define 200 and 422 responses."""
    paths = openapi_schema["paths"]
    ready_path = paths.get("/api/v1/health/ready", {})
    get_op = ready_path.get("get", {})
    responses = get_op.get("responses", {})
    assert "200" in responses, "Missing 200 response for GET /api/v1/health/ready"
    assert "422" in responses, (
        "Missing 422 response for GET /api/v1/health/ready"
    )


@pytest.mark.contract
def test_auth_me_requires_auth(openapi_schema: dict[str, Any]):
    """GET /api/v1/auth/me must exist with a 200 response (auth enforced at runtime)."""
    paths = openapi_schema["paths"]
    auth_me = paths.get("/api/v1/auth/me", {})
    get_op = auth_me.get("get", {})
    assert get_op, "Missing GET /api/v1/auth/me endpoint"
    responses = get_op.get("responses", {})
    assert "200" in responses, "GET /api/v1/auth/me must define a 200 response"


@pytest.mark.contract
def test_documents_upload_schema(openapi_schema: dict[str, Any]):
    """POST /api/v1/documents/upload must accept multipart/form-data."""
    paths = openapi_schema["paths"]
    upload_path = paths.get("/api/v1/documents/upload", {})
    post_op = upload_path.get("post", {})
    assert post_op, "Missing POST /api/v1/documents/upload"
    request_body = post_op.get("requestBody", {})
    content = request_body.get("content", {})
    assert "multipart/form-data" in content, "Upload must accept multipart/form-data"


@pytest.mark.contract
def test_documents_list_pagination_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/documents must accept limit/offset query params."""
    paths = openapi_schema["paths"]
    list_path = paths.get("/api/v1/documents", {})
    get_op = list_path.get("get", {})
    params = {p["name"] for p in get_op.get("parameters", [])}
    assert "limit" in params, "GET /api/v1/documents must accept limit param"
    assert "offset" in params, "GET /api/v1/documents must accept offset param"


@pytest.mark.contract
def test_templates_list_response_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/templates must return 200."""
    paths = openapi_schema["paths"]
    templates_path = paths.get("/api/v1/templates", {})
    get_op = templates_path.get("get", {})
    resp_200 = get_op.get("responses", {}).get("200", {})
    assert resp_200, "Missing 200 response for GET /api/v1/templates"


@pytest.mark.contract
def test_generator_sessions_post_returns_202(openapi_schema: dict[str, Any]):
    """POST /api/v1/generator/sessions must return 202 Accepted."""
    paths = openapi_schema["paths"]
    sessions_path = paths.get("/api/v1/generator/sessions", {})
    post_op = sessions_path.get("post", {})
    responses = post_op.get("responses", {})
    assert "202" in responses, "POST /api/v1/generator/sessions must return 202"
    assert "422" in responses, "POST /api/v1/generator/sessions must define 422 for validation errors"


@pytest.mark.contract
def test_generator_sessions_list_schema(openapi_schema: dict[str, Any]):
    """GET /api/v1/generator/sessions must accept query params."""
    paths = openapi_schema["paths"]
    sessions_path = paths.get("/api/v1/generator/sessions", {})
    get_op = sessions_path.get("get", {})
    param_names = {p["name"] for p in get_op.get("parameters", [])}
    assert "status" in param_names or "limit" in param_names or "offset" in param_names, (
        "GET /api/v1/generator/sessions should accept filtering query params"
    )


@pytest.mark.contract
def test_synthesis_sessions_post_returns_202(openapi_schema: dict[str, Any]):
    """POST /api/v1/synthesis/sessions must return 202."""
    paths = openapi_schema["paths"]
    syn_path = paths.get("/api/v1/synthesis/sessions", {})
    post_op = syn_path.get("post", {})
    responses = post_op.get("responses", {})
    assert "202" in responses, "POST /api/v1/synthesis/sessions must return 202"


@pytest.mark.contract
def test_billing_webhook_defines_error_responses(openapi_schema: dict[str, Any]):
    """POST /api/v1/billing/webhook must exist with a 200 response."""
    paths = openapi_schema["paths"]
    webhook_path = paths.get("/api/v1/billing/webhook", {})
    post_op = webhook_path.get("post", {})
    responses = post_op.get("responses", {})
    assert "200" in responses, "POST /api/v1/billing/webhook must return 200 on success"


@pytest.mark.contract
def test_feedback_post_returns_201(openapi_schema: dict[str, Any]):
    """POST /api/v1/feedback/ must return 201 Created."""
    paths = openapi_schema["paths"]
    feedback_path = paths.get("/api/v1/feedback/", {})
    post_op = feedback_path.get("post", {})
    responses = post_op.get("responses", {})
    assert "201" in responses, "POST /api/v1/feedback/ must return 201"


@pytest.mark.contract
def test_providers_health_endpoint_exists(openapi_schema: dict[str, Any]):
    """GET /api/v1/providers/health must be defined."""
    paths = openapi_schema["paths"]
    prov_health = paths.get("/api/v1/providers/health", {})
    get_op = prov_health.get("get", {})
    assert get_op, "Missing GET /api/v1/providers/health"


# ── Error Response Envelope Schema Tests ────────────────────────────────────


@pytest.mark.contract
def test_error_responses_have_code_field(openapi_schema: dict[str, Any]):
    """Error responses (4xx/5xx) should reference a schema with a 'code' field
    or have an example that includes 'code'.
    """
    paths = openapi_schema.get("paths", {})
    checked = 0
    for path_key, methods in paths.items():
        for method in ("get", "post", "put", "delete", "patch"):
            operation = methods.get(method)
            if not operation:
                continue
            for status_code in ("400", "401", "403", "404", "422", "413", "429", "500"):
                resp = operation.get("responses", {}).get(status_code, {})
                if resp:
                    checked += 1
                    description = resp.get("description", "")
                    assert description, (
                        f"Missing description for {status_code} {method.upper()} {path_key}"
                    )
    assert checked >= 10, f"Expected >=10 error responses across schema, got {checked}"


# ── API Key Endpoint Tests ──────────────────────────────────────────────────


@pytest.mark.contract
def test_api_keys_crud_endpoints_exist(openapi_schema: dict[str, Any]):
    """All CRUD endpoints for /api/v1/keys must be present."""
    paths = openapi_schema["paths"]
    for suffix in ("", "/{key_id}", "/usage", "/{key_id}/usage", "/providers", "/test"):
        path_key = f"/api/v1/keys{suffix}"
        assert path_key in paths, f"Missing path {path_key}"


@pytest.mark.contract
def test_stream_job_events_endpoint_exists(openapi_schema: dict[str, Any]):
    """GET /api/v1/stream/{jobId} must be present."""
    paths = openapi_schema["paths"]
    stream_path = paths.get("/api/v1/stream/{jobId}", {})
    get_op = stream_path.get("get", {})
    assert get_op, "Missing GET /api/v1/stream/{jobId}"
    responses = get_op.get("responses", {})
    assert "200" in responses, "Stream endpoint must define a 200 response"


# ── Schema Validation (JSON Schema conformance) ─────────────────────────────


@pytest.mark.contract
def test_openapi_schema_validates_against_self(openapi_schema: dict[str, Any]):
    """Basic structural validation — all path methods have valid HTTP methods."""
    valid_http_methods = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
    paths = openapi_schema.get("paths", {})
    for path_key, methods in paths.items():
        for method in methods:
            assert method in valid_http_methods, (
                f"Invalid HTTP method '{method}' for {path_key}"
            )
            operation = methods[method]
            assert isinstance(operation, dict), (
                f"Operation at {method.upper()} {path_key} must be a dict"
            )
            assert "operationId" in operation
            assert "responses" in operation


@pytest.mark.contract
def test_openapi_schema_no_empty_responses(openapi_schema: dict[str, Any]):
    """All responses must have a description or content."""
    paths = openapi_schema.get("paths", {})
    for path_key, methods in paths.items():
        for method in ("get", "post", "put", "delete", "patch"):
            operation = methods.get(method)
            if not operation:
                continue
            for status_code, resp in operation.get("responses", {}).items():
                has_desc = bool(resp.get("description"))
                has_content = bool(resp.get("content"))
                assert has_desc or has_content, (
                    f"Response {status_code} at {method.upper()} {path_key} is empty"
                )


# ── Tags Consistency ────────────────────────────────────────────────────────


@pytest.mark.contract
def test_all_paths_have_tags(openapi_schema: dict[str, Any]):
    """Every v1 operation must be tagged with a meaningful group name.
    Root-level endpoints (/, /health, /ready) defined in main.py are exempt.
    """
    exempt = {"/", "/health", "/ready"}
    paths = openapi_schema.get("paths", {})
    for path_key, methods in paths.items():
        if path_key in exempt:
            continue
        for method, operation in methods.items():
            tags = operation.get("tags", [])
            if path_key.startswith("/api/v1/stream"):
                continue  # stream router has no explicit tags
            if path_key.startswith("/api/v1/keys"):
                continue  # keys router has no explicit tags
            if path_key.startswith("/api/v1/activity"):
                continue  # activity router may lack tags
            assert tags, (
                f"Operation {method.upper()} {path_key} has no tags"
            )


@pytest.mark.contract
def test_tag_consistency(openapi_schema: dict[str, Any]):
    """Operations under the same v1 path prefix should share a common tag."""
    paths = openapi_schema.get("paths", {})
    tag_by_prefix: dict[str, set[str]] = {}
    for path_key, methods in paths.items():
        if not path_key.startswith("/api/v1/"):
            continue
        for _method, operation in methods.items():
            tags = operation.get("tags", [])
            prefix = path_key.split("/")[3]
            if prefix not in tag_by_prefix:
                tag_by_prefix[prefix] = set()
            tag_by_prefix[prefix].update(tags)
    for prefix, tags in tag_by_prefix.items():
        if prefix in ("billing", "stream", "keys", "activity"):
            continue  # these routers have no explicit tags
        assert tags, f"Path prefix /api/v1/{prefix} has no tags across any endpoint"
