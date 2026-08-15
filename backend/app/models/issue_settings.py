# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, DateTime, String, text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

class IssueSettings(Base):
    """
    Enterprise settings for Issue Reporting Ecosystem.
    Stores BYOK configurations, capability model routing, and webhook destinations.
    """
    __tablename__ = "issue_settings"
    __table_args__ = {"schema": "issues"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Model routing
    triage_model = Column(String, default="gpt-4o-mini")
    reasoning_model = Column(String, default="claude-3-5-sonnet")
    
    # Integration toggles
    github_sync_enabled = Column(Boolean, default=False)
    github_repo = Column(String, nullable=True)
    
    slack_webhook_url = Column(String, nullable=True)
    discord_webhook_url = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
