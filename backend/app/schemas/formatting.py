from typing import Any

from pydantic import BaseModel, Field


class FormattingOptions(BaseModel):
    output_format: str = Field(default="docx", pattern="^(docx|pdf)$")
    page_size: str = Field(default="A4", pattern="^(A4|Letter|Legal)$")
    font_family: str | None = None
    font_size: float | None = None
    line_spacing: float | None = None
    margins: dict[str, float] | None = None
    include_toc: bool = False
    include_page_numbers: bool = True
    include_running_header: bool = True
    first_line_indent: float | None = None
    paragraph_spacing: float | None = None


class HeadingStyleDef(BaseModel):
    level: int
    font_family: str | None = None
    font_size: int = 14
    bold: bool = True
    italic: bool = False
    alignment: str = "left"
    space_before: int = 12
    space_after: int = 6


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
    heading_styles: dict[int, dict[str, Any]] = {}
    page_numbers: bool = True
    running_header: bool = True
    title_page: bool = True
    abstract_required: bool = True
    keywords_required: bool = True
    reference_format: str = "hanging"
    first_line_indent: float = 0.5
    paragraph_spacing: float = 0.0
    is_builtin: bool = True


class StyleInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    citation_format: str
    fields: dict[str, Any] = {}
    is_builtin: bool = True
