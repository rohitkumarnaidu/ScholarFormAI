# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Document edit schemas — typed request models for document modification.

Prevents mass assignment by explicitly listing editable fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DocumentEditRequest(BaseModel):
    """Request body for POST /api/v1/documents/{jobId}/edit."""

    model_config = {"extra": "forbid"}

    template: str | None = Field(None, max_length=50, description="Target formatting template.")
    add_page_numbers: bool | None = Field(None, description="Whether to add page numbers.")
    add_borders: bool | None = Field(None, description="Whether to add borders.")
    add_cover_page: bool | None = Field(None, description="Whether to add a cover page.")
    generate_toc: bool | None = Field(None, description="Whether to generate table of contents.")
    add_line_numbers: bool | None = Field(None, description="Whether to add line numbers.")
    line_spacing: float | None = Field(None, ge=0.5, le=3.0, description="Line spacing value.")
    page_size: str | None = Field(None, max_length=20, description="Page size (Letter, A4, etc.).")
    title: str | None = Field(None, max_length=500, description="Document title.")
    content: str | None = Field(None, description="Updated document content.")
    sections: list[dict] | None = Field(None, description="Updated section structure.")
    metadata: dict | None = Field(None, description="Document metadata updates.")

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().lower()

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"letter", "a4", "a3", "legal", "tabloid"}
        if v.strip().lower() not in allowed:
            raise ValueError(f"Page size must be one of: {', '.join(sorted(allowed))}")
        return v.strip()

    def to_safe_dict(self) -> dict:
        """Return only the fields that were explicitly set (non-None)."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
