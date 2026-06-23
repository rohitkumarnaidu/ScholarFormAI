# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document Schemas — Request & Response models for the document pipeline API.

Covers upload, status polling, preview, comparison, and download endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Type aliases ──────────────────────────────────────────────────────────────

ExportFormat = Literal["docx", "pdf"]
DocumentStatus = Literal["PENDING", "PROCESSING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED", "CANCELLED"]
PageSize = Literal["Letter", "A4", "Legal"]
TemplateChoice = Literal[
    "IEEE",
    "ACM",
    "APA",
    "MLA",
    "Chicago",
    "Harvard",
    "Vancouver",
    "Springer",
    "Nature",
    "Elsevier",
    "Numeric",
    "Modern Blue",
    "Modern Gold",
    "Modern Red",
    "None",
    "Resume",
    "Portfolio",
]


# ── Upload / Request Schemas ──────────────────────────────────────────────────

class FormattingOptions(BaseModel):
    """Formatting preferences sent with the upload request."""

    page_numbers: bool = Field(True, description="Add page numbers to the footer.")
    borders: bool = Field(False, description="Add decorative page borders.")
    cover_page: bool = Field(False, description="Prepend a cover page.")
    toc: bool = Field(False, description="Insert a Table of Contents.")
    page_size: PageSize = Field("Letter", description="Output page size.")
    fast_mode: bool = Field(
        False,
        description="Enable performance-first pipeline (disables selected slow AI checks).",
    )


class DocumentUploadResponse(BaseModel):
    """Returned immediately after a successful file upload."""

    message: str = Field(..., description="Human-readable confirmation.")
    job_id: str = Field(..., description="UUID of the processing job.")
    status: DocumentStatus = Field("PROCESSING", description="Initial job status.")


# ── Status Schemas ────────────────────────────────────────────────────────────

class PhaseStatus(BaseModel):
    """Status of a single pipeline phase."""

    phase: str = Field(..., description="Pipeline stage name (e.g. 'parsing').")
    status: str = Field(..., description="Phase status: 'success', 'warning', 'failed'.")
    message: Optional[str] = Field(None, description="Human-readable phase message.")
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Phase progress percentage."
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp.")


class DocumentStatusResponse(BaseModel):
    """Returned by GET /api/v1/documents/{job_id}/status."""

    job_id: str
    status: str = Field(..., description="Overall job status.")
    current_phase: Optional[str] = Field(None, description="Currently active stage.")
    phase: Optional[str] = Field(None, description="Alias for current_phase (frontend compat).")
    progress_percentage: float = Field(0, ge=0, le=100)
    message: Optional[str] = Field(None, description="Status message or error detail.")
    updated_at: Optional[datetime] = None
    phases: List[PhaseStatus] = Field(
        default_factory=list, description="Detailed per-stage breakdown."
    )


# ── ORM / DB Schemas ─────────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    """Shared fields for all document representations."""

    filename: str = Field(..., description="Original uploaded filename.")
    template: str = Field(..., description="Journal template applied (e.g. 'IEEE').")
    status: str = Field(..., description="Processing status.")
    export_formats: List[ExportFormat] = Field(
        default_factory=lambda: ["docx", "pdf"],
        description="Requested output formats for the document pipeline.",
    )

    @field_validator("template")
    @classmethod
    def normalise_template(cls, v: str) -> str:
        return v.strip().upper() if v.strip().upper() != "NONE" else "none"


class Document(DocumentBase):
    """Full document record returned from the database."""

    id: str = Field(..., description="UUID of the document job.")
    user_id: Optional[str] = Field(None, description="Owner user UUID (None for anonymous).")
    output_path: Optional[str] = Field(None, description="Server path to the formatted output file.")
    original_file_path: Optional[str] = Field(None, description="Server path to the original upload.")
    progress: Optional[float] = Field(None, ge=0, le=100, description="Overall progress percentage.")
    current_stage: Optional[str] = Field(None, description="Name of the currently active pipeline stage.")
    error_message: Optional[str] = Field(None, description="Error detail if status is FAILED.")
    formatting_options: Optional[Dict[str, Any]] = Field(
        None, description="Formatting options used for this job."
    )
    created_at: datetime = Field(..., description="Job creation timestamp (UTC).")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp (UTC).")

    model_config = ConfigDict(from_attributes=True)


class DocumentListItem(BaseModel):
    """Lightweight document summary for list endpoints."""

    id: str
    filename: str
    template: str
    status: str
    progress: Optional[float] = None
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Returned by GET /api/v1/documents."""

    documents: List[DocumentListItem] = Field(default_factory=list)
    total: int = Field(0, description="Total matching documents (before pagination).")
    limit: int = Field(50, description="Page size used.")
    offset: int = Field(0, description="Page offset used.")


# ── Preview / Compare Schemas ─────────────────────────────────────────────────

class DocumentMetaSummary(BaseModel):
    """Minimal metadata included in preview and compare responses."""

    filename: str
    template: str
    status: str
    created_at: Optional[datetime] = None


class DocumentPreviewResponse(BaseModel):
    """Returned by GET /api/v1/documents/{job_id}/preview."""

    structured_data: Optional[Dict[str, Any]] = Field(
        None, description="Parsed and structured document content."
    )
    validation_results: Optional[Dict[str, Any]] = Field(
        None, description="Validation errors and warnings."
    )
    metadata: Optional[DocumentMetaSummary] = None


class CompareOriginal(BaseModel):
    raw_text: Optional[str] = None
    structured_data: None = None


class CompareFormatted(BaseModel):
    structured_data: Optional[Dict[str, Any]] = None


class DocumentCompareResponse(BaseModel):
    """Returned by GET /api/v1/documents/{job_id}/compare."""

    html_diff: str = Field(..., description="HTML diff of original vs formatted text.")
    original: CompareOriginal
    formatted: CompareFormatted


# Generation Schemas

class SectionSpec(BaseModel):
    name: str
    include: bool = True


class AcademicPaperMetadata(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    affiliation: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    sections: List[SectionSpec] = Field(default_factory=list)
    language: str = "english"


class ResumeEducationItem(BaseModel):
    institution: str
    degree: str
    year: Optional[str] = None


class ResumeExperienceItem(BaseModel):
    company: str
    role: str
    duration: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)


class ResumeMetadata(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    summary: Optional[str] = None
    education: List[ResumeEducationItem] = Field(default_factory=list)
    experience: List[ResumeExperienceItem] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class GenerationOptions(BaseModel):
    include_placeholder_content: bool = True
    word_count_target: int = 3000


class GenerateRequest(BaseModel):
    doc_type: str
    template: str
    metadata: Dict[str, Any]
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class GenerateResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None


class GenerateStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: int
    message: str
    error: Optional[str] = None
    output_path: Optional[str] = None
    outline: List[str] = Field(default_factory=list)
