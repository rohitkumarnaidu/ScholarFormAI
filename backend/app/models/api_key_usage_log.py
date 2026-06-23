# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
API Key Usage Log model for tracking per-key request analytics.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class ApiKeyUsageLog(Base):
    __tablename__ = "api_key_usage_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_api_key_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint = Column(String(200), nullable=True)
    model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
