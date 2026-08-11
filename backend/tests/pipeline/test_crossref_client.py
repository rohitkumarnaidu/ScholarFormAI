# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.services.crossref_client import CrossRefClient, CrossRefException


class TestCrossRefClient:
    @pytest.fixture
    def client(self):
        return CrossRefClient(email="test@example.com")

    def test_init_with_email(self):
        client = CrossRefClient(email="user@example.com")
        assert "User-Agent" in client.headers
        assert "user@example.com" in client.headers["User-Agent"]

    def test_init_without_email(self):
        client = CrossRefClient()
        assert client.headers == {}

    async def test_validate_doi_true(self, client):
        with patch.object(client, "get_metadata", new=AsyncMock(return_value={"title": ["Test"]})):
            assert await client.validate_doi("10.1234/test") is True

    async def test_validate_doi_false(self, client):
        with patch.object(client, "get_metadata", new=AsyncMock(side_effect=CrossRefException("Not found"))):
            assert await client.validate_doi("10.1234/fake") is False

    async def test_get_metadata_success(self, client):
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"message": {"title": ["Test"]}}
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            result = await client.get_metadata("10.1234/test")
            assert result["title"] == ["Test"]

    async def test_get_metadata_404(self, client):
        mock_response = MagicMock(status_code=404)
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(CrossRefException, match="DOI not found"):
                await client.get_metadata("10.1234/missing")

    async def test_get_metadata_api_error(self, client):
        mock_response = MagicMock(status_code=500)
        with patch.object(client._client, "get", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(CrossRefException, match="API error"):
                await client.get_metadata("10.1234/error")

    async def test_get_metadata_network_error(self, client):
        with patch.object(client._client, "get", new=AsyncMock(side_effect=httpx.RequestError("No connection"))):
            with pytest.raises(CrossRefException, match="Network error"):
                await client.get_metadata("10.1234/netfail")

    async def test_wait_for_rate_limit(self, client):
        with patch("app.pipeline.services.crossref_client.time.time", side_effect=[0.0, 0.01]):
            with patch("app.pipeline.services.crossref_client.asyncio.sleep", new=AsyncMock()) as mock_sleep:
                await client._wait_for_rate_limit()
                mock_sleep.assert_called_once()

    def test_calculate_confidence_full_match(self, client):
        ref_data = {"title": "Deep Learning", "year": 2016, "authors": ["Goodfellow, Ian"]}
        cr_data = {
            "title": ["Deep Learning"],
            "published-print": {"date-parts": [[2016]]},
            "author": [{"family": "Goodfellow", "given": "Ian"}],
        }
        score = client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_calculate_confidence_no_match(self, client):
        ref_data = {"title": "Different", "year": 2020, "authors": ["Unknown"]}
        cr_data = {"title": ["Other"], "published-online": {"date-parts": [[2019]]}}
        score = client.calculate_confidence(ref_data, cr_data)
        assert score < 0.5

    def test_calculate_confidence_no_checks_possible(self, client):
        score = client.calculate_confidence({}, {})
        assert score == 0.0

    def test_calculate_confidence_title_only(self, client):
        ref_data = {"title": "Exact Match Title"}
        cr_data = {"title": ["Exact Match Title"]}
        score = client.calculate_confidence(ref_data, cr_data)
        assert score == pytest.approx(0.5, abs=0.01)
