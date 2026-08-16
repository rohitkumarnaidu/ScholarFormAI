# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Shared test utilities for ScholarForm AI tests.

Usage:
    from tests.helpers import make_doc, make_block, make_section_block
"""

from __future__ import annotations

from unittest.mock import MagicMock


def make_doc(**overrides):
    """Create a MagicMock PipelineDocument with sensible defaults."""
    doc = MagicMock()
    doc.blocks = []
    doc.references = []
    doc.figures = []
    doc.tables = []
    doc.document_id = "test-doc-id"
    doc.original_filename = "manuscript.pdf"
    doc.formatting_options = {}
    doc.metadata = MagicMock()
    doc.metadata.ai_hints = {}
    doc.metadata.title = None
    doc.metadata.keywords = []
    doc.metadata.abstract = ""
    for k, v in overrides.items():
        setattr(doc, k, v)
    return doc


def make_block(
    text: str = "Test paragraph text.",
    index: int = 1,
    block_type: str = "body",
    font_size: float = 12.0,
    bold: bool = False,
    conf: float = 1.0,
    **overrides,
):
    """Create a MagicMock Block with sensible defaults."""
    from app.models import BlockType

    b = MagicMock()
    b.text = text
    b.index = index
    b.block_id = overrides.pop("block_id", f"b{index}")
    if isinstance(block_type, str):
        block_type = BlockType(block_type)
    b.block_type = block_type
    b.style = MagicMock()
    b.style.font_size = font_size
    b.style.bold = bold
    b.metadata = overrides.pop("metadata", {})
    b.classification_confidence = conf
    b.is_heading = block_type in (BlockType.HEADING_1, BlockType.HEADING_2, BlockType.HEADING_3, BlockType.TITLE)
    b.section_name = text if b.is_heading else ""
    for k, v in overrides.items():
        setattr(b, k, v)
    return b


def make_section_block(heading_text: str = "Section 1", level: int = 1, **overrides):
    """Create a heading block for a section."""
    from app.models import BlockType

    bt = BlockType.HEADING_1 if level == 1 else BlockType.HEADING_2
    return make_block(text=heading_text, block_type=bt, metadata={"level": level}, **overrides)


def make_sb():
    """Build a MagicMock supabase client with chained query pattern."""
    sb = MagicMock()
    t = MagicMock()
    t.select.return_value = t
    t.eq.return_value = t
    t.match.return_value = t
    t.order.return_value = t
    t.limit.return_value = t
    t.maybe_single.return_value = t
    ok = MagicMock()
    ok.data = []
    t.execute.return_value = ok
    t.insert.return_value = t
    t.update.return_value = t
    t.delete.return_value = t
    sb.table.return_value = t
    return sb
