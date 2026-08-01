# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Equation Model - Represents mathematical content.

Equations are extracted by the parsing stage and numbered by the formatting stage.
"""

from typing import Any

from pydantic import BaseModel, Field


class Equation(BaseModel):
    """
    Represents an equation in the document.
    Supports both block (display) and inline equations.
    """

    # Unique identifier
    equation_id: str = Field(..., description="Unique identifier (e.g., 'eqn_001')")

    # Sequential numbering
    number: str | None = Field(default=None, description="Sequential number (e.g., '(1)')")

    # Content
    text: str | None = Field(default=None, description="Plain text representation")
    mathml: str | None = Field(default=None, description="MathML representation")
    omml: str | None = Field(default=None, description="Office Math Markup Language (Word)")

    # Positioning
    is_block: bool = Field(default=True, description="True if block/display equation, False if inline")
    index: int = Field(..., description="Sequential position in document")
    block_id: str | None = Field(default=None, description="Parent block ID")

    # Relation
    referenced_by: list[str] = Field(default_factory=list, description="List of block IDs that reference this equation")

    # Metadata for formatting
    metadata: dict[str, Any] = Field(default_factory=dict)

    def has_content(self) -> bool:
        """Check if equation has any valid representation."""
        return any([self.text, self.mathml, self.omml])

    def get_display_number(self) -> str:
        """Get the formatted numbering string."""
        return self.number if self.number else ""
