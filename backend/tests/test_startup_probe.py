# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import _probe_grobid_startup, app


@pytest.mark.asyncio
async def test_probe_grobid_startup_skips_when_disabled():
    with patch("app.main.settings.GROBID_ENABLED", False):
        result = await _probe_grobid_startup()

    assert result is False


@pytest.mark.asyncio
async def test_probe_grobid_startup_success():
    class _HealthyClient:
        calls = []

        def __init__(self, *args, **kwargs):
            return

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            self.calls.append(url)
            return SimpleNamespace(status_code=200)

    with (
        patch("app.main.settings.GROBID_ENABLED", True),
        patch("app.main.settings.get_grobid_urls", lambda: ["http://grobid.local:8070"]),
        patch("app.main.settings.get_service_health_path", lambda _name: "/api/isalive"),
        patch("httpx.AsyncClient", _HealthyClient),
    ):
        result = await _probe_grobid_startup(attempts=3, timeout_seconds=0.01)

    assert result is True
    assert len(_HealthyClient.calls) == 1
    assert _HealthyClient.calls[0] == "http://grobid.local:8070/api/isalive"


@pytest.mark.asyncio
async def test_probe_grobid_startup_retries_then_degrades():
    class _UnhealthyClient:
        calls = 0

        def __init__(self, *args, **kwargs):
            return

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            _UnhealthyClient.calls += 1
            return SimpleNamespace(status_code=503)

    with (
        patch("app.main.settings.GROBID_ENABLED", True),
        patch("app.main.settings.get_grobid_urls", lambda: ["http://grobid.local:8070"]),
        patch("app.main.settings.get_service_health_path", lambda _name: "/api/isalive"),
        patch("httpx.AsyncClient", _UnhealthyClient),
    ):
        result = await _probe_grobid_startup(attempts=3, timeout_seconds=0.01)

    assert result is False
    assert _UnhealthyClient.calls == 3


def test_lifespan_sets_grobid_probe_state_even_when_failed():
    with (
        patch("app.main._probe_grobid_startup", new=AsyncMock(return_value=False)),
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        with TestClient(app) as client:
            assert client.app.state.grobid_startup_probe_ok is False
            response = client.get("/api/v1/health")

    assert response.status_code == 200
