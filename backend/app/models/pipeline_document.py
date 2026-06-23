# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from app.models.block import Block
from app.models.figure import Figure
from app.models.table import Table
from app.models.reference import Reference
from app.models.equation import Equation
from app.models.review import ReviewStatus, ReviewMetadata

logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    """Metadata extracted from the document or provided by the user."""
    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    affiliations: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    publication_date: Optional[datetime] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    corresponding_author: Optional[str] = None
    email: Optional[str] = None
    ai_hints: Dict[str, Any] = Field(default_factory=dict)


class TemplateInfo(BaseModel):
    """Information about the scientific template used for formatting."""
    template_name: str
    template_version: Optional[str] = "1.0"


class ProcessingStage(BaseModel):
    """Record of a single processing stage in the pipeline."""
    stage_name: str
    status: str
    message: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PipelineDocument(BaseModel):
    """
    Internal document model used throughout the pipeline.
    This is NOT the database model. It holds the full structured content.
    """
    document_id: str
    original_filename: Optional[str] = None
    source_path: Optional[str] = None

    # Content components
    blocks: List[Block] = Field(default_factory=list)
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    equations: List[Equation] = Field(default_factory=list)

    # Metadata
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    template: Optional[TemplateInfo] = None

    # Formatting Options
    formatting_options: Dict[str, Any] = Field(default_factory=dict)

    # Validation results
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)

    # HITL Signals
    review: Optional[ReviewMetadata] = Field(default=None)

    # Runtime/Persistence fields
    output_path: Optional[str] = None
    generated_doc: Optional[Any] = Field(None, exclude=True)  # Transient field for Word object

    # Execution history
    processing_history: List[ProcessingStage] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Ensure document_id is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("document_id must be a non-empty string")
        return v.strip()

    def add_processing_stage(
        self,
        stage_name: str,
        status: str,
        message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Helper to add a stage to history. Never raises."""
        try:
            stage = ProcessingStage(
                stage_name=stage_name,
                status=status,
                message=message,
                duration_ms=duration_ms,
            )
            self.processing_history.append(stage)
            self.updated_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.error("Failed to add processing stage '%s': %s", stage_name, exc)

    def get_block_by_id(self, block_id: str) -> Optional[Block]:
        """Find a block by its ID. Returns None if not found or on error."""
        if not block_id:
            return None
        try:
            for block in self.blocks:
                if block.block_id == block_id:
                    return block
        except Exception as exc:
            logger.error("Error in get_block_by_id('%s'): %s", block_id, exc)
        return None

    def get_figure_by_id(self, figure_id: str) -> Optional[Figure]:
        """Find a figure by its ID. Returns None if not found or on error."""
        if not figure_id:
            return None
        try:
            for figure in self.figures:
                if figure.figure_id == figure_id:
                    return figure
        except Exception as exc:
            logger.error("Error in get_figure_by_id('%s'): %s", figure_id, exc)
        return None

    def get_equation_by_id(self, equation_id: str) -> Optional[Equation]:
        """Find an equation by its ID. Returns None if not found or on error."""
        if not equation_id:
            return None
        try:
            for eqn in self.equations:
                if eqn.equation_id == equation_id:
                    return eqn
        except Exception as exc:
            logger.error("Error in get_equation_by_id('%s'): %s", equation_id, exc)
        return None

    def get_blocks_by_type(self, block_type: str) -> List[Block]:
        """Find blocks by their semantic type. Returns empty list on error."""
        if not block_type:
            return []
        try:
            return [b for b in self.blocks if b.block_type == block_type]
        except Exception as exc:
            logger.error("Error in get_blocks_by_type('%s'): %s", block_type, exc)
            return []

    def get_blocks_in_section(self, section_name: str) -> List[Block]:
        """Find blocks belonging to a specific section. Returns empty list on error."""
        if not section_name:
            return []
        try:
            return [
                b for b in self.blocks
                if b.section_name and section_name.lower() in b.section_name.lower()
            ]
        except Exception as exc:
            logger.error("Error in get_blocks_in_section('%s'): %s", section_name, exc)
            return []

    def get_section_names(self) -> List[str]:
        """Get unique section names present in the document. Returns empty list on error."""
        try:
            return list(set(b.section_name for b in self.blocks if b.section_name))
        except Exception as exc:
            logger.error("Error in get_section_names: %s", exc)
            return []

    def get_stats(self) -> Dict[str, int]:
        """Get counts of components. Always returns a valid dict."""
        try:
            return {
                "blocks": len(self.blocks),
                "figures": len(self.figures),
                "tables": len(self.tables),
                "references": len(self.references),
                "equations": len(self.equations),
                "stages": len(self.processing_history),
            }
        except Exception as exc:
            logger.error("Error in get_stats: %s", exc)
            return {
                "blocks": 0,
                "figures": 0,
                "tables": 0,
                "references": 0,
                "equations": 0,
                "stages": 0,
            }
