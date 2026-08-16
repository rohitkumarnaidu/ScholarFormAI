# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class NotificationPreference(Base):
    """
    Enterprise Notification Preferences Model
    Stores user-specific settings for channels and schedules.
    """

    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # JSON structure storing opt-ins: {"email": {"security": true, "billing": true}, "slack": {...}}
    channel_preferences = Column(JSONB, default=dict)

    # Do Not Disturb
    dnd_enabled = Column(Boolean, default=False)
    dnd_start_time = Column(String, nullable=True)  # HH:MM format
    dnd_end_time = Column(String, nullable=True)  # HH:MM format
    timezone = Column(String, default="UTC")

    # Digest Mode
    digest_mode = Column(String, default="none")  # none, daily, weekly
