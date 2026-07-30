# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pydantic v2 Schemas for Enterprise Update Management System.
All request/response schemas follow Pydantic v2 conventions and support standard api_envelope serialization.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class UpdateCheckRequest(BaseModel):
    """Payload for update check request."""
    model_config = ConfigDict(extra="ignore")

    channel: Optional[str] = Field(default="stable", description="Release channel to check (stable, beta, nightly, pre-release)")
    mode: Optional[str] = Field(default="manual", description="Check trigger mode (auto, manual, scheduled, startup)")
    current_version: Optional[str] = Field(default=None, description="Optional current version override")


class UpdateInfoSchema(BaseModel):
    """Schema representing candidate release details."""
    model_config = ConfigDict(extra="ignore")

    version: str = Field(..., description="Release version tag")
    channel: str = Field(default="stable", description="Release channel")
    published_at: Optional[str] = Field(default=None, description="ISO timestamp of release publication")
    release_notes_url: Optional[str] = Field(default=None, description="URL to release notes")
    download_url: Optional[str] = Field(default=None, description="Direct download URL for release asset")
    checksum: Optional[str] = Field(default=None, description="Expected SHA-256 digest")
    checksum_type: str = Field(default="sha256", description="Algorithm used for digest calculation")
    signature_url: Optional[str] = Field(default=None, description="URL to asset digital signature")
    signature_ed25519: Optional[str] = Field(default=None, description="Ed25519 digital signature string")
    size: int = Field(default=0, description="Release asset size in bytes")
    is_mandatory: bool = Field(default=False, description="Flag indicating if update is mandatory")
    is_security: bool = Field(default=False, description="Flag indicating if update contains security patches")
    changelog: Optional[List[str]] = Field(default=None, description="List of changelog bullet points")
    prerelease: bool = Field(default=False, description="Flag indicating if release is a pre-release")
    draft: bool = Field(default=False, description="Flag indicating if release is a draft")


class UpdateCheckResponse(BaseModel):
    """Schema for update check response."""
    model_config = ConfigDict(extra="ignore")

    current_version: str = Field(..., description="Current running application version")
    status: str = Field(..., description="Update status (up-to-date, update-available, error)")
    latest_version: Optional[str] = Field(default=None, description="Latest detected candidate version")
    update: Optional[UpdateInfoSchema] = Field(default=None, description="Update payload if available")
    check_mode: str = Field(default="manual", description="Trigger mode of the check")
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO timestamp of update check")
    error: Optional[str] = Field(default=None, description="Error message if check failed")


class UpdateDownloadRequest(BaseModel):
    """Payload for requesting an update download."""
    model_config = ConfigDict(extra="ignore")

    version: Optional[str] = Field(default=None, description="Target version to download (defaults to pending update)")
    channel: Optional[str] = Field(default=None, description="Optional channel filter")


class UpdateDownloadResponse(BaseModel):
    """Schema for update download response."""
    model_config = ConfigDict(extra="ignore")

    success: bool = Field(..., description="Download success indicator")
    version: Optional[str] = Field(default=None, description="Downloaded version tag")
    path: Optional[str] = Field(default=None, description="Local filesystem path to downloaded artifact")
    size: int = Field(default=0, description="Downloaded asset size in bytes")
    checksum_valid: bool = Field(default=True, description="SHA-256 digest validation status")
    error: Optional[str] = Field(default=None, description="Error description if download failed")


class UpdateInstallRequest(BaseModel):
    """Payload for update installation request."""
    model_config = ConfigDict(extra="ignore")

    version: Optional[str] = Field(default=None, description="Target version to install")
    source_path: Optional[str] = Field(default=None, description="Optional custom source file path for offline installs")
    restart_after: bool = Field(default=True, description="Whether to restart application after installation")


class UpdateOfflineInstallRequest(BaseModel):
    """Payload for offline archive update installation request."""
    model_config = ConfigDict(extra="ignore")

    archive_path: str = Field(..., description="Local filesystem path to offline update archive (.zip or .tar.gz)")
    signature: Optional[str] = Field(default=None, description="Optional digital signature")
    public_key: Optional[str] = Field(default=None, description="Optional public key for verification")


class UpdateInstallResponse(BaseModel):
    """Schema for update installation response."""
    model_config = ConfigDict(extra="ignore")

    success: bool = Field(..., description="Installation success indicator")
    version: Optional[str] = Field(default=None, description="Installed version tag")
    previous_version: Optional[str] = Field(default=None, description="Previous application version tag")
    backup_path: Optional[str] = Field(default=None, description="Backup location of previous installation")
    error: Optional[str] = Field(default=None, description="Error description if installation failed")


class UpdateRollbackRequest(BaseModel):
    """Payload for update rollback request."""
    model_config = ConfigDict(extra="ignore")

    target_version: Optional[str] = Field(default=None, description="Target version to roll back to")
    reason: Optional[str] = Field(default=None, description="Reason for initiating rollback")


class UpdateRollbackResponse(BaseModel):
    """Schema for update rollback response."""
    model_config = ConfigDict(extra="ignore")

    success: bool = Field(..., description="Rollback success indicator")
    version: Optional[str] = Field(default=None, description="Rolled back active version")
    previous_version: Optional[str] = Field(default=None, description="Version prior to rollback")
    error: Optional[str] = Field(default=None, description="Error description if rollback failed")


class UpdateVerifyRequest(BaseModel):
    """Payload for asset integrity and signature verification request."""
    model_config = ConfigDict(extra="ignore")

    file_path: Optional[str] = Field(default=None, description="Local path to file to verify")
    expected_checksum: Optional[str] = Field(default=None, description="Expected SHA-256 checksum string")
    checksum_algo: str = Field(default="sha256", description="Digest algorithm (sha256)")
    signature: Optional[str] = Field(default=None, description="Base64 or hex encoded digital signature")
    public_key: Optional[str] = Field(default=None, description="PEM, hex, or base64 encoded public key")


class UpdateVerifyResponse(BaseModel):
    """Schema for asset integrity and signature verification response."""
    model_config = ConfigDict(extra="ignore")

    valid: bool = Field(..., description="Overall integrity verification result")
    exists: bool = Field(default=True, description="Whether the file exists on filesystem")
    file_name: Optional[str] = Field(default=None, description="Filename of verified asset")
    path: Optional[str] = Field(default=None, description="Absolute file path")
    size_bytes: int = Field(default=0, description="File size in bytes")
    checksum_algo: str = Field(default="sha256", description="Algorithm used for hash calculation")
    expected_checksum: Optional[str] = Field(default=None, description="Expected checksum provided")
    calculated_sha256: Optional[str] = Field(default=None, description="Calculated SHA-256 digest")
    checksum_valid: bool = Field(default=True, description="Whether calculated hash matches expected hash")
    signature_provided: bool = Field(default=False, description="Whether digital signature was supplied")
    signature_valid: bool = Field(default=True, description="Whether digital signature verification succeeded")
    error: Optional[str] = Field(default=None, description="Error details if verification failed")


class UpdateSettingsSchema(BaseModel):
    """Schema for update management configuration settings."""
    model_config = ConfigDict(extra="ignore")

    channel: str = Field(default="stable", description="Selected release channel (stable, beta, nightly, pre-release)")
    auto_check: bool = Field(default=True, description="Enable automatic periodic update checks")
    auto_download: bool = Field(default=False, description="Enable automatic background download of updates")
    auto_install: bool = Field(default=False, description="Enable automatic installation of downloaded updates")
    auto_restart: bool = Field(default=True, description="Automatically restart after update installation")
    check_frequency_hours: int = Field(default=24, description="Check frequency interval in hours")
    notify_on_optional: bool = Field(default=True, description="Notify user on optional updates")
    notify_on_security: bool = Field(default=True, description="Notify user on security updates")
    check_at_startup: bool = Field(default=True, description="Perform update check on application startup")
    background_download: bool = Field(default=False, description="Use background download worker")
    proxy_url: Optional[str] = Field(default=None, description="HTTP/HTTPS proxy server URL")
    github_token: Optional[str] = Field(default=None, description="GitHub API access token for higher rate limits")
    verify_signature: bool = Field(default=True, description="Enforce digital signature verification")
    verify_checksum: bool = Field(default=True, description="Enforce SHA-256 digest verification")
    last_check: Optional[str] = Field(default=None, description="ISO timestamp of last update check")
    public_key: Optional[str] = Field(default=None, description="Configured public key for signature verification")


class UpdateSettingsUpdateSchema(BaseModel):
    """Payload for updating update settings."""
    model_config = ConfigDict(extra="ignore")

    settings: Dict[str, Any] = Field(..., description="Dictionary of settings key-value pairs to update")


class ReleaseNotesSchema(BaseModel):
    """Schema for release notes details."""
    model_config = ConfigDict(extra="ignore")

    version: str = Field(..., description="Target version for release notes")
    name: Optional[str] = Field(default=None, description="Release title or headline")
    published_at: Optional[str] = Field(default=None, description="ISO timestamp when release was published")
    html_url: Optional[str] = Field(default=None, description="Web URL to GitHub release page")
    body: Optional[str] = Field(default=None, description="Full release notes markdown text")
    changelog: Optional[List[str]] = Field(default=None, description="Parsed changelog bullet points")
    prerelease: bool = Field(default=False, description="Whether release is marked pre-release")
    author: Optional[str] = Field(default=None, description="Release author username")
    found: bool = Field(default=True, description="Whether release notes were found")


class ChannelSchema(BaseModel):
    """Schema representing an available release channel."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Channel identifier (stable, beta, nightly, pre-release)")
    name: str = Field(..., description="Display name of channel")
    description: str = Field(..., description="Channel description")
    recommended: bool = Field(default=False, description="Whether channel is recommended for default use")


class VersionInfoSchema(BaseModel):
    """Schema representing application version metadata."""
    model_config = ConfigDict(extra="ignore")

    current_version: str = Field(..., description="Current application version")
    channel: str = Field(default="stable", description="Active release channel")
    auto_check: bool = Field(default=True, description="Auto-check status")
    last_check: Optional[str] = Field(default=None, description="Timestamp of last update check")
    update_dir: str = Field(..., description="Local directory path for updates")
    history_count: int = Field(default=0, description="Total recorded history entries")


class UpdateHistoryItemSchema(BaseModel):
    """Schema representing a single update audit log entry."""
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(default=None, description="Unique audit record ID")
    version: str = Field(..., description="Target version of update attempt")
    channel: str = Field(default="stable", description="Release channel used")
    installed_at: str = Field(..., description="ISO timestamp of installation attempt")
    checksum: Optional[str] = Field(default=None, description="Calculated checksum of asset")
    checksum_type: str = Field(default="sha256", description="Digest algorithm used")
    success: bool = Field(default=True, description="Whether update succeeded")
    error_message: Optional[str] = Field(default=None, description="Error message if update failed")
    rolled_back: bool = Field(default=False, description="Whether update was subsequently rolled back")
    rollback_version: Optional[str] = Field(default=None, description="Version rolled back to")


class UpdateHistoryResponse(BaseModel):
    """Schema for update history response payload."""
    model_config = ConfigDict(extra="ignore")

    history: List[UpdateHistoryItemSchema] = Field(default_factory=list, description="List of update history records")
