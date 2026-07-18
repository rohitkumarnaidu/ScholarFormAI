# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from sqlalchemy import Column, String, DateTime, ForeignKey, text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    version_number = Column(String, nullable=False) # e.g., "v1", "v2-edited"
    edited_structured_data = Column(JSON, nullable=True) # Snapshot of what was edited
    output_path = Column(String, nullable=True) # Path to the DOCX/PDF generated for this version
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    document = relationship("Document", back_populates="versions", lazy="joined")
