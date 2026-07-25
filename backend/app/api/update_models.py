"""Pydantic models for update management API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UpdateSettings(BaseModel):
    channel: str = Field(default="stable", description="Release channel (stable, beta, nightly, pre-release)")
    auto_check: bool = Field(default=True, description="Automatically check for updates")
    auto_download: bool = Field(default=False, description="Automatically download updates")
    auto_install: bool = Field(default=False, description="Automatically install updates")
    auto_restart: bool = Field(default=True, description="Automatically restart after update")
    check_frequency_hours: int = Field(default=24, ge=1, le=720, description="Hours between update checks")
    notify_on_optional: bool = Field(default=True, description="Notify about optional updates")
    notify_on_security: bool = Field(default=True, description="Notify about security updates")
    check_at_startup: bool = Field(default=True, description="Check for updates on startup")
    background_download: bool = Field(default=False, description="Download updates in background")
    proxy_url: str | None = Field(default=None, description="Proxy URL for downloads")
    github_token: str | None = Field(default=None, description="GitHub API token")
    verify_signature: bool = Field(default=True, description="Verify digital signatures")
    verify_checksum: bool = Field(default=True, description="Verify checksums")


class UpdateSettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(description="Settings to update")


class UpdateCheckRequest(BaseModel):
    channel: str | None = Field(default=None, description="Channel to check")
    mode: str = Field(default="manual", description="Check mode (auto, manual, scheduled, startup)")


class UpdateCheckResponse(BaseModel):
    status: str = Field(description="Update status")
    current_version: str = Field(description="Currently installed version")
    latest_version: str | None = Field(default=None, description="Latest available version")
    update: dict | None = Field(default=None, description="Update information")
    check_mode: str = Field(default="manual", description="How the check was triggered")
    checked_at: str = Field(description="ISO datetime of check")
    error: str | None = Field(default=None, description="Error message if check failed")


class UpdateDownloadRequest(BaseModel):
    version: str | None = Field(default=None, description="Version to download")


class UpdateDownloadResponse(BaseModel):
    success: bool = Field(description="Whether download succeeded")
    version: str | None = Field(default=None, description="Downloaded version")
    path: str | None = Field(default=None, description="Download file path")
    size: int = Field(default=0, description="Download size in bytes")
    checksum_valid: bool | None = Field(default=None, description="Whether checksum verification passed")
    error: str | None = Field(default=None, description="Error message")


class UpdateInstallResponse(BaseModel):
    success: bool = Field(description="Whether installation succeeded")
    version: str | None = Field(default=None, description="Installed version")
    previous_version: str | None = Field(default=None, description="Previous version")
    backup_path: str | None = Field(default=None, description="Backup path for rollback")
    error: str | None = Field(default=None, description="Error message")


class UpdateRollbackResponse(BaseModel):
    success: bool = Field(description="Whether rollback succeeded")
    version: str | None = Field(default=None, description="Version rolled back to")
    previous_version: str | None = Field(default=None, description="Previous version before rollback")
    error: str | None = Field(default=None, description="Error message")


class UpdateHistoryResponse(BaseModel):
    history: list[dict] = Field(description="Update history entries")


class ReleaseNotesResponse(BaseModel):
    version: str = Field(description="Version number")
    name: str | None = Field(default=None, description="Release name")
    published_at: str | None = Field(default=None, description="Publication date")
    html_url: str | None = Field(default=None, description="Release URL")
    body: str | None = Field(default=None, description="Full release body")
    changelog: list[str] | None = Field(default=None, description="Parsed changelog entries")
    prerelease: bool = Field(default=False, description="Whether this is a pre-release")
    author: str | None = Field(default=None, description="Release author")
    found: bool = Field(description="Whether the release was found")


class ChannelsResponse(BaseModel):
    channels: list[dict] = Field(description="Available release channels")


class VersionInfoResponse(BaseModel):
    current_version: str = Field(description="Current installed version")
    channel: str = Field(description="Current release channel")
    auto_check: bool = Field(description="Whether auto-check is enabled")
    last_check: str | None = Field(default=None, description="Last check timestamp")
    update_dir: str = Field(description="Update directory")
    history_count: int = Field(default=0, description="Number of history entries")
