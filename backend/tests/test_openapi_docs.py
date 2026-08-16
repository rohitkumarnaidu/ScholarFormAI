# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not getattr(settings, "DEBUG", False),
    reason="OpenAPI docs are disabled outside DEBUG mode",
)


def _trigger_lazy_routers(client: TestClient) -> None:
    """Hit a v1 path to trigger the lazy router loader middleware."""
    client.get("/api/v1/health", follow_redirects=False)


def test_openapi_json_is_exposed() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        _trigger_lazy_routers(client)
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert payload.get("openapi")
    assert isinstance(payload.get("paths"), dict)
    v1_paths = [p for p in payload["paths"] if p.startswith("/api/v1/")]
    assert len(v1_paths) > 0, f"No /api/v1/ paths found in OpenAPI schema. Paths: {list(payload['paths'].keys())}"
    assert "/api/v1/documents/upload" in payload["paths"], (
        f"/api/v1/documents/upload not found. Available v1 paths: {v1_paths}"
    )


def test_swagger_docs_ui_is_exposed() -> None:
    with TestClient(app) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_redoc_ui_is_exposed() -> None:
    with TestClient(app) as client:
        response = client.get("/redoc")

    assert response.status_code == 200
    assert "redoc" in response.text.lower()
