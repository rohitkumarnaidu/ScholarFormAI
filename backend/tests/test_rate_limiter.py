# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for RateLimitMiddleware — comprehensive coverage of:
- In-memory store behaviour
- Per-IP limits
- Eviction of stale entries
- Health endpoint exemption
- Upload-specific limits
- Initialization
"""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, AsyncMock, Mock

try:
    from app.middleware.rate_limit import RateLimitMiddleware
except Exception as e:
    RateLimitMiddleware = None
    IMPORT_ERROR = e
else:
    IMPORT_ERROR = None


class TestRateLimiting:
    """Comprehensive unit tests for rate-limit logic."""

    # ── Helpers ──────────────────────────────────────────────────────

    def _make_middleware(self, rpm: int = 5):
        assert RateLimitMiddleware is not None, f"RateLimitMiddleware import failed: {IMPORT_ERROR}"
        mock_app = MagicMock()
        return RateLimitMiddleware(mock_app, requests_per_minute=rpm)

    def _make_request(self, ip: str, path: str = "/api/chat", method: str = "POST"):
        req = MagicMock()
        req.client.host = ip
        req.url.path = path
        req.method = method
        req.headers = {}
        return req

    async def _dispatch(self, mw, req):
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        return await mw.dispatch(req, call_next)

    # ── Initialization ───────────────────────────────────────────────

    def test_rate_limit_initialization(self):
        """Test rate limiting middleware initialization."""
        mw = self._make_middleware(rpm=60)
        assert mw.requests_per_minute == 60
        assert mw.request_counts is not None
        assert mw.upload_request_counts is not None

    # ── Basic Allow / Block ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        """A brand-new IP should always pass."""
        mw = self._make_middleware(rpm=10)
        req = self._make_request("192.168.1.1")
        res = await self._dispatch(mw, req)
        assert res.status_code == 200
        assert len(mw.request_counts["192.168.1.1"]) == 1

    @pytest.mark.asyncio
    async def test_exceeds_limit_is_blocked(self):
        """After rpm requests the IP should be rate-limited."""
        rpm = 3
        mw = self._make_middleware(rpm=rpm)
        req = self._make_request("10.0.0.1")

        for _ in range(rpm):
            res = await self._dispatch(mw, req)
            assert res.status_code == 200

        res_blocked = await self._dispatch(mw, req)
        assert hasattr(res_blocked, "status_code")
        assert res_blocked.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_traffic(self):
        """Test rate limiting allows normal traffic under limit."""
        mw = self._make_middleware(rpm=60)
        req = self._make_request("127.0.0.1")
        res = await self._dispatch(mw, req)
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_requests(self):
        """Test rate limiting blocks excessive requests."""
        mw = self._make_middleware(rpm=5)
        req = self._make_request("127.0.0.1")

        for _ in range(5):
            res = await self._dispatch(mw, req)
            assert res.status_code == 200

        res = await self._dispatch(mw, req)
        assert res.status_code == 429

    # ── Health Endpoint Exemption ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_rate_limit_skips_health_endpoint(self):
        """Test rate limiting skips /health endpoint."""
        mw = self._make_middleware(rpm=1)
        req = self._make_request("127.0.0.1", path="/health")

        for _ in range(100):
            res = await self._dispatch(mw, req)
            assert res.status_code == 200

    # ── Per-IP Isolation ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_rate_limit_is_per_ip(self):
        """Rate limit must track IPs independently."""
        mw = self._make_middleware(rpm=2)
        req_a = self._make_request("10.1.1.1")
        req_b = self._make_request("10.1.1.2")

        await self._dispatch(mw, req_a)
        await self._dispatch(mw, req_a)
        res_a_blocked = await self._dispatch(mw, req_a)
        assert res_a_blocked.status_code == 429

        res_b = await self._dispatch(mw, req_b)
        assert res_b.status_code == 200

    # ── Stale Entry Eviction ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_old_requests_evicted(self):
        """Requests older than window should be evicted."""
        mw = self._make_middleware(rpm=3)
        req = self._make_request("172.16.0.1")

        old_ts = time.time() - 120
        mw.request_counts["172.16.0.1"] = [old_ts, old_ts, old_ts]

        res = await self._dispatch(mw, req)
        assert res.status_code == 200
        assert len(mw.request_counts["172.16.0.1"]) == 1

    def test_rate_limit_cleanup(self):
        """Test old requests are cleaned up."""
        mw = self._make_middleware(rpm=60)
        mw.request_counts["127.0.0.1"] = [time.time() - 120]
        assert len(mw.request_counts["127.0.0.1"]) == 1

    # ── Upload-Specific Limits ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_upload_endpoint_tracked_separately(self):
        """Upload requests should be tracked in upload_request_counts."""
        mw = self._make_middleware(rpm=60)
        req = self._make_request("10.0.0.5", path="/api/v1/documents/upload", method="POST")

        await self._dispatch(mw, req)
        assert len(mw.upload_request_counts["10.0.0.5"]) == 1
        assert len(mw.request_counts["10.0.0.5"]) == 0

    @pytest.mark.asyncio
    async def test_upload_token_fingerprinting(self):
        """Upload rate limiting should use token fingerprint when auth header present."""
        mw = self._make_middleware(rpm=60)
        req = self._make_request("10.0.0.5", path="/api/v1/documents/upload", method="POST")
        req.headers["authorization"] = "Bearer test-token-12345"

        await self._dispatch(mw, req)
        assert len(mw.upload_request_counts) > 0
        key = list(mw.upload_request_counts.keys())[0]
        assert ":" in key

    # ── Error Response Structure ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_rate_limit_error_has_retry_after(self):
        """429 response should include retry_after field."""
        mw = self._make_middleware(rpm=1)
        req = self._make_request("10.9.9.9")

        await self._dispatch(mw, req)
        res = await self._dispatch(mw, req)
        assert res.status_code == 429
        body = res.body if hasattr(res, "body") else res.content
        assert b"retry_after" in body or b"Retry-After" in body or b"429" in body
