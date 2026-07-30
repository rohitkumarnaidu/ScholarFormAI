# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
SQLAlchemy Models for Enterprise Update Management System.
Includes models for UpdateChannel, UpdateRelease, UpdateHistory, UpdateRollback.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text, JSON, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class UpdateChannel(Base):
    """
    SQLAlchemy model representing a release distribution channel.
    (e.g., stable, beta, nightly, pre-release).
    """

    __tablename__ = "update_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_recommended = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_recommended": self.is_recommended,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UpdateRelease(Base):
    """
    SQLAlchemy model representing an enterprise software release metadata entry.
    """

    __tablename__ = "update_releases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=False, index=True, unique=True)
    channel = Column(String(50), nullable=False, default="stable", index=True)
    release_name = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    download_url = Column(Text, nullable=True)
    signature_url = Column(Text, nullable=True)
    checksum_sha256 = Column(String(128), nullable=True)
    signature_ed25519 = Column(Text, nullable=True)
    signature_rsa = Column(Text, nullable=True)
    size_bytes = Column(BigInteger, default=0, nullable=False)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    is_security = Column(Boolean, default=False, nullable=False)
    min_supported_version = Column(String(50), nullable=True)
    changelog_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "version": self.version,
            "channel": self.channel,
            "release_name": self.release_name,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "download_url": self.download_url,
            "signature_url": self.signature_url,
            "checksum_sha256": self.checksum_sha256,
            "signature_ed25519": self.signature_ed25519,
            "signature_rsa": self.signature_rsa,
            "size_bytes": self.size_bytes,
            "is_mandatory": self.is_mandatory,
            "is_security": self.is_security,
            "min_supported_version": self.min_supported_version,
            "changelog": self.changelog_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UpdateHistory(Base):
    """
    SQLAlchemy model representing an audit log entry for software update attempts.
    """

    __tablename__ = "update_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    device_id = Column(String(255), nullable=True)
    from_version = Column(String(50), nullable=True)
    to_version = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False, default="stable")
    status = Column(String(50), nullable=False, default="installed")
    checksum = Column(String(128), nullable=True)
    checksum_type = Column(String(20), default="sha256")
    error_message = Column(Text, nullable=True)
    rolled_back = Column(Boolean, default=False, nullable=False)
    rollback_version = Column(String(50), nullable=True)
    installed_at = Column(DateTime(timezone=True), server_default=text("now()"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "device_id": self.device_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "version": self.to_version,
            "channel": self.channel,
            "status": self.status,
            "checksum": self.checksum,
            "checksum_type": self.checksum_type,
            "error_message": self.error_message,
            "rolled_back": self.rolled_back,
            "rollback_version": self.rollback_version,
            "installed_at": self.installed_at.isoformat() if self.installed_at else None,
            "success": self.status == "installed" and not self.error_message,
        }


class UpdateRollback(Base):
    """
    SQLAlchemy model representing an audit log entry for version rollback operations.
    """

    __tablename__ = "update_rollback_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    history_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    from_version = Column(String(50), nullable=False)
    target_version = Column(String(50), nullable=False)
    backup_path = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=text("now()"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "history_id": str(self.history_id) if self.history_id else None,
            "from_version": self.from_version,
            "target_version": self.target_version,
            "backup_path": self.backup_path,
            "reason": self.reason,
            "status": self.status,
            "error_message": self.error_message,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "success": self.status == "success",
        }
