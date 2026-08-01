# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Figure Model - Represents an image/figure with caption and metadata.

Figures are extracted by the figures/ pipeline stage and associated
with their captions through caption matching.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FigureType(StrEnum):
    """Type of figure content."""

    DIAGRAM = "diagram"
    CHART = "chart"
    GRAPH = "graph"
    PHOTOGRAPH = "photograph"
    SCREENSHOT = "screenshot"
    ILLUSTRATION = "illustration"
    UNKNOWN = "unknown"


class ImageFormat(StrEnum):
    """Image file format."""

    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"
    SVG = "svg"
    EMF = "emf"
    WMF = "wmf"
    UNKNOWN = "unknown"


class Figure(BaseModel):
    """
    Represents a figure/image in the document.

    Figures are extracted with their positioning, size, and caption information.
    The caption is matched to the figure by the caption_matcher.
    """

    # Unique identifier
    figure_id: str = Field(..., description="Unique identifier (e.g., 'fig_001')")

    # Sequential numbering (assigned by formatting stage)
    number: int | None = Field(
        default=None, description="Sequential figure number in document (e.g., 1 for 'Figure 1')"
    )

    # Image data
    image_data: bytes | None = Field(default=None, description="Raw binary image data extracted from document")
    image_format: ImageFormat = Field(default=ImageFormat.UNKNOWN, description="Image format/extension")

    # Dimensions (in pixels or original units)
    width: float | None = Field(default=None, description="Image width in original units")
    height: float | None = Field(default=None, description="Image height in original units")

    # Position in document
    page_number: int | None = Field(default=None, description="Page where figure appears")
    index: int = Field(..., description="Sequential position among all figures (0-based)")

    # Caption information (matched by caption_matcher)
    caption_text: str | None = Field(
        default=None, description="Full caption text (e.g., 'Figure 1: System Architecture')"
    )
    caption_block_id: str | None = Field(default=None, description="Block ID of the caption block")

    # Parsed caption components
    label: str | None = Field(default=None, description="Figure label (e.g., 'Figure 1', 'Fig. 2')")
    title: str | None = Field(default=None, description="Descriptive title from caption (e.g., 'System Architecture')")

    # Classification
    figure_type: FigureType = Field(default=FigureType.UNKNOWN, description="Type of figure content")

    # Cross-references
    referenced_by: list[str] = Field(default_factory=list, description="List of block IDs that reference this figure")

    # Section context
    section_name: str | None = Field(default=None, description="Section where this figure appears")

    # Validation
    is_valid: bool = Field(default=True, description="Whether figure passed validation")
    warnings: list[str] = Field(
        default_factory=list, description="Validation warnings (e.g., missing caption, low resolution)"
    )

    # Formatting metadata (assigned by formatting stage)
    placement: str | None = Field(default=None, description="Placement preference (e.g., 'top', 'bottom', 'here')")

    # File export information (assigned by export stage)
    export_filename: str | None = Field(default=None, description="Filename for exported image (e.g., 'figure_1.png')")
    export_path: str | None = Field(default=None, description="Path where image was exported")

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(use_enum_values=True)

    def has_caption(self) -> bool:
        """Check if figure has an associated caption."""
        return self.caption_text is not None and len(self.caption_text.strip()) > 0

    def get_display_label(self) -> str:
        """Get display label for this figure."""
        if self.label:
            return self.label
        if self.number:
            return f"Figure {self.number}"
        return f"Figure {self.figure_id}"
