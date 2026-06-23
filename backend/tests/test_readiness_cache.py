# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services import health_checks


@pytest.fixture(autouse=True)
def reset_readiness_cache():
    health_checks._reset_readiness_cache_for_tests()
    yield
    health_checks._reset_readiness_cache_for_tests()


def _configure_fast_readiness(
    monkeypatch,
    ttl_seconds: float,
    *,
    isolate_external: bool = True,
) -> None:
    monkeypatch.setattr(health_checks.settings, "READINESS_CACHE_TTL_SECONDS", ttl_seconds, raising=False)
    monkeypatch.setattr(health_checks.settings, "GROBID_ENABLED", False, raising=False)
    monkeypatch.setattr(health_checks.settings, "USE_SCIBERT_CLASSIFICATION", False, raising=False)
    if isolate_external:
        # Keep cache tests deterministic by avoiding external endpoint probes.
        monkeypatch.setattr(health_checks, "_service_urls", lambda *args, **kwargs: [])


@pytest.mark.asyncio
async def test_readiness_cache_hits_within_ttl(monkeypatch):
    _configure_fast_readiness(monkeypatch, ttl_seconds=5.0)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch(
            "app.services.llm_service.check_health",
            new=AsyncMock(return_value={"nvidia": "healthy"}),
        ) as mock_llm:
            first_payload, first_status = await health_checks.get_readiness_payload()
            second_payload, second_status = await health_checks.get_readiness_payload()

    assert first_status == second_status
    assert first_payload["ready"] == second_payload["ready"]
    assert first_payload["checks"] == second_payload["checks"]
    assert mock_sb.call_count == 1
    assert mock_llm.await_count == 1


@pytest.mark.asyncio
async def test_readiness_cache_refreshes_after_ttl(monkeypatch):
    _configure_fast_readiness(monkeypatch, ttl_seconds=0.01)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch(
            "app.services.llm_service.check_health",
            new=AsyncMock(return_value={"nvidia": "healthy"}),
        ) as mock_llm:
            first_payload, _ = await health_checks.get_readiness_payload()
            await asyncio.sleep(0.02)
            second_payload, _ = await health_checks.get_readiness_payload()

    assert first_payload["timestamp"] != second_payload["timestamp"]
    assert mock_sb.call_count == 2
    assert mock_llm.await_count == 2


@pytest.mark.asyncio
async def test_readiness_force_refresh_bypasses_cache(monkeypatch):
    _configure_fast_readiness(monkeypatch, ttl_seconds=30.0)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}) as mock_sb:
        with patch(
            "app.services.llm_service.check_health",
            new=AsyncMock(return_value={"nvidia": "healthy"}),
        ) as mock_llm:
            await health_checks.get_readiness_payload()
            await health_checks.get_readiness_payload(force_refresh=True)

    assert mock_sb.call_count == 2
    assert mock_llm.await_count == 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_readiness_includes_dependency_probe_results(monkeypatch):
    _configure_fast_readiness(monkeypatch, ttl_seconds=0.0, isolate_external=False)
    monkeypatch.setattr(health_checks.settings, "GROBID_ENABLED", True, raising=False)
    monkeypatch.setattr(
        health_checks.settings,
        "get_grobid_urls",
        lambda: ["https://grobid-primary.example", "https://grobid-shadow.example"],
        raising=False,
    )
    monkeypatch.setattr(health_checks.settings, "DOCLING_URLS", "https://docling.example", raising=False)
    monkeypatch.setattr(health_checks.settings, "OCR_URLS", "https://ocr.example", raising=False)
    monkeypatch.setattr(health_checks.settings, "DOCX_CONVERTER_URLS", "https://docx.example", raising=False)
    monkeypatch.setattr(health_checks.settings, "get_service_health_path", lambda _name: "/api/isalive", raising=False)

    class _ProbeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            if "grobid-primary.example" in url:
                return SimpleNamespace(status_code=502)
            return SimpleNamespace(status_code=200)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
        with patch("httpx.AsyncClient", return_value=_ProbeClient()):
            with patch(
                "app.services.llm_service.check_health",
                new=AsyncMock(return_value={"nvidia": "healthy"}),
            ):
                payload, status_code = await health_checks.get_readiness_payload(force_refresh=True)

    assert status_code == 200
    assert payload["dependencies"]["grobid"]["status"] == "ready"
    assert payload["dependencies"]["grobid"]["endpoint"] == "https://grobid-shadow.example/api/isalive"
    assert payload["dependencies"]["docling"]["status"] == "ready"
    assert payload["dependencies"]["ocr"]["status"] == "ready"
    assert payload["dependencies"]["docx_converter"]["status"] == "ready"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_readiness_includes_nougat_and_scibert_remote_dependencies(monkeypatch):
    _configure_fast_readiness(monkeypatch, ttl_seconds=0.0, isolate_external=False)
    monkeypatch.setattr(health_checks.settings, "ENABLE_NOUGAT_PARSER", True, raising=False)
    monkeypatch.setattr(health_checks.settings, "NOUGAT_URLS", "https://nougat.example", raising=False)
    monkeypatch.setattr(health_checks.settings, "NOUGAT_HEALTH_PATH", "/", raising=False)
    monkeypatch.setattr(health_checks.settings, "USE_SCIBERT_CLASSIFICATION", True, raising=False)
    monkeypatch.setattr(health_checks.settings, "SCIBERT_URLS", "https://scibert.example", raising=False)
    monkeypatch.setattr(health_checks.settings, "SCIBERT_HEALTH_PATH", "/", raising=False)

    class _ProbeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return SimpleNamespace(status_code=200)

    with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
        with patch("app.services.health_checks.should_enable_scibert", return_value=True):
            with patch("httpx.AsyncClient", return_value=_ProbeClient()):
                with patch(
                    "app.services.llm_service.check_health",
                    new=AsyncMock(return_value={"nvidia": "healthy"}),
                ):
                    payload, status_code = await health_checks.get_readiness_payload(force_refresh=True)

    assert status_code == 200
    assert payload["dependencies"]["nougat"]["status"] == "ready"
    assert payload["dependencies"]["scibert"]["status"] == "ready"
