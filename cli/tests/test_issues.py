"""Tests for issue management CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
import sys

# Mock backend modules for CLI tests
sys.modules["app"] = MagicMock()
sys.modules["app.services"] = MagicMock()
sys.modules["app.services.issue_service"] = MagicMock()

from amf.main import cli


@pytest.fixture
def mock_issue_service():
    with patch("amf.commands.issues._get_service") as mock_get_service:
        instance = MagicMock()
        mock_get_service.return_value = instance
        instance.submit_issue.return_value = {
            "id": "test-id", "tracking_number": "AMF-250726-0001",
            "title": "Test", "description": "Testing",
            "category": "bug", "severity": "medium", "status": "new",
            "source": "cli", "created_at": "2026-07-25T10:00:00",
            "comments": [], "timeline": [],
        }
        instance.get_issue.return_value = {
            "id": "test-id", "tracking_number": "AMF-250726-0001",
            "title": "Test Bug", "description": "Description here",
            "category": "bug", "severity": "high", "status": "new",
            "source": "cli", "created_at": "2026-07-25T10:00:00",
            "updated_at": "2026-07-25T10:00:00", "comments": [],
            "timeline": [], "labels": ["bug"],
        }
        instance.list_issues.return_value = [
            {"id": "1", "tracking_number": "AMF-001", "title": "Bug 1",
             "category": "bug", "severity": "high", "status": "new",
             "created_at": "2026-07-25T10:00:00", "assigned_to": None},
            {"id": "2", "tracking_number": "AMF-002", "title": "Bug 2",
             "category": "bug", "severity": "medium", "status": "in-progress",
             "created_at": "2026-07-25T11:00:00", "assigned_to": "dev1"},
        ]
        instance.add_comment.return_value = {"tracking_number": "AMF-001"}
        instance.update_issue.return_value = {"tracking_number": "AMF-001", "status": "resolved"}
        instance.get_stats.return_value = {
            "total_issues": 10, "open_issues": 5, "resolved_issues": 3,
            "critical_issues": 1, "by_status": {}, "by_category": {},
            "by_severity": {}, "sla_breaches": 0, "total_comments": 15,
            "avg_resolution_time_hours": 24,
        }
        instance.check_sla.return_value = []
        instance.list_labels.return_value = {"bug": {"name": "bug", "color": "#d73a4a", "description": "Bug"}}
        yield instance


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
