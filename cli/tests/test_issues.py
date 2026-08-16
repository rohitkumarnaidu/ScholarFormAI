"""Tests for issue management CLI commands."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock backend modules for CLI tests
sys.modules["app"] = MagicMock()
sys.modules["app.services"] = MagicMock()
sys.modules["app.services.issue_service"] = MagicMock()

from amf.main import cli


def test_issue_report(runner):
    result = runner.invoke(cli, ["issue", "report", "-t", "Test Bug", "-d", "Found a bug", "-c", "bug"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_report_with_all_options(runner):
    result = runner.invoke(cli, ["issue", "report", "-t", "Test", "-d", "Desc", "-c", "performance", "-s", "high", "-n", "User", "-e", "u@test.com"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_list(runner):
    result = runner.invoke(cli, ["issue", "list"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_list_with_filters(runner):
    result = runner.invoke(cli, ["issue", "list", "--status", "new", "--category", "bug"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_show(runner):
    result = runner.invoke(cli, ["issue", "show", "test-id"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_comment(runner):
    result = runner.invoke(cli, ["issue", "comment", "test-id", "-b", "I found the issue"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_update(runner):
    result = runner.invoke(cli, ["issue", "update", "test-id", "--status", "resolved"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_search(runner):
    result = runner.invoke(cli, ["issue", "search", "bug"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_stats(runner):
    result = runner.invoke(cli, ["issue", "stats"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_labels(runner):
    result = runner.invoke(cli, ["issue", "labels"])
    assert result.exit_code == 0
    assert "This feature is now managed via the Enterprise Web Dashboard" in result.output


def test_issue_help(runner):
    result = runner.invoke(cli, ["issue", "--help"])
    assert result.exit_code == 0
