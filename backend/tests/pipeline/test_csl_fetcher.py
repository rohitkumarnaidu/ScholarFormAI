# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Force cache reset before importing module
from app.pipeline.services import csl_fetcher

csl_fetcher.reset_csl_cache_for_tests()


@pytest.fixture(autouse=True)
def reset_cache():
    csl_fetcher.reset_csl_cache_for_tests()


class TestCslFetcherCacheHelpers:
    def test_search_cache_ttl_default(self):
        ttl = csl_fetcher._search_cache_ttl_seconds()
        assert ttl == 300.0

    def test_style_cache_ttl_default(self):
        ttl = csl_fetcher._style_cache_ttl_seconds()
        assert ttl == 1800.0

    def test_reset_cache_clears_locks(self):
        csl_fetcher.reset_csl_cache_for_tests()
        assert csl_fetcher._search_cache == {}
        assert csl_fetcher._style_cache == {}
        assert csl_fetcher._search_cache_lock is None
        assert csl_fetcher._style_cache_lock is None


class TestCslFetcherLocalStyles:
    def test_local_styles_returns_list(self):
        result = csl_fetcher._local_styles()
        assert isinstance(result, list)
        for row in result:
            assert "slug" in row
            assert "source" in row
            assert row["source"] == "local"

    def test_local_styles_finds_local_templates(self):
        result = csl_fetcher._local_styles()
        slugs = [r["slug"] for r in result]
        assert "ieee" in slugs
        assert "apa" in slugs


class TestCslFetcherSearchStyles:
    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_search_returns_empty_for_blank(self, mock_httpx):
        result = await csl_fetcher.search_styles("", limit=5)
        assert isinstance(result, list)

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_search_local_only_found(self, mock_httpx):
        result = await csl_fetcher.search_styles("ieee", limit=10)
        slugs = [r["slug"] for r in result]
        assert "ieee" in slugs
        pass

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_search_local_only_not_found(self, mock_httpx):
        result = await csl_fetcher.search_styles("nonexistentstylexyz", limit=5)
        assert len(result) == 0

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_search_remote_success(self, mock_httpx):
        mock_resp = MagicMock(spec=["raise_for_status", "json"])
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"name": "custom-style", "title": "Custom Style"},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx.return_value = mock_client
        result = await csl_fetcher.search_styles("custom", limit=5)
        assert len(result) > 0

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_search_remote_failure_returns_local_only(self, mock_httpx):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Network error")
        mock_httpx.return_value = mock_client
        result = await csl_fetcher.search_styles("ieee", limit=5)
        assert len(result) > 0


class TestCslFetcherFetchStyle:
    def test_empty_slug_raises(self):
        with pytest.raises(ValueError, match="slug is required"):
            import asyncio
            asyncio.run(csl_fetcher.fetch_style(""))

    def test_blank_slug_raises(self):
        with pytest.raises(ValueError, match="slug is required"):
            import asyncio
            asyncio.run(csl_fetcher.fetch_style("   "))

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_fetch_local_style(self, mock_httpx):
        result = await csl_fetcher.fetch_style("ieee")
        assert result["slug"] == "ieee"
        assert result["source"] == "local"
        assert "content" in result

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_fetch_remote_style(self, mock_httpx):
        mock_resp = MagicMock(spec=["raise_for_status", "text"])
        mock_resp.status_code = 200
        mock_resp.text = "<style>...</style>"
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx.return_value = mock_client

        # Temporarily remove local path to force remote fetch
        orig = csl_fetcher.TEMPLATES_DIR
        fake_dir = Path(__file__).parent / "_nonexistent"
        csl_fetcher.TEMPLATES_DIR = fake_dir

        try:
            result = await csl_fetcher.fetch_style("someremotestyle")
            assert result["source"] == "remote"
            assert result["content"] == "<style>...</style>"
        finally:
            csl_fetcher.TEMPLATES_DIR = orig

    @patch("app.pipeline.services.csl_fetcher.httpx.AsyncClient")
    async def test_fetch_style_caching(self, mock_httpx):
        mock_resp = MagicMock(spec=["raise_for_status", "text"])
        mock_resp.status_code = 200
        mock_resp.text = "<style>data</style>"
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_httpx.return_value = mock_client

        orig = csl_fetcher.TEMPLATES_DIR
        fake_dir = Path(__file__).parent / "_nonexistent"
        csl_fetcher.TEMPLATES_DIR = fake_dir

        try:
            r1 = await csl_fetcher.fetch_style("cachedtest")
            assert r1["source"] == "remote"
            assert mock_client.get.call_count == 1

            r2 = await csl_fetcher.fetch_style("cachedtest")
            assert r2["source"] == "remote"
            # Should use cache, not call again
            assert mock_client.get.call_count == 1
        finally:
            csl_fetcher.TEMPLATES_DIR = orig


@pytest.fixture(scope="module", autouse=True)
def cleanup_cache():
    yield
    csl_fetcher.reset_csl_cache_for_tests()
