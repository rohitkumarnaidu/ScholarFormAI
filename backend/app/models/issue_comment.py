# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, DateTime, String, text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

class IssueComment(Base):
    __tablename__ = "issue_comments"
    __table_args__ = {"schema": "issues"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.issues.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    body = Column(String, nullable=False)
    is_internal = Column(Boolean, default=False) # For admin-only notes
    is_ai_generated = Column(Boolean, default=False) # For AI suggested fixes/responses
    
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    # Relationships
    issue = relationship("Issue", back_populates="comments", lazy="selectin")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin", primaryjoin="IssueComment.user_id == foreign(User.id)")
