# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app


def test_v1_namespace_includes_migrated_router_paths():
    paths = {route.path for route in app.routes}
    expected = {
        "/api/v1/auth/login",
        "/api/v1/auth/signup",
        "/api/v1/feedback/",
        "/api/v1/metrics/health",
        "/api/v1/stream/{jobId}",
        "/api/v1/documents/upload",
        "/api/v1/generator/sessions",
        "/api/v1/templates",
    }
    missing = expected - paths
    assert not missing, f"Missing migrated v1 routes: {sorted(missing)}"
    assert "/api/templates" not in paths
    assert "/api/documents" not in paths


def test_v1_auth_login_uses_envelope(monkeypatch):
    monkeypatch.setattr(
        "app.routers.v1.auth.AuthService.login",
        AsyncMock(return_value={"access_token": "token-123", "token_type": "bearer"}),
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "SafePass1!"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "data" in payload
    assert payload.get("error") is None
    assert payload["data"]["access_token"] == "token-123"
