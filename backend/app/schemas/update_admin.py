"""Pydantic models for admin update management."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class UpdateApplicationBase(BaseModel):
    name: str = Field(..., description="Application name")
    description: str | None = Field(default=None, description="Application description")
    public_key: str | None = Field(default=None, description="Public key for signature verification")

class UpdateApplicationCreate(UpdateApplicationBase):
    pass

class UpdateApplicationResponse(UpdateApplicationBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateChannelBase(BaseModel):
    name: str = Field(..., description="Channel name (e.g. stable, beta, nightly)")
    is_active: bool = Field(default=True, description="Is channel active")

class UpdateChannelCreate(UpdateChannelBase):
    app_id: UUID = Field(..., description="Application ID")

class UpdateChannelResponse(UpdateChannelBase):
    id: UUID
    app_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateReleaseBase(BaseModel):
    version: str = Field(..., description="SemVer version")
    release_notes: str | None = Field(default=None, description="Release notes")
    is_mandatory: bool = Field(default=False, description="Is this a mandatory update")
    is_security_update: bool = Field(default=False, description="Is this a security update")
    github_release_id: str | None = Field(default=None, description="Linked GitHub Release ID")

class UpdateReleaseCreate(UpdateReleaseBase):
    app_id: UUID = Field(..., description="Application ID")
    channel_id: UUID = Field(..., description="Channel ID")

class UpdateReleaseResponse(UpdateReleaseBase):
    id: UUID
    app_id: UUID
    channel_id: UUID
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateArtifactBase(BaseModel):
    os: str = Field(..., description="OS (windows, macos, linux)")
    arch: str = Field(..., description="Architecture (x64, arm64)")
    download_url: str = Field(..., description="Download URL")
    size_bytes: int = Field(..., description="Size in bytes")
    sha256_checksum: str = Field(..., description="SHA-256 checksum")
    digital_signature: str | None = Field(default=None, description="Digital signature")

class UpdateArtifactCreate(UpdateArtifactBase):
    release_id: UUID = Field(..., description="Release ID")

class UpdateArtifactResponse(UpdateArtifactBase):
    id: UUID
    release_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
