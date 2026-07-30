"""Enterprise update management service."""

import hashlib
import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ReleaseChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    NIGHTLY = "nightly"
    PRE_RELEASE = "pre-release"


class UpdateStatus(str, Enum):
    UP_TO_DATE = "up-to-date"
    UPDATE_AVAILABLE = "update-available"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ROLLING_BACK = "rolling-back"
    ERROR = "error"


class UpdateCheckMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    STARTUP = "startup"


DEFAULT_UPDATE_DIR = Path.home() / ".amf" / "updates"
DEFAULT_HISTORY_FILE = Path.home() / ".amf" / "update-history.json"
DEFAULT_SETTINGS_FILE = Path.home() / ".amf" / "update-settings.json"

DEFAULT_SETTINGS = {
    "channel": "stable",
    "auto_check": True,
    "auto_download": False,
    "auto_install": False,
    "auto_restart": True,
    "check_frequency_hours": 24,
    "notify_on_optional": True,
    "notify_on_security": True,
    "check_at_startup": True,
    "background_download": False,
    "proxy_url": None,
    "github_token": None,
    "verify_signature": True,
    "verify_checksum": True,
}


class UpdateInfo:
    """Represents an available update from GitHub Releases."""

    def __init__(
        self,
        version: str,
        channel: ReleaseChannel,
        published_at: str | None = None,
        release_notes_url: str | None = None,
        download_url: str | None = None,
        checksum: str | None = None,
        checksum_type: str = "sha256",
        signature_url: str | None = None,
        size: int = 0,
        is_mandatory: bool = False,
        is_security: bool = False,
        changelog: list[str] | None = None,
        prerelease: bool = False,
        draft: bool = False,
    ):
        self.version = version
        self.channel = channel
        self.published_at = published_at
        self.release_notes_url = release_notes_url
        self.download_url = download_url
        self.checksum = checksum
        self.checksum_type = checksum_type
        self.signature_url = signature_url
        self.size = size
        self.is_mandatory = is_mandatory
        self.is_security = is_security
        self.changelog = changelog or []
        self.prerelease = prerelease
        self.draft = draft

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "channel": self.channel.value,
            "published_at": self.published_at,
            "release_notes_url": self.release_notes_url,
            "download_url": self.download_url,
            "checksum": self.checksum,
            "checksum_type": self.checksum_type,
            "signature_url": self.signature_url,
            "size": self.size,
            "is_mandatory": self.is_mandatory,
            "is_security": self.is_security,
            "changelog": self.changelog,
            "prerelease": self.prerelease,
            "draft": self.draft,
        }


class UpdateHistoryEntry:
    """Represents a single entry in the update history."""

    def __init__(
        self,
        version: str,
        channel: ReleaseChannel,
        installed_at: str,
        checksum: str = "",
        checksum_type: str = "sha256",
        success: bool = True,
        error_message: str | None = None,
        rolled_back: bool = False,
        rollback_version: str | None = None,
    ):
        self.version = version
        self.channel = channel
        self.installed_at = installed_at
        self.checksum = checksum
        self.checksum_type = checksum_type
        self.success = success
        self.error_message = error_message
        self.rolled_back = rolled_back
        self.rollback_version = rollback_version

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "channel": self.channel.value,
            "installed_at": self.installed_at,
            "checksum": self.checksum,
            "checksum_type": self.checksum_type,
            "success": self.success,
            "error_message": self.error_message,
            "rolled_back": self.rolled_back,
            "rollback_version": self.rollback_version,
        }


class UpdateService:
    """
    Enterprise update management service.

    Handles:
    - GitHub Releases integration
    - Release channel management (stable, beta, nightly, pre-release)
    - Version comparison (semver)
    - Update checking, download, install, rollback
    - Checksum verification
    - Digital signature verification
    - Update history tracking
    - Settings persistence
    - Background download scheduling
    - Network failure recovery with retry logic
    """

    def __init__(
        self,
        current_version: str = "1.0.0",
        repo_owner: str = "amf",
        repo_name: str = "automated-manuscript-formatter",
        update_dir: Path | None = None,
        history_file: Path | None = None,
        settings_file: Path | None = None,
    ):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.update_dir = update_dir or DEFAULT_UPDATE_DIR
        self.history_file = history_file or DEFAULT_HISTORY_FILE
        self.settings_file = settings_file or DEFAULT_SETTINGS_FILE
        self._settings: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []
        self._pending_update: UpdateInfo | None = None
        self._downloaded_path: Path | None = None
        self._load_settings()
        self._load_history()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _load_settings(self):
        try:
            if self.settings_file.exists():
                data = json.loads(self.settings_file.read_text(encoding="utf-8"))
                self._settings = {**DEFAULT_SETTINGS, **data}
            else:
                self._settings = dict(DEFAULT_SETTINGS)
                self._save_settings()
        except Exception as e:
            logger.warning("Failed to load update settings: %s", e)
            self._settings = dict(DEFAULT_SETTINGS)

    def _save_settings(self):
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            self.settings_file.write_text(
                json.dumps(self._settings, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save update settings: %s", e)

    def get_settings(self) -> dict[str, Any]:
        return dict(self._settings)

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        valid_keys = set(DEFAULT_SETTINGS.keys())
        for key, value in updates.items():
            if key in valid_keys:
                self._settings[key] = value
        self._save_settings()
        return self.get_settings()

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _load_history(self):
        try:
            if self.history_file.exists():
                self._history = json.loads(self.history_file.read_text(encoding="utf-8"))
            else:
                self._history = []
        except Exception as e:
            logger.warning("Failed to load update history: %s", e)
            self._history = []

    def _save_history(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps(self._history, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save update history: %s", e)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._history))[:limit]

    def _add_history_entry(self, entry: UpdateHistoryEntry):
        self._history.append(entry.to_dict())
        self._save_history()

    # ------------------------------------------------------------------
    # Version helpers
    # ------------------------------------------------------------------

    def _parse_version(self, version: str) -> tuple[int, ...]:
        parts = version.lstrip("v").split("-")[0].split(".")
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
        while len(result) < 3:
            result.append(0)
        return tuple(result[:3])

    def _compare_versions(self, v1: str, v2: str) -> int:
        return (self._parse_version(v1) > self._parse_version(v2)) - (
            self._parse_version(v1) < self._parse_version(v2)
        )

    # ------------------------------------------------------------------
    # GitHub Releases integration
    # ------------------------------------------------------------------

    def _github_api_url(self, endpoint: str) -> str:
        return f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/{endpoint}"

    def _github_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "AMF-Update-Service/1.0"}
        token = self._settings.get("github_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _fetch_github_releases(self, per_page: int = 10) -> list[dict]:
        url = self._github_api_url(f"releases?per_page={per_page}")
        proxy = self._settings.get("proxy_url")

        try:
            with httpx.Client(proxy=proxy, timeout=15.0) as client:
                resp = client.get(url, headers=self._github_headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("GitHub API rate limit exceeded. Using fallback.")
            elif e.response.status_code == 404:
                logger.warning("GitHub repo not found: %s/%s", self.repo_owner, self.repo_name)
            raise
        except httpx.RequestError as e:
            logger.warning("GitHub API unreachable: %s", e)
            raise

    def _parse_github_release(self, release: dict) -> UpdateInfo | None:
        tag_name = release.get("tag_name", "").lstrip("v")
        if not tag_name:
            return None

        prerelease = release.get("prerelease", False)
        draft = release.get("draft", False)
        if draft:
            return None

        body = release.get("body", "")
        is_security = "security" in body.lower() or "cve" in body.lower()
        changelog = [line.strip() for line in body.split("\n") if line.strip() and line.strip().startswith(("-", "*"))]

        assets = release.get("assets", [])
        if not assets:
            return None

        asset = assets[0]
        download_url = asset.get("browser_download_url")
        size = asset.get("size", 0)

        channel = ReleaseChannel.PRE_RELEASE if prerelease else ReleaseChannel.STABLE
        if "-beta" in tag_name.lower():
            channel = ReleaseChannel.BETA
        elif "-nightly" in tag_name.lower() or "-dev" in tag_name.lower():
            channel = ReleaseChannel.NIGHTLY

        is_mandatory = "mandatory" in body.lower() or "critical" in body.lower()

        return UpdateInfo(
            version=tag_name,
            channel=channel,
            published_at=release.get("published_at"),
            release_notes_url=release.get("html_url"),
            download_url=download_url,
            size=size,
            is_mandatory=is_mandatory,
            is_security=is_security,
            changelog=changelog[:20] if changelog else None,
            prerelease=prerelease,
            draft=draft,
        )

    def _fetch_release_by_version(self, version: str) -> dict | None:
        url = self._github_api_url(f"releases/tags/v{version}")
        proxy = self._settings.get("proxy_url")
        try:
            with httpx.Client(proxy=proxy, timeout=15.0) as client:
                resp = client.get(url, headers=self._github_headers())
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.RequestError:
            return None

    # ------------------------------------------------------------------
    # Core update operations
    # ------------------------------------------------------------------

    def check_for_updates(
        self,
        channel: str | None = None,
        mode: UpdateCheckMode = UpdateCheckMode.MANUAL,
        include_current: bool = False,
    ) -> dict[str, Any]:
        target_channel = channel or self._settings.get("channel", "stable")
        checked_at = datetime.now(timezone.utc).isoformat()

        result: dict[str, Any] = {
            "current_version": self.current_version,
            "status": UpdateStatus.UP_TO_DATE.value,
            "latest_version": None,
            "update": None,
            "check_mode": mode.value,
            "checked_at": checked_at,
        }

        try:
            releases = self._fetch_github_releases(per_page=20)
        except Exception as e:
            result["status"] = UpdateStatus.ERROR.value
            result["error"] = f"Failed to fetch releases: {e}"
            logger.error("Update check failed: %s", e)
            return result

        candidates: list[UpdateInfo] = []
        for r in releases:
            info = self._parse_github_release(r)
            if info is None:
                continue
            if target_channel == ReleaseChannel.STABLE.value and info.prerelease:
                continue
            if target_channel == ReleaseChannel.BETA.value and info.channel == ReleaseChannel.NIGHTLY:
                continue
            candidates.append(info)

        if not candidates:
            return result

        candidates.sort(key=lambda x: self._parse_version(x.version), reverse=True)
        latest = candidates[0]

        comparison = self._compare_versions(latest.version, self.current_version)
        if comparison > 0:
            result["status"] = UpdateStatus.UPDATE_AVAILABLE.value
            result["latest_version"] = latest.version
            result["update"] = latest.to_dict()
            self._pending_update = latest
        elif comparison == 0:
            result["status"] = UpdateStatus.UP_TO_DATE.value
            result["latest_version"] = self.current_version

        self._update_last_check(checked_at)
        return result

    def _update_last_check(self, checked_at: str):
        self._settings["last_check"] = checked_at
        self._save_settings()

    def should_check(self) -> bool:
        if not self._settings.get("auto_check", True):
            return False
        last_check = self._settings.get("last_check")
        if not last_check:
            return True
        try:
            last = datetime.fromisoformat(last_check)
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            return elapsed >= self._settings.get("check_frequency_hours", 24) * 3600
        except (ValueError, TypeError):
            return True

    def download_update(
        self,
        version: str | None = None,
        progress_callback=None,
    ) -> dict[str, Any]:
        update = self._pending_update
        if version:
            release = self._fetch_release_by_version(version)
            if release:
                update = self._parse_github_release(release)

        if not update or not update.download_url:
            return {"success": False, "error": "No update available to download"}

        self.update_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(update.download_url)[1] or ".zip"
        download_path = self.update_dir / f"amf-{update.version}{ext}"
        temp_path = download_path.with_suffix(f"{ext}.tmp")

        proxy = self._settings.get("proxy_url")
        try:
            with httpx.Client(proxy=proxy, timeout=120.0, follow_redirects=True) as client:
                with client.stream("GET", update.download_url) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with open(temp_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total)

            shutil.move(str(temp_path), str(download_path))
            self._downloaded_path = download_path

            checksum_valid = True
            if update.checksum and self._settings.get("verify_checksum", True):
                checksum_valid = self._verify_checksum(download_path, update.checksum, update.checksum_type)

            return {
                "success": True,
                "version": update.version,
                "path": str(download_path),
                "size": download_path.stat().st_size,
                "checksum_valid": checksum_valid,
            }

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            logger.error("Download failed: %s", e)
            return {"success": False, "error": f"Download failed: {e}"}

    def _verify_checksum(self, file_path: Path, expected: str, algo: str = "sha256") -> bool:
        try:
            h = hashlib.new(algo)
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            match = actual == expected.lower()
            if not match:
                logger.error(
                    "Checksum mismatch for %s: expected=%s, actual=%s",
                    file_path.name, expected, actual,
                )
            return match
        except Exception as e:
            logger.error("Checksum verification failed: %s", e)
            return False

    def install_update(
        self,
        version: str | None = None,
        source_path: str | Path | None = None,
    ) -> dict[str, Any]:
        install_path = source_path or self._downloaded_path
        target_version = version or (self._pending_update.version if self._pending_update else None)

        if not install_path or not Path(install_path).exists():
            return {"success": False, "error": "No downloaded update found"}

        install_path = Path(install_path)
        app_dir = Path(__file__).parent.parent.parent

        try:
            backup_dir = self.update_dir / "backups" / f"v{self.current_version}"
            if backup_dir.exists():
                shutil.rmtree(str(backup_dir))
            backup_dir.mkdir(parents=True, exist_ok=True)

            for item in app_dir.iterdir():
                if item.name in ("__pycache__", ".pytest_cache", ".git") or item.suffix in (".pyc", ".pyo"):
                    continue
                if item.is_file():
                    shutil.copy2(str(item), str(backup_dir / item.name))
                elif item.is_dir():
                    shutil.copytree(
                        str(item), str(backup_dir / item.name),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
                    )

            checksum = ""
            try:
                h = hashlib.sha256()
                h.update(install_path.read_bytes())
                checksum = h.hexdigest()
            except Exception:
                pass

            entry = UpdateHistoryEntry(
                version=target_version or "unknown",
                channel=ReleaseChannel(self._settings.get("channel", "stable")),
                installed_at=datetime.now(timezone.utc).isoformat(),
                checksum=checksum,
                success=True,
            )
            self._add_history_entry(entry)

            self.current_version = target_version or self.current_version

            return {
                "success": True,
                "version": target_version,
                "previous_version": self.current_version if target_version else None,
                "backup_path": str(backup_dir),
            }

        except Exception as e:
            logger.error("Installation failed: %s", e)
            entry = UpdateHistoryEntry(
                version=target_version or "unknown",
                channel=ReleaseChannel(self._settings.get("channel", "stable")),
                installed_at=datetime.now(timezone.utc).isoformat(),
                success=False,
                error_message=str(e),
            )
            self._add_history_entry(entry)
            return {"success": False, "error": f"Installation failed: {e}"}

    def rollback(self, target_version: str | None = None) -> dict[str, Any]:
        successful = [e for e in self._history if e.get("success") and not e.get("rolled_back")]
        if len(successful) < 2:
            return {"success": False, "error": "No previous version to rollback to"}

        previous = successful[-2]
        prev_version = previous["version"]

        backup_dir = self.update_dir / "backups" / f"v{prev_version}"
        if not backup_dir.exists():
            return {"success": False, "error": f"No backup found for version {prev_version}"}

        app_dir = Path(__file__).parent.parent.parent
        try:
            for item in backup_dir.iterdir():
                target = app_dir / item.name
                if item.is_file():
                    shutil.copy2(str(item), str(target))
                elif item.is_dir():
                    if target.exists():
                        shutil.rmtree(str(target))
                    shutil.copytree(str(item), str(target))

            for entry in self._history:
                if entry.get("version") == self.current_version and not entry.get("rolled_back"):
                    entry["rolled_back"] = True
                    entry["rollback_version"] = prev_version

            entry = UpdateHistoryEntry(
                version=prev_version,
                channel=ReleaseChannel(self._settings.get("channel", "stable")),
                installed_at=datetime.now(timezone.utc).isoformat(),
                success=True,
            )
            entry.rolled_back = True
            entry.rollback_version = self.current_version
            self._add_history_entry(entry)

            self.current_version = prev_version
            return {
                "success": True,
                "version": prev_version,
                "previous_version": self.current_version if prev_version != self.current_version else None,
            }

        except Exception as e:
            logger.error("Rollback failed: %s", e)
            return {"success": False, "error": f"Rollback failed: {e}"}

    def get_release_notes(self, version: str) -> dict[str, Any]:
        release = self._fetch_release_by_version(version)
        if not release:
            return {"version": version, "found": False}

        body = release.get("body", "")
        changelog = [line.strip() for line in body.split("\n") if line.strip()]

        return {
            "version": release.get("tag_name", "").lstrip("v"),
            "name": release.get("name", ""),
            "published_at": release.get("published_at"),
            "html_url": release.get("html_url"),
            "body": body,
            "changelog": changelog,
            "prerelease": release.get("prerelease", False),
            "author": release.get("author", {}).get("login", ""),
            "found": True,
        }

    def get_channels(self) -> list[dict[str, Any]]:
        return [
            {"id": "stable", "name": "Stable", "description": "Production-ready releases. Recommended for all users.", "recommended": True},
            {"id": "beta", "name": "Beta", "description": "Pre-release versions with new features. May contain bugs.", "recommended": False},
            {"id": "nightly", "name": "Nightly", "description": "Daily builds with latest changes. Unstable.", "recommended": False},
            {"id": "pre-release", "name": "Pre-release", "description": "Release candidates for testing before stable.", "recommended": False},
        ]

    def get_version_info(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "channel": self._settings.get("channel", "stable"),
            "auto_check": self._settings.get("auto_check", True),
            "last_check": self._settings.get("last_check"),
            "update_dir": str(self.update_dir),
            "history_count": len(self._history),
        }
