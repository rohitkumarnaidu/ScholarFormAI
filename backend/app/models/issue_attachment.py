# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from sqlalchemy import Column, DateTime, String, text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class IssueAttachment(Base):
    __tablename__ = "issue_attachments"
    __table_args__ = {"schema": "issues"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.issues.id", ondelete="CASCADE"), nullable=False)

    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'screenshot', 'recording', 'log', 'other'
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Relationships
    issue = relationship("Issue", back_populates="attachments", lazy="selectin")
