from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Author(BaseModel):
    first_name: str
    last_name: str
    affiliation: str | None = None
    email: str | None = None
    orcid: str | None = None


class Paragraph(BaseModel):
    text: str
    style: str | None = None
    alignment: str | None = None


class Section(BaseModel):
    heading: str
    level: int = 1
    content: list[Paragraph] = []
    subsections: list["Section"] = []


class Reference(BaseModel):
    authors: list[Author] = []
    year: str | None = None
    title: str
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None


class Manuscript(BaseModel):
    title: str
    authors: list[Author] = []
    abstract: str | None = None
    keywords: list[str] = []
    sections: list[Section] = []
    references: list[Reference] = []
    acknowledgments: str | None = None


class FormattingOptions(BaseModel):
    output_format: str = "docx"
    page_size: str = "A4"
    font_family: str | None = None
    font_size: float | None = None
    line_spacing: float | None = None
    include_toc: bool = False
    include_page_numbers: bool = True
    include_running_header: bool = True


class FormattingStyle(BaseModel):
    id: str
    name: str
    version: str
    description: str
    citation_format: str
    font_family: str = "Times New Roman"
    font_size: int = 12
    line_spacing: float = 2.0
    margin_inches: float = 1.0
    is_builtin: bool = True


class ManuscriptResult(BaseModel):
    download_url: str
    preview_url: str | None = None
    pages: int = 0
    metadata: dict[str, Any] = {}
    style_applied: str
    formatted_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationIssue(BaseModel):
    code: str
    message: str
    location: str | None = None
    severity: str = "warning"


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    suggestions: list[str] = []
