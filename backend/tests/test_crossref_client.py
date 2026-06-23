# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


"""
Unit tests for CrossRefClient.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from app.pipeline.services.crossref_client import CrossRefClient, CrossRefException

class TestCrossRefClient:
    
    @pytest.fixture
    def client(self):
        return CrossRefClient(email="test@example.com")

    @patch("requests.get")
    def test_validate_doi_exists(self, mock_get, client):
        """Test validate_doi returns True when DOI exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"title": ["Test Title"]}}
        mock_get.return_value = mock_response
        
        assert client.validate_doi("10.1000/182") is True
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_validate_doi_not_found(self, mock_get, client):
        """Test validate_doi returns False when DOI not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        assert client.validate_doi("10.1000/nonexistent") is False

    @patch("requests.get")
    def test_get_metadata_success(self, mock_get, client):
        """Test metadata retrieval."""
        expected_data = {"title": ["Test Title"], "author": [{"family": "Doe"}]}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": expected_data}
        mock_get.return_value = mock_response
        
        data = client.get_metadata("10.1000/182")
        assert data == expected_data

    @patch("requests.get")
    def test_get_metadata_error(self, mock_get, client):
        """Test get_metadata raises exception on API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        with pytest.raises(CrossRefException):
            client.get_metadata("10.1000/error")

    def test_calculate_confidence(self, client):
        """Test confidence score calculation."""
        ref_data = {
            "title": "A Great Paper",
            "year": 2023,
            "authors": ["Doe, John"]
        }
        
        # 1. Perfect Match
        cr_data_perfect = {
            "title": ["A Great Paper"],
            "published-print": {"date-parts": [[2023]]},
            "author": [{"family": "Doe", "given": "John"}]
        }
        score = client.calculate_confidence(ref_data, cr_data_perfect)
        assert score >= 0.9  # Should be 1.0 ideally
        
        # 2. Partial Match (Different Year)
        cr_data_diff_year = {
            "title": ["A Great Paper"],
            "published-print": {"date-parts": [[2020]]},
            "author": [{"family": "Doe"}]
        }
        score = client.calculate_confidence(ref_data, cr_data_diff_year)
        # 0.5 (title) + 0.2 (author) = 0.7
        assert 0.6 <= score <= 0.8

        # 3. No Match
        cr_data_none = {
            "title": ["Completely Different"],
            "published-print": {"date-parts": [[1990]]},
            "author": [{"family": "Smith"}]
        }
        score = client.calculate_confidence(ref_data, cr_data_none)
        assert score < 0.2

    @patch("time.sleep")
    @patch("time.time")
    @patch("requests.get")
    def test_rate_limiting(self, mock_get, mock_time, mock_sleep, client):
        """Test that rate limiting waits appropriate time."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Sequence of time.time() calls:
        # 1. Initial check in _wait_for_rate_limit (first request) -> 100.0
        # 2. Update last_request_time -> 100.0
        # 3. Initial check in _wait_for_rate_limit (second request) -> 100.01 (too soon)
        # 4. Update last_request_time -> 100.01
        
        mock_time.side_effect = [100.0, 100.0, 100.01, 100.01]
        
        # First request (should not sleep)
        client.get_metadata("doi1")
        mock_sleep.assert_not_called()
        
        # Second request (0.01s elapsed < 0.025s limit) -> should sleep
        client.get_metadata("doi2")
        
        # Verify sleep was called with roughly 0.015s
        mock_sleep.assert_called_once()
        args, _ = mock_sleep.call_args
        assert 0.0 < args[0] < 0.05

