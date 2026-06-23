# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.services import csl_fetcher


def _mock_httpx_client(*, payload=None, text: str = ""):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=payload if payload is not None else [])
    response.text = text

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=response)
    return client


@pytest.fixture(autouse=True)
def reset_csl_cache():
    csl_fetcher.reset_csl_cache_for_tests()
    yield
    csl_fetcher.reset_csl_cache_for_tests()


@pytest.mark.asyncio
async def test_search_styles_uses_cache(monkeypatch):
    monkeypatch.setattr(csl_fetcher.settings, "CSL_SEARCH_CACHE_TTL_SECONDS", 30, raising=False)
    monkeypatch.setattr(
        csl_fetcher,
        "_local_styles",
        lambda: [{"slug": "ieee", "title": "IEEE", "source": "local"}],
        raising=True,
    )
    client = _mock_httpx_client(payload=[{"name": "apa", "title": "APA"}])

    with patch("httpx.AsyncClient", return_value=client):
        first = await csl_fetcher.search_styles("ieee")
        second = await csl_fetcher.search_styles("ieee")

    assert first == second
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_fetch_style_remote_uses_cache(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(csl_fetcher.settings, "CSL_FETCH_CACHE_TTL_SECONDS", 30, raising=False)
    monkeypatch.setattr(csl_fetcher, "TEMPLATES_DIR", tmp_path, raising=True)
    client = _mock_httpx_client(text="<style id='remote'/>")

    with patch("httpx.AsyncClient", return_value=client):
        first = await csl_fetcher.fetch_style("my-remote-style")
        second = await csl_fetcher.fetch_style("my-remote-style")

    assert first == second
    assert first["source"] == "remote"
    assert client.get.await_count == 1


@pytest.mark.asyncio
async def test_search_styles_cache_expires(monkeypatch):
    monkeypatch.setattr(csl_fetcher.settings, "CSL_SEARCH_CACHE_TTL_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(
        csl_fetcher,
        "_local_styles",
        lambda: [{"slug": "ieee", "title": "IEEE", "source": "local"}],
        raising=True,
    )
    client = _mock_httpx_client(payload=[{"name": "apa", "title": "APA"}])

    with patch("httpx.AsyncClient", return_value=client):
        await csl_fetcher.search_styles("ieee")
        await asyncio.sleep(0.02)
        await csl_fetcher.search_styles("ieee")

    assert client.get.await_count == 2
