# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Plain Text Parser - Extract content from .txt files.

Converts plain text files to internal Document model by:
- Splitting into paragraphs (double newlines)
- Detecting potential headings (ALL CAPS, numbered, etc.)
- Preserving line breaks and structure
"""

import os
import re
from typing import List
from datetime import datetime, timezone
from pathlib import Path

from app.pipeline.parsing.base_parser import BaseParser
from app.models import (
    PipelineDocument as Document,
    DocumentMetadata,
    Block,
    BlockType,
    TextStyle,
)
from app.utils.id_generator import generate_block_id


class TxtParser(BaseParser):
    """Parses plain text (.txt) files into Document model instances."""

    def __init__(self):
        """Initialize the text parser."""
        self.block_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        """Check if this parser supports TXT format."""
        return file_extension.lower() == ".txt"

    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse a plain text file into a Document model.

        Args:
            file_path: Path to the .txt file
            document_id: Unique identifier for this document

        Returns:
            Document instance with all extracted content

        Raises:
            FileNotFoundError: If TXT file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"TXT file not found: {file_path}")

        # Reset counters
        self.block_counter = 0

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

        # Convert document_id to string if needed
        if not isinstance(document_id, str):
            document_id = str(document_id)

        # Initialize document
        document = Document(
            document_id=document_id,
            original_filename=Path(file_path).name,
            source_path=file_path,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Extract metadata (limited for plain text)
        document.metadata = DocumentMetadata()

        # Extract content
        blocks = self._extract_blocks(content)
        document.blocks = blocks

        # Add processing history
        document.add_processing_stage(
            stage_name="parsing", status="success", message=f"Parsed plain text: {len(blocks)} blocks"
        )

        return document

    def _extract_blocks(self, content: str) -> List[Block]:
        """Extract blocks from plain text content."""
        blocks = []

        # Split by double newlines (paragraphs)
        paragraphs = content.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1

            # Detect bullet lists (-, *, •, ◦)
            is_bullet_list = re.match(r"^\s*[-\*•◦]\s+", para)

            # Detect numbered lists (1., 1), a), (1), etc.)
            # STRICT LOGIC:
            # 1. Must have space after the delimiter
            # 2. Number must be reasonable (1-99) to avoid years like "1990."
            is_numbered_list = False
            num_match = re.match(r"^\s*(\d+)(\.|\))\s+", para)
            if num_match:
                number = int(num_match.group(1))
                if 0 < number < 100:  # Valid list range
                    is_numbered_list = True
            else:
                # Check for letter markers a), (1)
                is_numbered_list = re.match(r"^\s*(?:[a-z]\)|\(\d+\))\s+", para)

            # Detect potential headings
            is_potential_heading = (
                para.isupper()  # ALL CAPS
                or (
                    len(para) < 100 and not para.endswith(".") and not is_bullet_list and not is_numbered_list
                )  # Short and no period
            )

            # Preserve emails and URLs by detecting them
            has_email = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", para)
            has_url = re.search(r"https?://[^\s]+", para)

            style = TextStyle(bold=is_potential_heading)

            block = Block(
                block_id=block_id, text=para, index=self.block_counter * 100, block_type=BlockType.UNKNOWN, style=style
            )

            if is_potential_heading:
                block.metadata["potential_heading"] = True

            if is_bullet_list or is_numbered_list:
                block.metadata["is_list_item"] = True
                block.metadata["list_type"] = "ordered" if is_numbered_list else "unordered"

            if has_email:
                block.metadata["contains_email"] = True

            if has_url:
                block.metadata["contains_url"] = True

            blocks.append(block)

        return blocks
