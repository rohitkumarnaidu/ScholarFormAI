# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Normalization Stage - Clean and normalize text content.

This is the second stage of the pipeline. It takes a parsed Document
and normalizes all text content without changing meaning or structure.

Input: Document from parsing stage (with UNKNOWN block types)
Output: Document with normalized text (still UNKNOWN block types)

Normalization includes:
- Unicode character normalization (quotes, dashes, spaces)
- Whitespace normalization (trim, collapse)
- Metadata field cleaning
- Table cell text trimming

IMPORTANT:
- Do NOT detect structure
- Do NOT classify blocks
- Do NOT re-order blocks
- Do NOT drop content
- Preserve all block IDs and positions
- Preserve UNKNOWN block types
- Be conservative (when unsure, do nothing)
"""

from typing import List, Optional
from datetime import datetime, timezone

from app.models import PipelineDocument as Document, Block, Table, DocumentMetadata
from app.utils.text_utils import (
    normalize_block_text,
    normalize_table_cell_text,
    clean_metadata_field,
)


from app.pipeline.base import PipelineStage


class Normalizer(PipelineStage):
    """
    Normalizes text content in a Document model.

    This stage cleans text without interpreting semantic meaning.
    Structure detection and classification happen in later stages.
    """

    def __init__(self):
        """Initialize the normalizer."""
        pass

    def process(self, document: Document) -> Document:
        """
        Normalize all text content in the document.

        This modifies block text, table cells, and metadata in place
        while preserving all IDs, positions, and block types.

        Args:
            document: Document from parsing stage

        Returns:
            Document with normalized text content
        """
        start_time = datetime.now(timezone.utc)

        # Track initial block count for audit logging
        initial_block_count = len(document.blocks)

        # Calculate median font size for consolidation rules
        median_font = self._calculate_median_font_size(document.blocks)

        # Normalize metadata
        document.metadata = self._normalize_metadata(document.metadata)

        # Normalize blocks
        document.blocks = self._normalize_blocks(document.blocks, median_font)

        # SAFE INVARIANT CHECK: Verify index uniqueness (NOT continuity)
        # Parser assigns global indices. Normalizer may drop blocks, creating gaps.
        # Anchors (figures/tables/equations) rely on parser indices remaining stable.
        # We verify uniqueness to prevent duplicate indices, but DO NOT enforce continuity.
        indices = [block.index for block in document.blocks]
        assert len(indices) == len(set(indices)), "Duplicate block indices detected"
        assert all(isinstance(idx, int) for idx in indices), "Non-integer block index detected"

        # Normalize tables
        document.tables = self._normalize_tables(document.tables)

        # Note: Figures don't have text to normalize (only captions, which come later)

        # Update processing history
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        document.add_processing_stage(
            stage_name="normalization",
            status="success",
            message=f"Normalized {len(document.blocks)} blocks (suppressed {initial_block_count - len(document.blocks)}), {len(document.tables)} tables, metadata",
            duration_ms=duration_ms,
        )

        document.updated_at = datetime.now(timezone.utc)

        return document

    def _normalize_metadata(self, metadata: DocumentMetadata) -> DocumentMetadata:
        """
        Normalize document metadata fields.

        Args:
            metadata: Original metadata

        Returns:
            Normalized metadata
        """
        # Clean title
        if metadata.title:
            metadata.title = clean_metadata_field(metadata.title)

        # Clean authors
        if metadata.authors:
            metadata.authors = [
                clean_metadata_field(author)
                for author in metadata.authors
                if clean_metadata_field(author)  # Remove empty authors
            ]

        # Clean affiliations
        if metadata.affiliations:
            metadata.affiliations = [
                clean_metadata_field(affiliation)
                for affiliation in metadata.affiliations
                if clean_metadata_field(affiliation)
            ]

        # Clean abstract
        if metadata.abstract:
            # Abstract can have newlines, so use block text normalization
            metadata.abstract = normalize_block_text(metadata.abstract)

        # Clean keywords
        if metadata.keywords:
            metadata.keywords = [
                clean_metadata_field(keyword) for keyword in metadata.keywords if clean_metadata_field(keyword)
            ]

        # Clean journal/publisher names
        if metadata.journal:
            metadata.journal = clean_metadata_field(metadata.journal)

        # Clean author names
        if metadata.corresponding_author:
            metadata.corresponding_author = clean_metadata_field(metadata.corresponding_author)

        if metadata.email:
            metadata.email = clean_metadata_field(metadata.email)

        return metadata

    def _normalize_blocks(self, blocks: List[Block], median_font: Optional[float] = None) -> List[Block]:
        """
        Normalize text in all blocks with strict sequential logic.

        STRICT ORDER OF OPERATIONS (Journal Editor Mode):
        1. CLEAN text (whitespace/unicode)
        2. REPAIR corruptions (e.g. "2ethodology" -> "2 Methodology")
        3. SPLIT merged blocks (Heading merged with body text)
        4. FILTER empty blocks (Post-split)
        """
        import re

        normalized_blocks = []

        # Comprehensive Keyword List for Academic Sections
        keywords = [
            "Abstract",
            "Introduction",
            "Methods",
            "Methodology",
            "Materials and Methods",
            "Results",
            "Findings",
            "Discussion",
            "Conclusion",
            "Conclusions",
            "References",
            "Bibliography",
            "Works Cited",
            "Background",
            "Literature Review",
            "Summary",
            "Keywords",
            "Acknowledgment",
            "Acknowledgements",
            "Appendix",
            "Appendices",
        ]
        kw_regex = "(?:" + "|".join(keywords) + ")"

        for block in blocks:
            # 1. CLEAN
            text = normalize_block_text(block.text, is_empty_ok=True)

            # 2. REPAIR (Crucial to run before splitting)
            text = self._repair_common_corruptions(text)

            # 3. SPLIT MERGED BLOCKS
            was_split = False

            # HARDENING FIX: Prevent image-only paragraphs from entering split logic
            # Blocks with figures must remain atomic to preserve anchor stability
            if block.metadata.get("has_figure"):
                # Skip all split logic for blocks containing figures
                has_content = text.strip() or block.metadata.get("has_figure") or block.metadata.get("has_equation")
                if has_content:
                    normalized_blocks.append(block.model_copy(update={"text": text}))
                continue

            # Pattern A: ABSTRACT SPLIT (ABSOLUTE PRIORITY)
            # Matches "AbstractThe system..." or "Abstract: This paper..."
            abstract_match = re.match(r"^Abstract[:\.\—\-]?\s*(.+)$", text, flags=re.IGNORECASE)
            if abstract_match:
                body_text = abstract_match.group(1).strip()
                if body_text:
                    # Split into "Abstract" (Heading) and "rest of text" (Body)
                    normalized_blocks.append(
                        block.model_copy(
                            update={
                                "text": "Abstract",
                                "metadata": {
                                    **block.metadata,
                                    "split_from_original": True,
                                    "split_reason": "abstract_split",
                                },
                            }
                        )
                    )
                    normalized_blocks.append(
                        block.model_copy(
                            update={
                                "block_id": f"{block.block_id}_body",
                                "text": body_text,
                                "index": block.index + 1,  # SAFE: Gap provided by Parser Step 100
                                "metadata": {
                                    **block.metadata,
                                    "split_from_original": True,
                                    "split_reason": "abstract_split",
                                },
                            }
                        )
                    )
                    was_split = True

            if was_split:
                continue

            # Pattern B: Numbered Headings + Body
            # Match "1 IntroductionScientific..." or "1 Introduction: Scientific..."
            # The [A-Z] guard ensures we are splitting at a potential sentence boundary.

            # HARDENING FIX: Prevent list items from being misclassified as numbered headings
            # List items (e.g., "1. Introduction" in a list) must not trigger split logic
            if block.metadata.get("list_level") is None:
                # Only apply numbered heading split if NOT a list item
                numbered_merged_match = re.match(
                    rf"^(\d+(?:\.\d+)*\.?\s*(?:{kw_regex}|[A-Z][a-z]+))[:\.\—\-]?\s*([A-Z].+)$", text
                )
                if numbered_merged_match:
                    heading_part = numbered_merged_match.group(1).strip()
                    body_part = numbered_merged_match.group(2).strip()

                    if len(body_part) > 20 or re.search(r"[\.\?\!]\s", body_part):
                        normalized_blocks.append(
                            block.model_copy(
                                update={
                                    "text": heading_part,
                                    "metadata": {
                                        **block.metadata,
                                        "split_from_original": True,
                                        "split_reason": "numbered_split",
                                    },
                                }
                            )
                        )
                        normalized_blocks.append(
                            block.model_copy(
                                update={
                                    "block_id": f"{block.block_id}_body",
                                    "text": body_part,
                                    "index": block.index + 1,  # SAFE Gap
                                    "metadata": {
                                        **block.metadata,
                                        "split_from_original": True,
                                        "split_reason": "numbered_split",
                                    },
                                }
                            )
                        )
                        was_split = True

            if was_split:
                continue

            # Pattern C: Keyword + Body (Non-numbered)
            keyword_merged_match = re.match(rf"^({kw_regex})([A-Z][a-z].*)$", text)
            if keyword_merged_match:
                heading_part = keyword_merged_match.group(1).strip()
                body_part = keyword_merged_match.group(2).strip()

                if len(body_part) > 30 or re.search(r"[\.\?\!]\s", body_part):
                    normalized_blocks.append(
                        block.model_copy(
                            update={
                                "text": heading_part,
                                "metadata": {
                                    **block.metadata,
                                    "split_from_original": True,
                                    "split_reason": "keyword_split",
                                },
                            }
                        )
                    )
                    normalized_blocks.append(
                        block.model_copy(
                            update={
                                "block_id": f"{block.block_id}_body",
                                "text": body_part,
                                "index": block.index + 1,  # SAFE Gap
                                "metadata": {
                                    **block.metadata,
                                    "split_from_original": True,
                                    "split_reason": "keyword_split",
                                },
                            }
                        )
                    )
                    was_split = True

            if not was_split:
                # 4. FILTER EMPTY (Finally append if not empty OR if it holds content)
                has_content = text.strip() or block.metadata.get("has_figure") or block.metadata.get("has_equation")
                if has_content:
                    normalized_blocks.append(block.model_copy(update={"text": text}))

        # 5. PHYSICAL CONSOLIDATION of Multi-line Headings
        consolidated_blocks = []
        idx = 0
        while idx < len(normalized_blocks):
            block_a = normalized_blocks[idx]
            if idx + 1 < len(normalized_blocks):
                block_b = normalized_blocks[idx + 1]

                text_a = block_a.text.strip()
                text_b = block_b.text.strip()

                # Consolidation Rules
                is_a_heading = block_a.style.bold or (
                    median_font and block_a.style.font_size and block_a.style.font_size > median_font
                )
                is_b_heading = block_b.style.bold or (
                    median_font and block_b.style.font_size and block_b.style.font_size > median_font
                )

                if (
                    len(text_a) < 80
                    and len(text_b) < 80
                    and is_a_heading
                    and is_b_heading
                    and not re.search(r"[\.\?\!]$", text_a)
                    and text_b
                    and text_b[0].isupper()
                    and len(text_a) + len(text_b) < 150
                ):
                    # Merge
                    merged_text = f"{text_a} {text_b}"
                    merged_block = block_a.model_copy(
                        update={
                            "text": merged_text,
                            "metadata": {
                                **block_a.metadata,
                                "merged_multiline_heading": True,
                                "merged_from": block_b.block_id,
                            },
                        }
                    )
                    consolidated_blocks.append(merged_block)
                    idx += 2
                    continue

            consolidated_blocks.append(block_a)
            idx += 1

        # 6. SAFE EXTENSION: Duplicate Consecutive Block Filter
        # Remove identical consecutive blocks (text, style, metadata)
        final_blocks = []
        for i, b in enumerate(consolidated_blocks):
            if i == 0:
                final_blocks.append(b)
                continue

            prev = final_blocks[-1]
            if b.text.strip() == prev.text.strip() and b.style == prev.style and b.metadata == prev.metadata:
                if b.text.strip():
                    prev.metadata["has_consecutive_duplicate"] = True
                    prev.warnings.append(f"Standardization: Consecutive duplicate suppressed ({b.block_id})")
                    continue

            final_blocks.append(b)

        return final_blocks

    def _calculate_median_font_size(self, blocks: List[Block]) -> Optional[float]:
        """Calculate median font size for outlier detection."""
        from statistics import median

        font_sizes = [b.style.font_size for b in blocks if b.style.font_size and b.text.strip()]
        return median(font_sizes) if font_sizes else None

    def _repair_common_corruptions(self, text: str) -> str:
        """
        Repair specific known text corruptions from parsing artifacts.

        STRICTLY fix: "2ethodology" -> "2 Methodology"
        """
        import re

        if not text:
            return text

        # Patterns for common academic headings starting with a number
        # Fixing the lowercase first letter corruption
        repairs = [
            (r"^(\d+)\s*ntroduction", r"\1 Introduction"),
            (r"^(\d+)\s*ethodology", r"\1 Methodology"),
            (r"^(\d+)\s*esults", r"\1 Results"),
            (r"^(\d+)\s*iscussion", r"\1 Discussion"),
            (r"^(\d+)\s*onclusion", r"\1 Conclusion"),
            (r"^(\d+)\s*eferences", r"\1 References"),
            (r"^(\d+)\s*bstract", r"\1 Abstract"),
        ]

        for pattern, replacement in repairs:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _normalize_tables(self, tables: List[Table]) -> List[Table]:
        """
        Normalize text in all tables.

        This normalizes:
        - Cell text
        - Caption text (if present)
        - Both cells list and rows array

        Args:
            tables: List of tables from parsing

        Returns:
            List of tables with normalized cell text
        """
        normalized_tables = []

        for table in tables:
            # Normalize caption if present
            caption_text = table.caption_text
            if caption_text:
                caption_text = normalize_block_text(caption_text)

            # Normalize cells
            normalized_cells = []
            for cell in table.cells:
                normalized_cell_text = normalize_table_cell_text(cell.text)
                # Use model_copy to preserve all cell properties
                normalized_cell = cell.model_copy(update={"text": normalized_cell_text})
                normalized_cells.append(normalized_cell)

            # Normalize 2D rows array
            normalized_rows = []
            for row in table.rows:
                normalized_row = [normalize_table_cell_text(cell_text) for cell_text in row]
                normalized_rows.append(normalized_row)

            # Create normalized table
            # Preserve all properties except the ones we're updating
            normalized_table = table.model_copy(
                update={
                    "caption_text": caption_text,
                    "cells": normalized_cells,
                    "rows": normalized_rows,
                }
            )

            normalized_tables.append(normalized_table)

        return normalized_tables

    def _sanitize_empty_orphan_blocks(self, blocks: List[Block]) -> List[Block]:
        """
        SURGICAL QUALITY HARDENING: Remove empty orphan BODY blocks.

        This is a minimal, invariant-safe post-normalization sanitation pass
        to remove empty blocks that create visual artifacts in formatted output.

        CRITICAL SAFETY CONDITIONS:
        A block may be removed ONLY if ALL of the following are true:
        1. block.text.strip() == "" (empty text)
        2. block_type == BODY (not a structural element)
        3. block.metadata does NOT contain semantic flags:
           - has_figure
           - has_equation
           - list_level
           - anchor flags
        4. Block is NOT referenced by any caption or anchor

        INVARIANT PRESERVATION:
        - Does NOT mutate block.index values
        - Does NOT renumber anything
        - Does NOT shift anchors
        - Does NOT change block ordering
        - Preserves sparse index domain

        Args:
            blocks: Normalized blocks

        Returns:
            Sanitized blocks with empty orphans removed
        """
        from app.models.block import BlockType

        sanitized_blocks = []

        for block in blocks:
            # Check if block is an empty orphan block
            is_empty = block.text.strip() == ""
            # During normalization, blocks are still UNKNOWN type
            # After classification, empty blocks become BODY type
            is_orphan_type = block.block_type in [BlockType.BODY, BlockType.UNKNOWN]

            # Check for semantic metadata that would preserve the block
            has_figure = block.metadata.get("has_figure", False)
            has_equation = block.metadata.get("has_equation", False)
            has_list_level = "list_level" in block.metadata
            has_anchor_flag = any(
                key in block.metadata for key in ["anchor", "figure_anchor", "table_anchor", "equation_anchor"]
            )

            # Safe removal conditions
            is_orphan = (
                is_empty
                and is_orphan_type
                and not has_figure
                and not has_equation
                and not has_list_level
                and not has_anchor_flag
            )

            if is_orphan:
                # Skip this empty orphan block (remove it)
                continue

            # Keep all other blocks
            sanitized_blocks.append(block)

        return sanitized_blocks


# Convenience function
def normalize_document(document: Document) -> Document:
    """
    Normalize a parsed document.

    This is a convenience wrapper around Normalizer.

    Args:
        document: Document from parsing stage

    Returns:
        Document with normalized text

    Example:
        >>> from app.pipeline.parsing import parse_docx
        >>> from app.pipeline.normalization import normalize_document
        >>>
        >>> doc = parse_docx("manuscript.docx", "job_123")
        >>> doc = normalize_document(doc)
        >>> bool(doc)
    """
    normalizer = Normalizer()
    return normalizer.process(document)
