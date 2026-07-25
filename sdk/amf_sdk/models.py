from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Author(BaseModel):
    first_name: str
    last_name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None


class Paragraph(BaseModel):
    text: str
    style: Optional[str] = None
    alignment: Optional[str] = None


class Section(BaseModel):
    heading: str
    level: int = 1
    content: List[Paragraph] = []
    subsections: List["Section"] = []


class Reference(BaseModel):
    authors: List[Author] = []
    year: Optional[str] = None
    title: str
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None


class Manuscript(BaseModel):
    title: str
    authors: List[Author] = []
    abstract: Optional[str] = None
    keywords: List[str] = []
    sections: List[Section] = []
    references: List[Reference] = []
    acknowledgments: Optional[str] = None


class FormattingOptions(BaseModel):
    output_format: str = "docx"
    page_size: str = "A4"
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    line_spacing: Optional[float] = None
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
    preview_url: Optional[str] = None
    pages: int = 0
    metadata: Dict[str, Any] = {}
    style_applied: str
    formatted_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationIssue(BaseModel):
    code: str
    message: str
    location: Optional[str] = None
    severity: str = "warning"


class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []
    suggestions: List[str] = []
