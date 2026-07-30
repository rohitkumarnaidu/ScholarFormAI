"""Desktop Application Update Integration Hook & IPC Service Bridge.

Provides background polling, native notification signals, platform-specific
installer launching (Windows .exe/.msi, macOS .dmg/.pkg, Linux .AppImage), and process restart handlers.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.services.update_service import ReleaseChannel, UpdateService, UpdateStatus

logger = logging.getLogger(__name__)


class DesktopNotificationEvent:
    """Represents a native desktop notification event."""

    def __init__(self, event_type: str, data: dict[str, Any], version: str | None = None):
        self.event_type = event_type
        self.data = data
        self.version = version
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "version": self.version,
            "timestamp": self.timestamp,
        }


class DesktopUpdateBridge:
    """
    Bridge service integrating ScholarFormAI UpdateService with Desktop Applications
    (Electron, Tauri, PyQt, Custom Native Apps).

    Features:
    - Thread-safe background polling loop
    - Native desktop notification signal emitter
    - IPC event listener registry
    - Platform-specific installer launcher (.exe, .msi, .dmg, .pkg, .AppImage)
    - Safe process restart handler
    """

    def __init__(self, update_service: UpdateService | None = None):
        self.service = update_service or UpdateService()
        self._listeners: dict[str, list[Callable[[DesktopNotificationEvent], None]]] = {
            "update_available": [],
            "download_progress": [],
            "download_complete": [],
            "install_started": [],
            "install_complete": [],
            "error": [],
            "status_changed": [],
        }
        self._listener_lock = threading.Lock()
        self._polling_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._is_polling = False
        self._last_notification: DesktopNotificationEvent | None = None

    # ------------------------------------------------------------------
    # Notification & Event Listener System
    # ------------------------------------------------------------------

    def register_listener(self, event_type: str, callback: Callable[[DesktopNotificationEvent], None]) -> None:
        """Register a callback for desktop update events."""
        with self._listener_lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def unregister_listener(self, event_type: str, callback: Callable[[DesktopNotificationEvent], None]) -> None:
        """Unregister an existing event callback."""
        with self._listener_lock:
            if event_type in self._listeners and callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

    def emit_notification(self, event_type: str, data: dict[str, Any], version: str | None = None) -> DesktopNotificationEvent:
        """Emit notification signal to registered callbacks and desktop environment."""
        event = DesktopNotificationEvent(event_type=event_type, data=data, version=version)
        self._last_notification = event

        with self._listener_lock:
            callbacks = list(self._listeners.get(event_type, []))
            all_callbacks = list(self._listeners.get("status_changed", []))

        for cb in callbacks + all_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error("Error executing desktop notification callback for %s: %s", event_type, e)

        return event

    # ------------------------------------------------------------------
    # Polling Loop
    # ------------------------------------------------------------------

    def start_polling(self, interval_seconds: int = 3600, channel: str | None = None) -> bool:
        """Start background polling thread for update checks."""
        if self._is_polling:
            logger.info("Polling loop already running.")
            return False

        self._stop_event.clear()
        self._is_polling = True
        self._polling_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_seconds, channel),
            daemon=True,
            name="DesktopUpdateBridgePolling",
        )
        self._polling_thread.start()
        logger.info("Started desktop update polling loop (interval=%ds)", interval_seconds)
        return True

    def stop_polling(self) -> bool:
        """Signal background polling thread to terminate."""
        if not self._is_polling:
            return False

        self._stop_event.set()
        self._is_polling = False
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=3.0)
        logger.info("Stopped desktop update polling loop.")
        return True

    def _poll_loop(self, interval_seconds: int, channel: str | None):
        while not self._stop_event.is_set():
            try:
                res = self.check_now(channel=channel)
                if res.get("status") == UpdateStatus.UPDATE_AVAILABLE.value:
                    upd = res.get("update", {})
                    self.emit_notification(
                        event_type="update_available",
                        data=res,
                        version=upd.get("version"),
                    )

                    # Handle auto-download if enabled in settings
                    if self.service.get_settings().get("auto_download"):
                        dl_res = self.service.download_update_with_retry(version=upd.get("version"))
                        if dl_res.get("success"):
                            self.emit_notification(
                                event_type="download_complete",
                                data=dl_res,
                                version=upd.get("version"),
                            )
            except Exception as e:
                logger.error("Polling check failed: %s", e)
                self.emit_notification("error", {"error": str(e)})

            self._stop_event.wait(timeout=interval_seconds)

    def check_now(self, channel: str | None = None) -> dict[str, Any]:
        """Trigger an immediate update check and emit event."""
        res = self.service.check_for_updates(channel=channel)
        if res.get("status") == UpdateStatus.UPDATE_AVAILABLE.value:
            upd = res.get("update", {})
            self.emit_notification("update_available", res, version=upd.get("version"))
        return res

    # ------------------------------------------------------------------
    # Download & Install Bridge Operations
    # ------------------------------------------------------------------

    def download_update(self, version: str | None = None, retries: int = 3) -> dict[str, Any]:
        """Download update payload with progress callbacks and desktop signal emission."""
        def progress_cb(downloaded: int, total: int):
            percent = (downloaded / total * 100) if total else 0
            self.emit_notification(
                "download_progress",
                {"downloaded": downloaded, "total": total, "percent": round(percent, 2)},
                version=version,
            )

        res = self.service.download_update_with_retry(
            version=version, max_retries=retries, progress_callback=progress_cb
        )
        if res.get("success"):
            self.emit_notification("download_complete", res, version=res.get("version"))
        else:
            self.emit_notification("error", res, version=version)
        return res

    def install_and_launch(
        self,
        version: str | None = None,
        source_path: str | Path | None = None,
        auto_restart: bool = True,
    ) -> dict[str, Any]:
        """Execute atomic installation and launch installer / restart process."""
        self.emit_notification("install_started", {"version": version})

        res = self.service.install_update(version=version, source_path=source_path)

        if not res.get("success"):
            self.emit_notification("error", res, version=version)
            return res

        self.emit_notification("install_complete", res, version=res.get("version"))

        if auto_restart and self.service.get_settings().get("auto_restart", True):
            self.restart_application()

        return res

    # ------------------------------------------------------------------
    # Platform-Specific Installer Launcher
    # ------------------------------------------------------------------

    def launch_installer(
        self,
        installer_path: str | Path,
        platform_type: str | None = None,
        quiet: bool = True,
    ) -> dict[str, Any]:
        """Launch platform-specific installer (.exe, .msi, .dmg, .pkg, .AppImage)."""
        path = Path(installer_path)
        if not path.exists():
            return {"success": False, "error": f"Installer file not found: {path}"}

        target_platform = (platform_type or platform.system()).lower()
        suffix = path.suffix.lower()

        try:
            if "win" in target_platform:
                if suffix == ".msi":
                    args = ["msiexec", "/i", str(path)]
                    if quiet:
                        args.append("/qn")
                    proc = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else: # .exe or fallback
                    args = [str(path)]
                    if quiet:
                        args.append("/S")
                    proc = subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
                return {"success": True, "pid": proc.pid, "platform": "windows", "installer": str(path)}

            elif "darwin" in target_platform or "mac" in target_platform:
                if suffix == ".dmg":
                    proc = subprocess.Popen(["hdiutil", "attach", str(path)])
                elif suffix == ".pkg":
                    args = ["installer", "-pkg", str(path), "-target", "/"]
                    proc = subprocess.Popen(args)
                else:
                    proc = subprocess.Popen(["open", str(path)])
                return {"success": True, "pid": proc.pid, "platform": "macos", "installer": str(path)}

            else: # Linux / Unix
                if suffix == ".appimage":
                    os.chmod(path, 0o755)
                    proc = subprocess.Popen([str(path)])
                elif suffix == ".deb":
                    proc = subprocess.Popen(["dpkg", "-i", str(path)])
                else: # .tar.gz or raw binary
                    proc = subprocess.Popen(["chmod", "+x", str(path)])
                    proc = subprocess.Popen([str(path)])
                return {"success": True, "pid": proc.pid, "platform": "linux", "installer": str(path)}

        except Exception as e:
            logger.error("Failed to launch installer %s: %s", path, e)
            return {"success": False, "error": f"Failed to launch installer: {e}"}

    # ------------------------------------------------------------------
    # Process Restart Handler
    # ------------------------------------------------------------------

    def restart_application(
        self,
        app_binary: str | Path | None = None,
        args: list[str] | None = None,
        delay_seconds: float = 1.0,
    ) -> None:
        """Safe application restart handler."""
        logger.info("Restarting application in %.1fs...", delay_seconds)
        time.sleep(delay_seconds)

        executable = str(app_binary) if app_binary else sys.executable
        exec_args = args if args is not None else sys.argv

        try:
            if platform.system().lower() == "windows":
                cmd = [executable] + exec_args[1:]
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
                sys.exit(0)
            else:
                os.execv(executable, [executable] + exec_args[1:])
        except Exception as e:
            logger.error("Failed to restart application: %s", e)
            sys.exit(1)

    # ------------------------------------------------------------------
    # IPC Status Bridge
    # ------------------------------------------------------------------

    def get_bridge_status(self) -> dict[str, Any]:
        """Return full desktop update bridge status IPC payload."""
        with self._listener_lock:
            listeners_count = sum(len(cbs) for cbs in self._listeners.values())

        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "is_polling": self._is_polling,
            "current_version": self.service.current_version,
            "active_channel": self.service.get_settings().get("channel", "stable"),
            "pending_update": self.service._pending_update.to_dict() if self.service._pending_update else None,
            "listeners_count": listeners_count,
            "last_check": self.service.get_settings().get("last_check"),
            "last_notification": self._last_notification.to_dict() if self._last_notification else None,
        }
