# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services import health_checks


@pytest.fixture(autouse=True)
def reset_health_cache():
    health_checks._reset_readiness_cache_for_tests()
    yield
    health_checks._reset_readiness_cache_for_tests()


def _configure_health_cache(monkeypatch, ttl_seconds: float) -> None:
    monkeypatch.setattr(health_checks.settings, "HEALTH_CACHE_TTL_SECONDS", ttl_seconds, raising=False)


def _mock_httpx_client(status_code: int = 200):
    response = AsyncMock()
    response.status_code = status_code
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=response)
    return client


@pytest.mark.asyncio
async def test_health_cache_hits_within_ttl(monkeypatch):
    _configure_health_cache(monkeypatch, ttl_seconds=5.0)
    monkeypatch.setattr(health_checks.settings, "OLLAMA_URL", "http://ollama:11434", raising=False)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch("httpx.AsyncClient", return_value=_mock_httpx_client()):
            with patch("app.services.model_store.model_store.get_model", return_value=True):
                first_payload, first_status = await health_checks.get_health_payload()
                second_payload, second_status = await health_checks.get_health_payload()

    assert first_status == second_status == 200
    assert first_payload == second_payload
    assert mock_sb.call_count == 1


@pytest.mark.asyncio
async def test_health_cache_refreshes_after_ttl(monkeypatch):
    _configure_health_cache(monkeypatch, ttl_seconds=0.01)
    monkeypatch.setattr(health_checks.settings, "OLLAMA_URL", "http://ollama:11434", raising=False)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch("httpx.AsyncClient", return_value=_mock_httpx_client()):
            with patch("app.services.model_store.model_store.get_model", return_value=True):
                await health_checks.get_health_payload()
                await asyncio.sleep(0.02)
                await health_checks.get_health_payload()

    assert mock_sb.call_count == 2


@pytest.mark.asyncio
async def test_health_force_refresh_bypasses_cache(monkeypatch):
    _configure_health_cache(monkeypatch, ttl_seconds=30.0)
    monkeypatch.setattr(health_checks.settings, "OLLAMA_URL", "http://ollama:11434", raising=False)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch("httpx.AsyncClient", return_value=_mock_httpx_client()):
            with patch("app.services.model_store.model_store.get_model", return_value=True):
                await health_checks.get_health_payload()
                await health_checks.get_health_payload(force_refresh=True)

    assert mock_sb.call_count == 2
