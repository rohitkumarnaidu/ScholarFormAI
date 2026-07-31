# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ProcessingStatus(Base):
    __tablename__ = "processing_status"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    phase = Column(String, nullable=False)  # UPLOAD, EXTRACTION, NLP_ANALYSIS, VALIDATION, PERSISTENCE
    status = Column(
        String, nullable=False
    )  # PENDING, PROCESSING, COMPLETED, COMPLETED_WITH_WARNINGS, FAILED, CANCELLED
    progress_percentage = Column(Integer, nullable=True)  # 0-100
    message = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()"))

    document = relationship("Document", back_populates="processing_statuses", lazy="joined")
