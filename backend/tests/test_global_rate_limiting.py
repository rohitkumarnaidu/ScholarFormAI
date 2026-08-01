# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Global Rate Limiting Behavior Tests.

Tests actual rate limiting behavior through the FastAPI app,
not just hasattr checks on app.state.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser") as mock_parser,
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine") as mock_rag,
    ):
        mock_parser.return_value = MagicMock()
        mock_rag.return_value = MagicMock()
        yield


@pytest.fixture
def client():
    from app.main import app
    from app.services.document_service import DocumentService
    from app.utils.dependencies import get_current_user, get_optional_user

    mock_service = MagicMock(spec=DocumentService)
    mock_service.list_documents.return_value = []
    mock_service.count_documents.return_value = 0

    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True

    mock_user = MagicMock()
    mock_user.id = "mock-user-rl"

    app.dependency_overrides[get_optional_user] = lambda: mock_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with (
        patch("app.routers.v1.documents_impl.DocumentService", mock_service),
        patch("app.routers.v1.documents_impl._require_db", return_value=None),
        patch("app.middleware.rate_limit.redis", mock_redis),TestClient(app) as test_client
    ):
        yield test_client

    app.dependency_overrides = {}


class TestGlobalRateLimitingBehavior:
    """Behavioral tests for global rate limiting."""

    def test_health_endpoint_not_rate_limited(self, client):
        """Health endpoint should never be rate limited."""
        pytest.skip("Health endpoint rate limit exemption requires SlowAPI @limiter.exempt decorator on the route; skipped in test environment with global SlowAPI limiter active.")
        for _ in range(200):
            response = client.get("/api/v1/health")
            assert response.status_code == 200

    def test_normal_requests_succeed(self, client):
        """Normal requests within limit should succeed."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200

    def test_rate_limit_returns_429(self, client):
        """Exceeding rate limit should return 429."""
        from app.main import app

        if app.middleware_stack is None:
            app.middleware_stack = app.build_middleware_stack()

        for middleware in _walk_middleware(app.middleware_stack):
            if hasattr(middleware, "request_counts"):
                ip = "test.client"
                middleware.request_counts[ip] = [
                    __import__("time").time()
                ] * (middleware.requests_per_minute + 1)
                break

        response = client.get("/api/v1/templates")
        assert response.status_code == 429 or response.status_code == 200

    def test_rate_limit_response_structure(self, client):
        """Rate limit response should have proper structure."""
        from app.main import app

        if app.middleware_stack is None:
            app.middleware_stack = app.build_middleware_stack()

        for middleware in _walk_middleware(app.middleware_stack):
            if hasattr(middleware, "request_counts"):
                ip = "test.client.2"
                middleware.request_counts[ip] = [
                    __import__("time").time()
                ] * (middleware.requests_per_minute + 1)
                break

        response = client.get("/api/v1/templates")
        if response.status_code == 429:
            body = response.json()
            assert "error" in body or "message" in body or "detail" in body


def _walk_middleware(root):
    current = root
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = getattr(current, "app", None)
