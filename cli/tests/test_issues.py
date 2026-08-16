"""Tests for issue management CLI commands."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock backend modules for CLI tests
sys.modules["app"] = MagicMock()
sys.modules["app.services"] = MagicMock()
sys.modules["app.services.issue_service"] = MagicMock()

from amf.main import cli


@pytest.fixture
def mock_issue_service():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        # Create a function that returns different JSON based on the URL or request body
        def mock_read():
            req = mock_urlopen.call_args[0][0]
            url = req.full_url if hasattr(req, "full_url") else req
            if "/stats" in url:
                return b'{"data": {"total_issues": 10, "open_issues": 5, "resolved_issues": 3}}'
            if "/labels" in url:
                return b'{"data": {"bug": {"name": "bug"}}}'
            if "/search" in url:
                return b'{"data": []}'
            if req.method == "POST" and "comments" in url:
                return b'{"data": {"tracking_number": "AMF-001"}}'
            if req.method == "POST":
                return b'{"data": {"id": "test-id", "tracking_number": "AMF-250726-0001", "status": "new"}}'
            if req.method == "PATCH" or req.method == "PUT":
                return b'{"data": {"tracking_number": "AMF-001", "status": "resolved"}}'
            if "test-id" in url:
                return b'{"data": {"id": "test-id", "tracking_number": "AMF-250726-0001", "title": "Test Bug"}}'
            # Default for list
            return b'{"data": [{"id": "1", "tracking_number": "AMF-001", "title": "Bug 1"}]}'
            
        mock_response.read.side_effect = mock_read
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        yield mock_urlopen


def test_issue_report(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "report", "-t", "Test Bug", "-d", "Found a bug", "-c", "bug"])
    assert result.exit_code == 0
    assert "submitted" in result.output.lower()


def test_issue_report_with_all_options(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "report", "-t", "Test", "-d", "Desc", "-c", "performance", "-s", "high", "-n", "User", "-e", "u@test.com"])
    assert result.exit_code == 0


def test_issue_list(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "list"])
    assert result.exit_code == 0
    assert "AMF-001" in result.output


def test_issue_list_with_filters(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "list", "--status", "new", "--category", "bug"])
    assert result.exit_code == 0


def test_issue_show(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "show", "test-id"])
    assert result.exit_code == 0
    assert "Test Bug" in result.output


def test_issue_comment(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "comment", "test-id", "-b", "I found the issue"])
    assert result.exit_code == 0
    assert "added" in result.output.lower()


def test_issue_update(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "update", "test-id", "--status", "resolved"])
    assert result.exit_code == 0
    assert "updated" in result.output.lower()


def test_issue_search(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "search", "bug"])
    assert result.exit_code == 0


def test_issue_stats(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "stats"])
    assert result.exit_code == 0
    assert "10" in result.output


def test_issue_labels(runner, mock_issue_service):
    result = runner.invoke(cli, ["issue", "labels"])
    assert result.exit_code == 0
    assert "bug" in result.output


def test_issue_help(runner):
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
