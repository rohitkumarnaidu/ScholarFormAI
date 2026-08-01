# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    session_id = Column(String, nullable=True)
    original_text = Column(Text, nullable=False)
    suggested_text = Column(Text, nullable=False)
    suggestion_type = Column(String, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, server_default=text("'pending'"))
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="suggestions", lazy="joined")
    document = relationship("Document", back_populates="suggestions", lazy="joined")
