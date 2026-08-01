# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentResult(Base):
    __tablename__ = "document_results"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    structured_data = Column(JSONB, nullable=True)  # Detected sections, citations, references
    validation_results = Column(JSONB, nullable=True)  # Violations, suggested fixes
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    document = relationship("Document", back_populates="results", lazy="joined")
