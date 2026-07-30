"""Tests for update management CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from amf.main import cli

@pytest.fixture
def mock_update_service():
    """Mock the UpdateService to avoid network calls."""
    with patch("amf.commands.update._get_update_service") as mock_get_service:
        instance = MagicMock()
        mock_get_service.return_value = instance

        instance.check_for_updates.return_value = {
            "status": "up-to-date",
            "current_version": "1.0.0",
            "latest_version": "1.0.0",
            "update": None,
            "check_mode": "manual",
            "checked_at": "2026-07-25T10:00:00",
        }

        instance.download_update.return_value = {
            "success": True,
            "version": "1.1.0",
            "path": "/tmp/amf-1.1.0.zip",
            "size": 1024000,
            "checksum_valid": True,
        }

        instance.install_update.return_value = {
            "success": True,
            "version": "1.1.0",
            "previous_version": "1.0.0",
            "backup_path": "/tmp/backup",
        }

        instance.rollback.return_value = {
            "success": True,
            "version": "1.0.0",
        }

        instance.get_history.return_value = [
            {
                "version": "1.1.0",
                "channel": "stable",
                "installed_at": "2026-07-25T10:00:00",
                "checksum": "abc",
                "checksum_type": "sha256",
                "success": True,
                "error_message": None,
                "rolled_back": False,
                "rollback_version": None,
            },
            {
                "version": "1.0.0",
                "channel": "stable",
                "installed_at": "2026-06-01T10:00:00",
                "checksum": "def",
                "checksum_type": "sha256",
                "success": True,
                "error_message": None,
                "rolled_back": False,
                "rollback_version": None,
            },
        ]

        instance.get_channels.return_value = [
            {"id": "stable", "name": "Stable", "description": "Production-ready", "recommended": True},
            {"id": "beta", "name": "Beta", "description": "Pre-release", "recommended": False},
        ]

        instance.get_settings.return_value = {
            "channel": "stable",
            "auto_check": True,
            "auto_download": False,
            "auto_install": False,
            "check_frequency_hours": 24,
        }

        instance.verify_asset_integrity.return_value = {
            "valid": True,
            "exists": True,
            "file_name": "amf-1.1.0.zip",
            "path": "/tmp/amf-1.1.0.zip",
            "size_bytes": 1024000,
            "checksum_algo": "sha256",
            "expected_checksum": None,
            "calculated_sha256": "abc123def4567890",
            "checksum_valid": True,
            "signature_provided": False,
            "signature_valid": True,
        }

        instance.get_release_notes.return_value = {
            "version": "1.1.0",
            "name": "v1.1.0",
            "published_at": "2026-07-25T10:00:00",
            "found": True,
            "body": "## Release Notes\n- Bug fixes and stability improvements.",
            "changelog": ["Bug fixes and stability improvements."],
        }

        yield instance



def test_update_check(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "check"])
    assert result.exit_code == 0
    assert "up to date" in result.output.lower() or "current" in result.output.lower()


def test_update_check_json(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "check", "--json"])
    assert result.exit_code == 0
    assert '"status": "up-to-date"' in result.output


def test_update_check_with_channel(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "check", "--channel", "beta"])
    assert result.exit_code == 0


def test_update_download(runner: CliRunner, mock_update_service):
    mock_update_service.check_for_updates.return_value = {
        "status": "update-available",
        "current_version": "1.0.0",
        "latest_version": "1.1.0",
        "update": {"version": "1.1.0", "size": 1024000, "channel": "stable"},
        "check_mode": "manual",
        "checked_at": "2026-07-25T10:00:00",
    }
    mock_update_service.download_update_with_retry.return_value = {
        "success": True,
        "version": "1.1.0",
        "path": "/tmp/amf-1.1.0.zip",
        "size": 1024000,
        "checksum_valid": True,
    }
    result = runner.invoke(cli, ["update", "download"])
    assert result.exit_code == 0


def test_update_download_version(runner: CliRunner, mock_update_service):
    mock_update_service.check_for_updates.return_value = {
        "status": "update-available",
        "current_version": "1.0.0",
        "latest_version": "1.1.0",
        "update": {"version": "1.1.0", "size": 1024000, "channel": "stable"},
        "check_mode": "manual",
        "checked_at": "2026-07-25T10:00:00",
    }
    mock_update_service.download_update_with_retry.return_value = {
        "success": True,
        "version": "1.1.0",
        "path": "/tmp/amf-1.1.0.zip",
        "size": 1024000,
        "checksum_valid": True,
    }
    result = runner.invoke(cli, ["update", "download", "--version", "1.1.0"])
    assert result.exit_code == 0


def test_update_verify(runner: CliRunner, mock_update_service, tmp_path):
    test_file = tmp_path / "amf-1.1.0.zip"
    test_file.write_bytes(b"dummy data")
    result = runner.invoke(cli, ["update", "verify", "--file", str(test_file)])
    assert result.exit_code == 0
    assert "Verification Report" in result.output or "VERIFIED" in result.output


def test_update_install(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "install"])
    assert result.exit_code == 0
    assert "Installed" in result.output


def test_update_offline(runner: CliRunner, mock_update_service, tmp_path):
    pkg_file = tmp_path / "amf-1.1.0.tar.gz"
    pkg_file.write_bytes(b"offline package data")
    result = runner.invoke(cli, ["update", "offline", str(pkg_file)])
    assert result.exit_code == 0
    assert "Successfully installed" in result.output or "offline" in result.output.lower()


def test_update_rollback(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "rollback"])
    assert result.exit_code == 0
    assert "Rolled back" in result.output


def test_update_history(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "history"])
    assert result.exit_code == 0
    assert "1.1.0" in result.output


def test_update_channels(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "channels"])
    assert result.exit_code == 0
    assert "stable" in result.output


def test_update_channel_switch(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "channel", "beta"])
    assert result.exit_code == 0


def test_update_settings_show(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "settings"])
    assert result.exit_code == 0
    assert "channel" in result.output


def test_update_settings_update(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "settings", "--channel", "beta", "--auto-download"])
    assert result.exit_code == 0


def test_update_release_notes(runner: CliRunner, mock_update_service):
    result = runner.invoke(cli, ["update", "release-notes", "1.1.0"])
    assert result.exit_code == 0


def test_update_help(runner: CliRunner):
    result = runner.invoke(cli, ["update", "--help"])
    assert result.exit_code == 0

