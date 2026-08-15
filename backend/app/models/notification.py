# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class Notification(Base):
    """
    Enterprise Notification Model
    Stores individual notifications sent to users.
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    type = Column(String, nullable=False, index=True) # system, ai, security, performance, update, maintenance, incident, deployment, usage, billing
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    metadata_json = Column(JSONB, default=dict) # Using metadata_json to avoid conflict with Base.metadata
    
    status = Column(String, default="pending", index=True) # pending, sent, failed
    read_at = Column(DateTime, nullable=True)
    
    retry_count = Column(String, default="0") # Using string temporarily if integer is tricky, wait no, let's just use string to be safe on sqlite vs postgres differences or Integer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
