# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, DateTime, String, text, Enum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = {"schema": "issues"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tracking_number = Column(String, unique=True, index=True, nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)

    type = Column(
        String, nullable=False
    )  # e.g., 'bug', 'feature_request', 'feedback', 'performance', 'security', 'crash'
    priority = Column(String, default="medium")  # low, medium, high, critical
    severity = Column(String, default="minor")  # minor, major, critical, blocker
    status = Column(String, default="open")  # open, in_progress, resolved, closed, duplicate, spam

    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)  # null for anonymous
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)

    # Metadata and environment context
    system_info = Column(JSON, nullable=True)  # OS, browser, device, app version
    ai_category = Column(String, nullable=True)
    ai_summary = Column(String, nullable=True)
    ai_suggested_fix = Column(String, nullable=True)

    github_issue_url = Column(String, nullable=True)
    github_issue_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    # Relationships
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan", lazy="selectin")
    attachments = relationship("IssueAttachment", back_populates="issue", cascade="all, delete-orphan", lazy="selectin")
    user = relationship(
        "User", foreign_keys=[user_id], lazy="selectin", primaryjoin="Issue.user_id == foreign(User.id)"
    )
    assignee = relationship(
        "User", foreign_keys=[assignee_id], lazy="selectin", primaryjoin="Issue.assignee_id == foreign(User.id)"
    )
