# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
User API Key model for managing user-provided LLM provider keys.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from app.db.base import Base


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    api_key_encrypted = Column(Text, nullable=False)
    key_label = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=60, nullable=False)
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)
    daily_quota = Column(Integer, default=10000, nullable=False)
    total_requests = Column(Integer, default=0, nullable=False)
    last_request_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys", lazy="joined", primaryjoin="foreign(UserApiKey.user_id) == User.id")
    usage_logs = relationship("ApiKeyUsageLog", back_populates="api_key", lazy="selectin", primaryjoin="UserApiKey.id == foreign(ApiKeyUsageLog.user_api_key_id)")

    def to_dict(self, mask_key: bool = True) -> dict:
        key_value = self.api_key_encrypted
        if mask_key and key_value:
            key_value = f"{key_value[:4]}...{key_value[-4:]}" if len(key_value) > 8 else "****"
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "provider": self.provider,
            "key_label": self.key_label,
            "is_active": self.is_active,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "daily_quota": self.daily_quota,
            "total_requests": self.total_requests,
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "key_preview": key_value,
        }
