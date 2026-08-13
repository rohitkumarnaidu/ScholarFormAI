from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CitationFormat(StrEnum):
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    HARVARD = "harvard"
    VANCOUVER = "vancouver"
    TURABIAN = "turabian"
    ACS = "acs"
    AMA = "ama"


class Author(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    first_name: str
    last_name: str
    affiliation: str | None = None
    email: str | None = None
    orcid: str | None = None


class Paragraph(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    text: str
    style: str | None = None
    alignment: str | None = None
    indent: float | None = None
    bullet: bool | None = False


class Section(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    heading: str
    level: int = 1
    content: list[Paragraph] = []
    subsections: list["Section"] = []


class Reference(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    authors: list[Author] = []
    year: str | None = None
    title: str
    journal: str | None = None
    book_title: str | None = None
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    url: str | None = None
    isbn: str | None = None


class Manuscript(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    title: str
    authors: list[Author] = []
    abstract: str | None = None
    keywords: list[str] = []
    sections: list[Section] = []
    references: list[Reference] = []
    acknowledgments: str | None = None
    funding_statement: str | None = None
    conflict_of_interest: str | None = None
    corresponding_author: Author | None = None


class FormattingOptions(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    output_format: str = Field(default="docx", pattern="^(docx|pdf)$")
    page_size: str = Field(default="A4", pattern="^(A4|Letter|Legal)$")
    font_family: str | None = None
    font_size: float | None = None
    line_spacing: float | None = None
    margins: dict[str, float] | None = None
    include_toc: bool = False
    include_page_numbers: bool = True
    include_running_header: bool = True


class FormatRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    manuscript: Manuscript
    style_id: str = Field(default="apa", min_length=2, max_length=50)
    options: FormattingOptions | None = None


class FormatResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    download_url: str
    preview_url: str | None = None
    pages: int = 0
    metadata: dict[str, Any] = {}
    style_applied: str
    formatted_at: datetime = Field(default_factory=datetime.utcnow)


class ValidateRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    manuscript: Manuscript
    style_id: str = Field(default="apa", min_length=2, max_length=50)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    code: str
    message: str
    location: str | None = None
    severity: str = "warning"


class ValidateResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    suggestions: list[str] = []


class StyleInfo(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: str
    name: str
    version: str
    description: str
    citation_format: CitationFormat
    fields: dict[str, Any] = {}
    is_builtin: bool = True


class PreviewRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    manuscript: Manuscript
    style_id: str = "apa"
    options: FormattingOptions | None = None


class PreviewResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    html: str
    style_applied: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    status: str
    version: str
    service: str
    uptime: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
