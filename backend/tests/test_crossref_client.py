# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Unit tests for CrossRefClient.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from app.pipeline.services.crossref_client import CrossRefClient, CrossRefException


class TestCrossRefClient:
    @pytest.fixture
    def client(self):
        return CrossRefClient(email="test@example.com")

    async def test_validate_doi_exists(self, client):
        """Test validate_doi returns True when DOI exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"title": ["Test Title"]}}

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            assert await client.validate_doi("10.1000/182") is True

    async def test_validate_doi_not_found(self, client):
        """Test validate_doi returns False when DOI not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            assert await client.validate_doi("10.1000/nonexistent") is False

    async def test_get_metadata_success(self, client):
        """Test metadata retrieval."""
        expected_data = {"title": ["Test Title"], "author": [{"family": "Doe"}]}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": expected_data}

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            data = await client.get_metadata("10.1000/182")
            assert data == expected_data

    async def test_get_metadata_error(self, client):
        """Test get_metadata raises exception on API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(CrossRefException):
                await client.get_metadata("10.1000/error")

    def test_calculate_confidence(self, client):
        """Test confidence score calculation."""
        ref_data = {"title": "A Great Paper", "year": 2023, "authors": ["Doe, John"]}

        # 1. Perfect Match
        cr_data_perfect = {
            "title": ["A Great Paper"],
            "published-print": {"date-parts": [[2023]]},
            "author": [{"family": "Doe", "given": "John"}],
        }
        score = client.calculate_confidence(ref_data, cr_data_perfect)
        assert score >= 0.9  # Should be 1.0 ideally

        # 2. Partial Match (Different Year)
        cr_data_diff_year = {
            "title": ["A Great Paper"],
            "published-print": {"date-parts": [[2020]]},
            "author": [{"family": "Doe"}],
        }
        score = client.calculate_confidence(ref_data, cr_data_diff_year)
        # 0.5 (title) + 0.2 (author) = 0.7
        assert 0.6 <= score <= 0.8

        # 3. No Match
        cr_data_none = {
            "title": ["Completely Different"],
            "published-print": {"date-parts": [[1990]]},
            "author": [{"family": "Smith"}],
        }
        score = client.calculate_confidence(ref_data, cr_data_none)
        assert score < 0.2

    async def test_rate_limiting(self, client):
        """Test that rate limiting waits appropriate time."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {}}

        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with patch("time.time", side_effect=[100.0, 100.0, 100.01, 100.01]):
                with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
                    # First request (should not sleep)
                    await client.get_metadata("doi1")
                    mock_sleep.assert_not_called()

                    # Second request (0.01s elapsed < 0.025s limit) -> should sleep
                    await client.get_metadata("doi2")

                    # Verify sleep was called with roughly 0.015s
                    mock_sleep.assert_called_once()
                    args, _ = mock_sleep.call_args
                    assert 0.0 < args[0] < 0.05


# ---------------------------------------------------------------------------
# Services version of CrossRefClient (app/services/crossref_client.py)
# ---------------------------------------------------------------------------


class TestCrossRefClientServices:
    @pytest.fixture
    def client(self):
        from app.services.crossref_client import CrossRefClient

        return CrossRefClient(contact_email="test@example.com")

    def test_init_sets_headers(self, client):
        assert "User-Agent" in client.headers
        assert "test@example.com" in client.headers["User-Agent"]

    def test_validate_citation_empty_returns_empty(self, client):
        assert client.validate_citation("") == {}
        assert client.validate_citation("short") == {}

    def test_validate_citation_cache_hit(self, client):
        client._api_cache["Some Author 2023"] = {"doi": "10.1234/test"}
        result = client.validate_citation("  Some Author 2023  ")
        assert result["doi"] == "10.1234/test"

    @patch("app.services.crossref_client.HAS_REDIS", True)
    @patch("app.services.crossref_client.redis_client")
    def test_get_cache_redis_hit(self, mock_redis, client):
        import json

        mock_redis.get.return_value = json.dumps({"doi": "10.1234/redis"})
        result = client._get_cache("test-query")
        assert result["doi"] == "10.1234/redis"
        mock_redis.get.assert_called_with("crossref:test-query")

    @patch("app.services.crossref_client.HAS_REDIS", True)
    @patch("app.services.crossref_client.redis_client")
    def test_get_cache_redis_miss(self, mock_redis, client):
        mock_redis.get.return_value = None
        assert client._get_cache("test-query") is None

    @patch("app.services.crossref_client.HAS_REDIS", True)
    @patch("app.services.crossref_client.redis_client")
    def test_get_cache_redis_exception(self, mock_redis, client):
        mock_redis.get.side_effect = Exception("redis down")
        assert client._get_cache("test-query") is None

    @patch("app.services.crossref_client.HAS_REDIS", True)
    @patch("app.services.crossref_client.redis_client")
    def test_set_cache_redis(self, mock_redis, client):
        import json

        client._set_cache("test-key", {"doi": "10.1234/save"})
        mock_redis.setex.assert_called_once_with(
            "crossref:test-key",
            86400 * 7,
            json.dumps({"doi": "10.1234/save"}),
        )

    @patch("app.services.crossref_client.HAS_REDIS", False)
    def test_get_cache_no_redis(self, client):
        assert client._get_cache("test") is None

    @patch("app.services.crossref_client.HAS_REDIS", False)
    def test_set_cache_no_redis(self, client):
        client._set_cache("test", {"doi": "x"})
        # Should not raise

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_success(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/test",
                        "title": ["Test Paper"],
                        "author": [{"given": "John", "family": "Doe"}],
                        "score": 85.0,
                        "URL": "https://doi.org/10.1234/test",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        result = client._fetch_api("Test Paper")
        assert result["doi"] == "10.1234/test"
        assert result["title"] == "Test Paper"
        assert "Doe" in result["authors"]
        assert result["confidence"] == 85.0
        # Verify cache was set
        assert "Test Paper" in client._api_cache

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_not_found(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"items": []}}
        mock_get.return_value = mock_response
        assert client._fetch_api("No Results") == {}

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_rate_limited_then_succeeds(self, mock_get, client):
        responses = [MagicMock(status_code=429), MagicMock(status_code=200)]
        responses[1].json.return_value = {"message": {"items": [{"DOI": "10.1234/rl"}]}}
        mock_get.side_effect = responses
        with patch("app.services.crossref_client.time.sleep"):
            result = client._fetch_api("Rate Limited")
        assert result["doi"] == "10.1234/rl"

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_rate_limited_exhausted(self, mock_get, client):
        responses = [MagicMock(status_code=429) for _ in range(4)]
        mock_get.side_effect = responses
        with patch("app.services.crossref_client.time.sleep"):
            result = client._fetch_api("Rate Limited Forever")
        assert result == {}

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_network_error(self, mock_get, client):
        mock_get.side_effect = requests.RequestException("timeout")
        result = client._fetch_api("Network Error")
        assert result == {}

    @patch("app.services.crossref_client.requests.get")
    def test_fetch_api_json_error(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("bad json")
        mock_get.return_value = mock_response
        result = client._fetch_api("Bad JSON")
        assert result == {}

    @patch("app.services.crossref_client.requests.get")
    def test_cache_trim(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"items": []}}
        mock_get.return_value = mock_response
        # Fill cache beyond 2000 limit
        for i in range(2010):
            client._api_cache[f"key_{i}"] = {"val": i}
        client._fetch_api("new_query")
        assert len(client._api_cache) <= 2001


class TestGetCrossRefClient:
    def test_returns_singleton(self):
        from app.services.crossref_client import get_crossref_client

        c1 = get_crossref_client()
        c2 = get_crossref_client()
        assert c1 is c2
