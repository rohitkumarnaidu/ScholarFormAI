# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Block Model - Represents a text block (paragraph, heading, list item, etc.)

This is the fundamental unit of content in the document pipeline.
Each block represents a contiguous piece of text with associated metadata.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BlockType(StrEnum):
    """Classification of block content types."""

    # Structural elements
    TITLE = "title"

    # Headings
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    HEADING_4 = "heading_4"

    # Abstract & Keywords
    ABSTRACT_HEADING = "abstract_heading"
    ABSTRACT_BODY = "abstract_body"
    KEYWORDS_HEADING = "keywords_heading"
    KEYWORDS_BODY = "keywords_body"

    # Main Content
    BODY = "body"  # Main body text (paragraphs)
    PARAGRAPH = "paragraph"  # Kept for compatibility, alias to BODY concept
    LIST_ITEM = "list_item"
    QUOTE = "quote"
    CODE = "code"

    # Metadata elements
    AUTHOR = "author"
    AFFILIATION = "affiliation"

    # References
    REFERENCES_HEADING = "references_heading"
    REFERENCE_ENTRY = "reference_entry"

    # Special sections
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"
    EQUATION = "equation"

    # Supplemental Academic Sections
    ACKNOWLEDGEMENTS = "acknowledgements"
    FUNDING = "funding"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    FOOTNOTE = "footnote"

    # Unclassified
    UNKNOWN = "unknown"

    # Legacy/Aliases (optional, kept if needed)
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"
    REFERENCE_ITEM = "reference_item"


class ListType(StrEnum):
    """Type of list if block is a list item."""

    ORDERED = "ordered"
    UNORDERED = "unordered"


class TextStyle(BaseModel):
    """Fine-grained text styling information."""

    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    font_name: str | None = None
    font_size: float | None = None  # in points
    color: str | None = None  # hex color code

    model_config = ConfigDict(frozen=True)  # Immutable


class Block(BaseModel):
    """
    Represents a single text block in the document.

    Blocks flow through the pipeline and are enriched with metadata
    at each stage (structure detection, classification, etc.).
    """

    # Unique identifier for this block
    block_id: str = Field(..., description="Unique identifier for this block")

    # Content
    text: str = Field(..., description="Raw text content")

    # Classification (assigned by structure_detection and classification stages)
    block_type: BlockType = Field(default=BlockType.UNKNOWN, description="Semantic type of this block")

    # Position information (assigned by parser)
    index: int = Field(..., description="Sequential position in document (0-based)")
    page_number: int | None = Field(default=None, description="Page number if available from parser")

    # Styling (extracted by parser)
    style: TextStyle = Field(default_factory=TextStyle, description="Visual styling information")

    # Hierarchical information (assigned by structure_detection)
    level: int | None = Field(default=None, description="Hierarchy level (e.g., heading depth, list nesting)")
    parent_id: str | None = Field(default=None, description="Block ID of parent block (e.g., section heading)")

    # List-specific metadata
    list_type: ListType | None = Field(default=None, description="Type of list if this is a list item")
    list_level: int | None = Field(default=None, description="Nesting level if this is a list item (0-based)")

    # Section information (assigned by structure_detection)
    section_name: str | None = Field(
        default=None, description="Name of the section this block belongs to (e.g., 'Introduction', 'Methods')"
    )

    # Semantic information (assigned by classification)
    semantic_intent: str | None = Field(
        default=None, description="Semantic label for classification (e.g., 'ABSTRACT_BODY')"
    )
    classification_confidence: float | None = Field(
        default=None, description="Confidence score for semantic classification"
    )

    # Cross-reference metadata (assigned by references stage)
    contains_citation: bool = Field(default=False, description="Whether this block contains inline citations")
    citation_keys: list[str] = Field(
        default_factory=list, description="List of citation keys found in this block (e.g., ['Smith2020', 'Jones2021'])"
    )

    # Validation and quality flags (assigned by validation stage)
    is_valid: bool = Field(default=True, description="Whether this block passed validation")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings for this block")

    # Extensibility for pipeline-specific metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata added by pipeline stages")

    model_config = ConfigDict(use_enum_values=True)

    def is_heading(self) -> bool:
        """Check if this block is a heading."""
        return self.block_type in {
            BlockType.HEADING_1,
            BlockType.HEADING_2,
            BlockType.HEADING_3,
            BlockType.HEADING_4,
        }

    def is_content(self) -> bool:
        """Check if this block is main content (paragraph, list, etc.)."""
        return self.block_type in {
            BlockType.PARAGRAPH,
            BlockType.LIST_ITEM,
            BlockType.QUOTE,
            BlockType.CODE,
        }

    def is_metadata(self) -> bool:
        """Check if this block is document metadata."""
        return self.block_type in {
            BlockType.TITLE,
            BlockType.AUTHOR,
            BlockType.AFFILIATION,
            BlockType.KEYWORDS,
        }
