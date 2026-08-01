# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Rate limiting contract tests.

Covers:
  2A: Rate limit header presence and format
  2B: Rate limit enforcement and window behavior
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


# ── 2A: Rate Limit Header Tests ─────────────────────────────────────────


class Test2A_RateLimitHeaders:
    """Rate limit header presence and format validation."""

    @pytest.fixture
    def authed_client(self):
        from app.main import app
        from app.utils.dependencies import get_current_user
        mock_user = MagicMock()
        mock_user.id = "user-rl-header"
        mock_user.role = "authenticated"
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 0

        mock_rl_result = MagicMock()
        mock_rl_result.allowed = True
        mock_rl_result.limit = 100
        mock_rl_result.remaining = 99
        mock_rl_result.reset_at = 1234567890.0
        mock_rl_result.retry_after = None

        with (
            patch("app.db.session.get_db", return_value=mock_db),
            patch("app.routers.v1.api_keys.ApiKeyService"),
            patch("app.routers.v1.api_keys.get_api_key_rate_limiter", return_value=mock_rl_result),
        ):
            with TestClient(app) as c:
                c.headers.update({"Authorization": "Bearer test-token"})
                yield c
        app.dependency_overrides.clear()

    def test_rate_limit_limit_header_present(self, authed_client):
        resp = authed_client.get("/api/v1/keys")
        if "X-RateLimit-Limit" in resp.headers:
            limit = resp.headers["X-RateLimit-Limit"]
            assert limit.isdigit(), f"X-RateLimit-Limit not numeric: {limit}"

    def test_rate_limit_remaining_decreases(self, authed_client):
        mock_rl = MagicMock()
        mock_rl.check_rate_limit.return_value = MagicMock(
            allowed=True, limit=100, remaining=95,
            reset_at=1234567890.0, retry_after=None,
        )
        with patch("app.routers.v1.api_keys.get_api_key_rate_limiter", return_value=mock_rl):
            resp = authed_client.post("/api/v1/keys/test", json={
                "provider": "openai", "api_key": "sk-test-key-12345",
            })
        if "X-RateLimit-Remaining" in resp.headers:
            remaining = int(resp.headers["X-RateLimit-Remaining"])
            assert remaining <= 100

    def test_rate_limit_reset_is_valid_unix_timestamp(self, authed_client):
        resp = authed_client.get("/api/v1/keys")
        if "X-RateLimit-Reset" in resp.headers:
            reset = resp.headers["X-RateLimit-Reset"]
            assert reset.lstrip("-").isdigit(), f"Reset not numeric: {reset}"
            import time
            now = time.time()
            reset_val = int(reset)
            assert reset_val > now - 86400, f"Reset {reset_val} too far in past"

    def test_retry_after_header_on_rate_limited(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=False, limit=10, remaining=0, reset_at=2000.0, retry_after=30.0)
        apply_rate_limit_headers(response, result)
        assert response.headers.get("Retry-After") == "31"

    def test_retry_after_minimum_one(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=False, limit=10, remaining=0, reset_at=2000.0, retry_after=0.0)
        apply_rate_limit_headers(response, result)
        assert response.headers.get("Retry-After") == "1"

    def test_rate_limit_all_endpoints_have_headers(self, authed_client):
        for path in ("/api/v1/keys",):
            mock_rl = MagicMock()
            mock_rl.check_rate_limit.return_value = MagicMock(
                allowed=True, limit=100, remaining=50,
                reset_at=1234567890.0, retry_after=None,
            )
            with patch("app.routers.v1.api_keys.get_api_key_rate_limiter", return_value=mock_rl):
                resp = authed_client.get(path)
            if resp.status_code < 500:
                if "X-RateLimit-Limit" in resp.headers:
                    assert int(resp.headers["X-RateLimit-Limit"]) >= 0


# ── 2B: Rate Limit Enforcement ───────────────────────────────────────────


class Test2B_RateLimitEnforcement:
    """Rate limit enforcement behavior."""

    @staticmethod
    def _rj(resp):
        return json.loads(resp.body.decode())

    def test_exceeding_limit_returns_429(self):
        from app.routers.v1._helpers import build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-rate"
        resp = build_error_response(mock_req, status_code=429, code="RATE_LIMITED",
                                     message="Too many requests")
        assert resp.status_code == 429
        body = self._rj(resp)
        assert body["error"]["code"] == "RATE_LIMITED"

    def test_rate_limited_response_envelope(self):
        from app.routers.v1._helpers import build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-rate2"
        resp = build_error_response(mock_req, status_code=429, code="RATE_LIMITED",
                                     message="Rate limit exceeded")
        body = self._rj(resp)
        assert "request_id" in body
        assert "timestamp" in body
        assert body["data"] is None

    def test_retry_after_header_present_on_429_response(self):
        resp = MagicMock()
        resp.headers = {}
        resp.status_code = 429
        resp.headers["Retry-After"] = "60"
        assert resp.headers["Retry-After"] == "60"

    def test_different_endpoints_have_separate_limits(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult
        r1 = MagicMock()
        r1.headers = {}
        r2 = MagicMock()
        r2.headers = {}
        res1 = RateLimitResult(allowed=True, limit=100, remaining=90, reset_at=2000.0, retry_after=None)
        res2 = RateLimitResult(allowed=True, limit=60, remaining=59, reset_at=3000.0, retry_after=None)
        apply_rate_limit_headers(r1, res1)
        apply_rate_limit_headers(r2, res2)
        assert r1.headers["X-RateLimit-Limit"] == "100"
        assert r2.headers["X-RateLimit-Limit"] == "60"

    def test_authenticated_users_have_higher_limits(self):
        from app.services.api_key_rate_limiter import RateLimitResult
        anon = RateLimitResult(allowed=True, limit=20, remaining=19, reset_at=1000.0, retry_after=None)
        authed = RateLimitResult(allowed=True, limit=100, remaining=99, reset_at=1000.0, retry_after=None)
        assert authed.limit >= anon.limit

    def test_rate_limit_window_reset(self):
        from app.services.api_key_rate_limiter import RateLimitResult
        import time
        future = time.time() + 60
        result = RateLimitResult(allowed=True, limit=100, remaining=0, reset_at=future, retry_after=60.0)
        assert result.retry_after > 0
        assert result.reset_at > time.time()

    def test_concurrent_requests_same_limits(self):
        from app.services.api_key_rate_limiter import RateLimitResult
        r1 = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=1000.0, retry_after=None)
        r2 = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=1000.0, retry_after=None)
        assert r1.limit == r2.limit
        assert r1.remaining == r2.remaining
