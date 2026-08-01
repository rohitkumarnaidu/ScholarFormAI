# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Table Model - Represents a table with rows, columns, and data.

Tables are extracted by the tables/ pipeline stage.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class TableCell(BaseModel):
    """Represents a single cell in a table."""

    row: int = Field(..., description="Row index (0-based)", ge=0)
    col: int = Field(..., description="Column index (0-based)", ge=0)
    text: str = Field(default="", description="Cell text content")

    # Spanning information
    rowspan: int = Field(default=1, description="Number of rows this cell spans", ge=1)
    colspan: int = Field(default=1, description="Number of columns this cell spans", ge=1)

    # Styling
    is_header: bool = Field(default=False, description="Whether this cell is a header")
    bold: bool = Field(default=False, description="Bold text")
    italic: bool = Field(default=False, description="Italic text")
    alignment: str | None = Field(
        default=None,
        description="Text alignment (left, center, right)",
    )

    # Extensibility
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (e.g., nested tables)",
    )

    @field_validator("alignment")
    @classmethod
    def validate_alignment(cls, v: str | None) -> str | None:
        """Ensure alignment is one of the accepted values."""
        if v is not None and v not in ("left", "center", "right", "justify"):
            logger.warning("Invalid alignment value '%s'; setting to None.", v)
            return None
        return v

    model_config = {"frozen": False}  # Allow metadata updates during extraction phase


class Table(BaseModel):
    """
    Represents a table in the document.

    Tables are extracted with their structure and content.
    Captions may appear above or below the table.
    """

    # Unique identifier
    table_id: str = Field(..., description="Unique identifier (e.g., 'tbl_001')")

    # Sequential numbering (assigned by formatting stage)
    number: int | None = Field(
        default=None,
        description="Sequential table number in document (e.g., 1 for 'Table 1')",
    )

    # Table structure
    num_rows: int = Field(..., description="Total number of rows", ge=0)
    num_cols: int = Field(..., description="Total number of columns", ge=0)

    # Table data
    cells: list[TableCell] = Field(
        default_factory=list,
        description="List of all table cells",
    )

    # Table data (Source of Truth)
    data: list[list[str]] = Field(
        default_factory=list,
        description="2D array representation of table (row-major order). data[row][col] = text",
    )

    # Backward compatibility
    rows: list[list[str]] = Field(
        default_factory=list,
        description="2D array representation of table (row-major order)",
    )

    # Header information
    has_header: bool = Field(
        default=False,
        description="Whether the table has a header row",
    )
    has_header_row: bool = Field(
        default=False,
        description="Whether first row is a header",
    )
    has_header_col: bool = Field(
        default=False,
        description="Whether first column is a header",
    )
    header_rows: int = Field(
        default=0,
        description="Number of header rows",
        ge=0,
    )

    # Position in document
    page_number: int | None = Field(
        default=None,
        description="Page where table appears",
    )
    index: int = Field(
        ...,
        description="Sequential position among all tables (0-based)",
        ge=0,
    )
    block_index: int = Field(
        ...,
        description="Global block index in document order (shared with text blocks)",
        ge=0,
    )

    # Caption information
    caption_text: str | None = Field(
        default=None,
        description="Full caption text (e.g., 'Table 1: Experimental Results')",
    )
    caption_block_id: str | None = Field(
        default=None,
        description="Block ID of the caption block",
    )
    caption_position: str | None = Field(
        default=None,
        description="Caption position relative to table (above, below)",
    )

    # Parsed caption components
    label: str | None = Field(
        default=None,
        description="Table label (e.g., 'Table 1', 'Table I')",
    )
    title: str | None = Field(
        default=None,
        description="Descriptive title from caption",
    )

    # Cross-references
    referenced_by: list[str] = Field(
        default_factory=list,
        description="List of block IDs that reference this table",
    )

    # Section context
    section_name: str | None = Field(
        default=None,
        description="Section where this table appears",
    )

    # Validation
    is_valid: bool = Field(
        default=True,
        description="Whether table passed validation",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings (e.g., missing caption, inconsistent columns)",
    )

    # Formatting metadata
    placement: str | None = Field(
        default=None,
        description="Placement preference (e.g., 'top', 'bottom', 'here')",
    )
    style: str | None = Field(
        default=None,
        description="Table style (e.g., 'grid', 'simple', 'booktabs')",
    )

    # Extensibility
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @field_validator("table_id")
    @classmethod
    def validate_table_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("table_id must be a non-empty string")
        return v.strip()

    model_config = {"use_enum_values": True}

    def has_caption(self) -> bool:
        """Check if table has an associated caption."""
        try:
            return bool(self.caption_text and self.caption_text.strip())
        except Exception as exc:
            logger.error("Error in Table.has_caption for '%s': %s", self.table_id, exc)
            return False

    def get_cell(self, row: int, col: int) -> TableCell | None:
        """Get cell at specified row and column. Returns None if not found."""
        if row < 0 or col < 0:
            logger.warning("get_cell called with negative indices (%d, %d)", row, col)
            return None
        try:
            for cell in self.cells:
                if cell.row == row and cell.col == col:
                    return cell
        except Exception as exc:
            logger.error(
                "Error in get_cell(%d, %d) for table '%s': %s",
                row,
                col,
                self.table_id,
                exc,
            )
        return None

    def get_display_label(self) -> str:
        """Get display label for this table. Always returns a non-empty string."""
        try:
            if self.label:
                return self.label
            if self.number is not None:
                return f"Table {self.number}"
            return f"Table {self.table_id}"
        except Exception as exc:
            logger.error("Error in get_display_label for '%s': %s", self.table_id, exc)
            return f"Table {self.table_id}"

    def get_row_data(self, row: int) -> list[str]:
        """Get all cell text for a specific row. Returns empty list on error or out-of-bounds."""
        if row < 0:
            logger.warning("get_row_data called with negative row index %d", row)
            return []
        try:
            if row < len(self.rows):
                return list(self.rows[row])
            if row < len(self.data):
                return list(self.data[row])
        except Exception as exc:
            logger.error(
                "Error in get_row_data(%d) for table '%s': %s",
                row,
                self.table_id,
                exc,
            )
        return []
