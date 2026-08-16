# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


FIXTURE_SETTINGS = type("Settings", (), {"CSL_SEARCH_CACHE_TTL_SECONDS": 300, "CSL_FETCH_CACHE_TTL_SECONDS": 1800})()


class TestCslFetcherModule:
    def test_search_cache_ttl_seconds_normal(self):
        from app.pipeline.services.csl_fetcher import _search_cache_ttl_seconds

        with patch("app.pipeline.services.csl_fetcher.settings", FIXTURE_SETTINGS):
            ttl = _search_cache_ttl_seconds()
            assert ttl == 300.0

    def test_search_cache_ttl_seconds_invalid(self):
        from app.pipeline.services.csl_fetcher import _search_cache_ttl_seconds

        bad_settings = type("Settings", (), {"CSL_SEARCH_CACHE_TTL_SECONDS": "not_a_number"})()
        with patch("app.pipeline.services.csl_fetcher.settings", bad_settings):
            ttl = _search_cache_ttl_seconds()
            assert ttl == 300.0

    def test_search_cache_ttl_seconds_negative(self):
        from app.pipeline.services.csl_fetcher import _search_cache_ttl_seconds

        neg_settings = type("Settings", (), {"CSL_SEARCH_CACHE_TTL_SECONDS": -100})()
        with patch("app.pipeline.services.csl_fetcher.settings", neg_settings):
            ttl = _search_cache_ttl_seconds()
            assert ttl == 0.0

    def test_search_cache_ttl_seconds_missing_attr(self):
        from app.pipeline.services.csl_fetcher import _search_cache_ttl_seconds

        no_attr = type("Settings", (), {})()
        with patch("app.pipeline.services.csl_fetcher.settings", no_attr):
            ttl = _search_cache_ttl_seconds()
            assert ttl == 300.0

    def test_style_cache_ttl_seconds_normal(self):
        from app.pipeline.services.csl_fetcher import _style_cache_ttl_seconds

        with patch("app.pipeline.services.csl_fetcher.settings", FIXTURE_SETTINGS):
            ttl = _style_cache_ttl_seconds()
            assert ttl == 1800.0

    def test_style_cache_ttl_seconds_invalid(self):
        from app.pipeline.services.csl_fetcher import _style_cache_ttl_seconds

        bad_settings = type("Settings", (), {"CSL_FETCH_CACHE_TTL_SECONDS": "bad"})()
        with patch("app.pipeline.services.csl_fetcher.settings", bad_settings):
            ttl = _style_cache_ttl_seconds()
            assert ttl == 1800.0

    def test_style_cache_ttl_seconds_negative(self):
        from app.pipeline.services.csl_fetcher import _style_cache_ttl_seconds

        neg_settings = type("Settings", (), {"CSL_FETCH_CACHE_TTL_SECONDS": -50})()
        with patch("app.pipeline.services.csl_fetcher.settings", neg_settings):
            ttl = _style_cache_ttl_seconds()
            assert ttl == 0.0

    def test_get_search_cache_lock_creates(self):
        from app.pipeline.services.csl_fetcher import _get_search_cache_lock, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        lock = _get_search_cache_lock()
        import asyncio

        assert isinstance(lock, asyncio.Lock)

    def test_get_search_cache_lock_reuses(self):
        from app.pipeline.services.csl_fetcher import _get_search_cache_lock, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        l1 = _get_search_cache_lock()
        l2 = _get_search_cache_lock()
        assert l1 is l2

    def test_get_style_cache_lock_creates(self):
        from app.pipeline.services.csl_fetcher import _get_style_cache_lock, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        lock = _get_style_cache_lock()
        import asyncio

        assert isinstance(lock, asyncio.Lock)

    def test_clone_style_rows(self):
        from app.pipeline.services.csl_fetcher import _clone_style_rows

        rows = [{"slug": "ieee", "title": "IEEE"}]
        cloned = _clone_style_rows(rows)
        assert cloned == rows
        assert cloned is not rows
        assert cloned[0] is not rows[0]

    def test_clone_style_payload(self):
        from app.pipeline.services.csl_fetcher import _clone_style_payload

        payload = {"slug": "ieee", "content": "<style/>"}
        cloned = _clone_style_payload(payload)
        assert cloned == payload
        assert cloned is not payload

    def test_reset_csl_cache_for_tests(self):
        from app.pipeline.services.csl_fetcher import _search_cache, _style_cache, reset_csl_cache_for_tests

        _search_cache["test"] = (1.0, [])
        _style_cache["test"] = (1.0, {})
        reset_csl_cache_for_tests()
        assert len(_search_cache) == 0
        assert len(_style_cache) == 0

    def test_local_styles(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import _local_styles

        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            (tmp_path / "ieee").mkdir()
            (tmp_path / "ieee" / "styles.csl").write_text("<style/>")
            (tmp_path / "apa").mkdir()
            (tmp_path / "apa" / "styles.csl").write_text("<style/>")
            rows = _local_styles()
            slugs = {r["slug"] for r in rows}
            assert "ieee" in slugs
            assert "apa" in slugs
            assert all(r["source"] == "local" for r in rows)

    def test_local_styles_empty_dir(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import _local_styles

        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            rows = _local_styles()
            assert rows == []


class TestSearchStyles:
    @pytest.mark.asyncio
    async def test_search_styles_empty_query(self):
        from app.pipeline.services.csl_fetcher import reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            with patch("httpx.AsyncClient"):
                results = await search_styles("", limit=10)
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_styles_cached_hit(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _search_cache, reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        cache_key = "test|20"
        _search_cache[cache_key] = (monotonic() + 1000, [{"slug": "cached", "title": "Cached", "source": "local"}])
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            results = await search_styles("test", limit=20)
            assert len(results) == 1
            assert results[0]["slug"] == "cached"

    @pytest.mark.asyncio
    async def test_search_styles_expired_cache(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _search_cache, reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        cache_key = "new|20"
        _search_cache[cache_key] = (monotonic() - 1000, [{"slug": "old", "title": "Old", "source": "local"}])
        with patch(
            "app.pipeline.services.csl_fetcher._local_styles",
            return_value=[{"slug": "new", "title": "NEW", "source": "local"}],
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.json.return_value = [{"name": "new", "title": "New Style"}]
                mock_response.raise_for_status.return_value = None
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                results = await search_styles("new", limit=20)
                slugs = [r["slug"] for r in results]
                assert "new" in slugs

    @pytest.mark.asyncio
    async def test_search_styles_remote_api_failure(self):
        from app.pipeline.services.csl_fetcher import reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_instance.get = AsyncMock(side_effect=Exception("Network error"))
                mock_client.return_value = mock_instance
                results = await search_styles("anything", limit=10)
                assert results == []

    @pytest.mark.asyncio
    async def test_search_styles_remote_returns_valid_data(self):
        from app.pipeline.services.csl_fetcher import reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.json.return_value = [
                    {"name": "ieee", "title": "IEEE Style"},
                    {"name": "", "title": "No slug"},
                ]
                mock_response.raise_for_status.return_value = None
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                results = await search_styles("ieee", limit=10)
                assert len(results) == 1
                assert results[0]["slug"] == "ieee"

    @pytest.mark.asyncio
    async def test_search_styles_remote_returns_non_list(self):
        from app.pipeline.services.csl_fetcher import reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.json.return_value = {"not": "a list"}
                mock_response.raise_for_status.return_value = None
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                results = await search_styles("ieee", limit=10)
                assert results == []

    @pytest.mark.asyncio
    async def test_search_styles_shared_lock_same_cache(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _search_cache, reset_csl_cache_for_tests, search_styles

        reset_csl_cache_for_tests()
        cache_key = "shared|20"
        _search_cache[cache_key] = (monotonic() + 1000, [{"slug": "shared_res", "title": "Shared", "source": "local"}])
        with patch("app.pipeline.services.csl_fetcher._local_styles", return_value=[]):
            results = await search_styles("shared", limit=20)
            assert results[0]["slug"] == "shared_res"


class TestFetchStyle:
    @pytest.mark.asyncio
    async def test_fetch_style_empty_slug_raises(self):
        from app.pipeline.services.csl_fetcher import fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with pytest.raises(ValueError, match="slug is required"):
            await fetch_style("")

    @pytest.mark.asyncio
    async def test_fetch_style_none_slug_raises(self):
        from app.pipeline.services.csl_fetcher import fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with pytest.raises(ValueError, match="slug is required"):
            await fetch_style(None)

    @pytest.mark.asyncio
    async def test_fetch_style_cached_hit(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _style_cache, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        _style_cache["ieee"] = (monotonic() + 1000, {"slug": "ieee", "source": "local", "content": "<style/>"})
        result = await fetch_style("ieee")
        assert result["slug"] == "ieee"
        assert result["content"] == "<style/>"

    @pytest.mark.asyncio
    async def test_fetch_style_local_path_exists(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            (tmp_path / "ieee").mkdir()
            (tmp_path / "ieee" / "styles.csl").write_text("<style>local</style>")
            result = await fetch_style("ieee")
            assert result["source"] == "local"
            assert result["content"] == "<style>local</style>"

    @pytest.mark.asyncio
    async def test_fetch_style_local_path_exists_ttl_zero(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import _style_cache, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        bad_settings = type("Settings", (), {"CSL_FETCH_CACHE_TTL_SECONDS": -1})()
        with patch("app.pipeline.services.csl_fetcher.settings", bad_settings):
            with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
                (tmp_path / "ieee").mkdir()
                (tmp_path / "ieee" / "styles.csl").write_text("<style>no-cache</style>")
                result = await fetch_style("ieee")
                assert result["source"] == "local"
                assert "ieee" not in _style_cache

    @pytest.mark.asyncio
    async def test_fetch_style_remote(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.text = "<style>remote</style>"
                mock_response.raise_for_status.return_value = None
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                result = await fetch_style("nature")
                assert result["source"] == "remote"
                assert result["content"] == "<style>remote</style>"

    @pytest.mark.asyncio
    async def test_fetch_style_remote_ttl_zero(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import _style_cache, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        bad_settings = type("Settings", (), {"CSL_FETCH_CACHE_TTL_SECONDS": -1})()
        with patch("app.pipeline.services.csl_fetcher.settings", bad_settings):
            with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_instance = MagicMock()
                    mock_instance.__aenter__.return_value = mock_instance
                    mock_instance.__aexit__.return_value = None
                    mock_response = MagicMock()
                    mock_response.text = "<style>remote-no-cache</style>"
                    mock_response.raise_for_status.return_value = None
                    mock_instance.get = AsyncMock(return_value=mock_response)
                    mock_client.return_value = mock_instance
                    result = await fetch_style("acm")
                assert result["source"] == "remote"
                assert "acm" not in _style_cache

    @pytest.mark.asyncio
    async def test_fetch_style_cached_under_lock(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _style_cache, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        _style_cache["apa"] = (monotonic() + 1000, {"slug": "apa", "source": "local", "content": "<style/>"})
        result = await fetch_style("apa")
        assert result["slug"] == "apa"

    @pytest.mark.asyncio
    async def test_fetch_style_locked_cache_hit(self):
        from time import monotonic

        from app.pipeline.services.csl_fetcher import _style_cache, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        _style_cache["locked"] = (monotonic() + 1000, {"slug": "locked", "source": "local", "content": "cached"})
        result = await fetch_style("locked")
        assert result["slug"] == "locked"

    @pytest.mark.asyncio
    async def test_fetch_style_remote_http_error(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = Exception("HTTP 404")
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                with pytest.raises(Exception):
                    await fetch_style("nonexistent")


class TestFetchStyleZoteroUrl:
    @pytest.mark.asyncio
    async def test_fetch_style_uses_zotero_url(self, tmp_path):
        from pathlib import Path

        from app.pipeline.services.csl_fetcher import ZOTERO_STYLE_URL, fetch_style, reset_csl_cache_for_tests

        reset_csl_cache_for_tests()
        with patch("app.pipeline.services.csl_fetcher.TEMPLATES_DIR", Path(str(tmp_path))):
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = MagicMock()
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_response = MagicMock()
                mock_response.text = "<style/>"
                mock_response.raise_for_status.return_value = None
                mock_instance.get = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_instance
                await fetch_style("my-style")
                expected_url = ZOTERO_STYLE_URL.format(slug="my-style")
                called_url = mock_instance.get.call_args[0][0]
                assert called_url == expected_url
