"""Tests for Desktop Application Update Integration Hook & IPC Service Bridge."""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.desktop_update_bridge import DesktopNotificationEvent, DesktopUpdateBridge
from app.services.update_service import ReleaseChannel, UpdateInfo, UpdateService, UpdateStatus


@pytest.fixture
def mock_update_service():
    """Mock UpdateService instance."""
    service = MagicMock(spec=UpdateService)
    service.current_version = "1.0.0"
    service.get_settings.return_value = {
        "channel": "stable",
        "auto_download": False,
        "auto_restart": True,
        "last_check": "2026-07-30T00:00:00Z",
    }
    service.check_for_updates.return_value = {
        "current_version": "1.0.0",
        "status": "update-available",
        "latest_version": "1.1.0",
        "update": {
            "version": "1.1.0",
            "channel": "stable",
            "download_url": "https://example.com/amf-1.1.0.zip",
            "size": 1024,
        },
    }
    service.download_update_with_retry.return_value = {
        "success": True,
        "version": "1.1.0",
        "path": "/tmp/amf-1.1.0.zip",
        "size": 1024,
        "checksum_valid": True,
        "signature_valid": True,
    }
    service.install_update.return_value = {
        "success": True,
        "version": "1.1.0",
        "previous_version": "1.0.0",
        "backup_path": "/tmp/backup_v1.0.0",
    }
    service._pending_update = None
    return service


def test_notification_event():
    event = DesktopNotificationEvent(
        event_type="update_available",
        data={"version": "1.1.0"},
        version="1.1.0",
    )
    d = event.to_dict()
    assert d["event_type"] == "update_available"
    assert d["version"] == "1.1.0"
    assert d["data"] == {"version": "1.1.0"}
    assert "timestamp" in d


def test_desktop_bridge_init(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    status = bridge.get_bridge_status()
    assert status["platform"] == platform.system()
    assert status["current_version"] == "1.0.0"
    assert status["active_channel"] == "stable"
    assert status["is_polling"] is False


def test_listeners_registration(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    received_events = []

    def callback(evt: DesktopNotificationEvent):
        received_events.append(evt)

    bridge.register_listener("update_available", callback)
    evt = bridge.emit_notification("update_available", {"version": "1.1.0"}, version="1.1.0")

    assert len(received_events) == 1
    assert received_events[0].event_type == "update_available"

    bridge.unregister_listener("update_available", callback)
    bridge.emit_notification("update_available", {"version": "1.1.0"}, version="1.1.0")
    assert len(received_events) == 1


def test_check_now(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    received_events = []

    bridge.register_listener("update_available", lambda e: received_events.append(e))
    res = bridge.check_now(channel="stable")

    assert res["status"] == "update-available"
    assert len(received_events) == 1
    assert received_events[0].version == "1.1.0"


def test_download_update(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    received = []

    bridge.register_listener("download_complete", lambda e: received.append(e))
    res = bridge.download_update(version="1.1.0")

    assert res["success"] is True
    assert len(received) == 1
    assert received[0].event_type == "download_complete"


def test_polling_lifecycle(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    with patch.object(bridge, "check_now", return_value={"status": "up-to-date"}):
        started = bridge.start_polling(interval_seconds=3600)
        assert started is True
        assert bridge._is_polling is True

        assert bridge.start_polling(interval_seconds=3600) is False

        stopped = bridge.stop_polling()
        assert stopped is True
        assert bridge._is_polling is False


def test_launch_installer_missing_file(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    res = bridge.launch_installer("/nonexistent/file/path.exe")
    assert res["success"] is False
    assert "not found" in res["error"]


@patch("subprocess.Popen")
def test_launch_installer_windows(mock_popen, mock_update_service, tmp_path):
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    mock_popen.return_value = mock_proc

    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"dummy setup")

    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    res = bridge.launch_installer(installer, platform_type="windows")

    assert res["success"] is True
    assert res["pid"] == 1234
    assert res["platform"] == "windows"


def test_install_and_launch(mock_update_service):
    bridge = DesktopUpdateBridge(update_service=mock_update_service)
    with patch.object(bridge, "restart_application") as mock_restart:
        res = bridge.install_and_launch(version="1.1.0", auto_restart=True)
        assert res["success"] is True
        mock_restart.assert_called_once()
