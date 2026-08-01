# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import patch

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

    def test_validate_doi_true(self, client):
        with patch.object(client, "get_metadata") as mock_get:
            mock_get.return_value = {"title": ["Test"]}
            assert client.validate_doi("10.1234/test") is True

    def test_validate_doi_false(self, client):
        with patch.object(client, "get_metadata") as mock_get:
            mock_get.side_effect = CrossRefException("Not found")
            assert client.validate_doi("10.1234/fake") is False

    @patch("app.pipeline.services.crossref_client.requests.get")
    def test_get_metadata_success(self, mock_get, client):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"message": {"title": ["Test"]}}
        result = client.get_metadata("10.1234/test")
        assert result["title"] == ["Test"]

    @patch("app.pipeline.services.crossref_client.requests.get")
    def test_get_metadata_404(self, mock_get, client):
        mock_get.return_value.status_code = 404
        with pytest.raises(CrossRefException, match="DOI not found"):
            client.get_metadata("10.1234/missing")

    @patch("app.pipeline.services.crossref_client.requests.get")
    def test_get_metadata_api_error(self, mock_get, client):
        mock_get.return_value.status_code = 500
        with pytest.raises(CrossRefException, match="API error"):
            client.get_metadata("10.1234/error")

    @patch("app.pipeline.services.crossref_client.requests.get")
    def test_get_metadata_network_error(self, mock_get, client):
        mock_get.side_effect = __import__("requests").exceptions.ConnectionError("No connection")
        with pytest.raises(CrossRefException, match="Network error"):
            client.get_metadata("10.1234/netfail")

    @patch("app.pipeline.services.crossref_client.time.time")
    @patch("app.pipeline.services.crossref_client.time.sleep")
    def test_wait_for_rate_limit(self, mock_sleep, mock_time, client):
        mock_time.side_effect = [0.0, 0.01]
        client._wait_for_rate_limit()
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
