# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UpdateApplication(Base):
    __tablename__ = "update_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    public_key = Column(String, nullable=True)  # Public key for signature verification
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    channels = relationship("UpdateChannel", back_populates="application", cascade="all, delete-orphan")
    releases = relationship("UpdateRelease", back_populates="application", cascade="all, delete-orphan")


class UpdateChannel(Base):
    __tablename__ = "update_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("update_applications.id"), nullable=False)
    name = Column(String, nullable=False)  # Stable, Beta, Nightly, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    application = relationship("UpdateApplication", back_populates="channels")
    releases = relationship("UpdateRelease", back_populates="channel")


class UpdateRelease(Base):
    __tablename__ = "update_releases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("update_applications.id"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("update_channels.id"), nullable=False)
    version = Column(String, nullable=False, index=True)  # SemVer
    release_notes = Column(String, nullable=True)
    is_mandatory = Column(Boolean, default=False)
    is_security_update = Column(Boolean, default=False)
    github_release_id = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), server_default=text("now()"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    application = relationship("UpdateApplication", back_populates="releases")
    channel = relationship("UpdateChannel", back_populates="releases")
    artifacts = relationship("UpdateArtifact", back_populates="release", cascade="all, delete-orphan")


class UpdateArtifact(Base):
    __tablename__ = "update_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    release_id = Column(UUID(as_uuid=True), ForeignKey("update_releases.id"), nullable=False)
    os = Column(String, nullable=False)  # windows, linux, macos
    arch = Column(String, nullable=False)  # x64, arm64, etc.
    download_url = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256_checksum = Column(String, nullable=False)
    digital_signature = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    release = relationship("UpdateRelease", back_populates="artifacts")


class UpdateTelemetry(Base):
    __tablename__ = "update_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    client_id = Column(String, nullable=False, index=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("update_applications.id"), nullable=False)
    from_version = Column(String, nullable=True)
    to_version = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, failed, rollback
    error_message = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=text("now()"))
