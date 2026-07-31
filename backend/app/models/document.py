# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from sqlalchemy import Column, String, DateTime, text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # No FK to auth.users (Supabase managed)
    filename = Column(String, nullable=False)
    template = Column(String, nullable=True)
    status = Column(String, nullable=False)
    original_file_path = Column(String, nullable=True)  # Path to the uploaded file
    raw_text = Column(String, nullable=True)  # Extracted raw text
    output_path = Column(String, nullable=True)
    formatting_options = Column(JSON, nullable=True)  # Stores { "page_size": "A4", "toc": true, ... }

    # Job State Fields
    progress = Column(Integer, default=0)
    current_stage = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    user = relationship("User", lazy="joined", primaryjoin="foreign(Document.user_id) == User.id")
    results = relationship("DocumentResult", back_populates="document", lazy="selectin")
    versions = relationship("DocumentVersion", back_populates="document", lazy="selectin")
    processing_statuses = relationship("ProcessingStatus", back_populates="document", lazy="selectin")
    suggestions = relationship("Suggestion", back_populates="document", lazy="selectin")
