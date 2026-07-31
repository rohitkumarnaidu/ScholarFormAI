# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Markdown Parser - Extract content from Markdown (.md) files.

Parses Markdown syntax to extract:
- Headings (# ## ###)
- Paragraphs
- Lists
- Code blocks
- Images
- Links
"""

import logging
import os
import re
from typing import List

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path

from app.pipeline.parsing.base_parser import BaseParser
from app.models import (
    PipelineDocument as Document,
    DocumentMetadata,
    Block,
    BlockType,
    TextStyle,
    Figure,
    ImageFormat,
)
from app.utils.id_generator import generate_block_id, generate_figure_id


class MarkdownParser(BaseParser):
    """Parses Markdown (.md) files into Document model instances."""

    def __init__(self):
        """Initialize the Markdown parser."""
        self.block_counter = 0
        self.figure_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        """Check if this parser supports Markdown format."""
        return file_extension.lower() in [".md", ".markdown"]

    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse a Markdown file into a Document model.

        Args:
            file_path: Path to the .md file
            document_id: Unique identifier for this document

        Returns:
            Document instance with all extracted content

        Raises:
            FileNotFoundError: If Markdown file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        # Reset counters
        self.block_counter = 0
        self.figure_counter = 0

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed for '%s'; falling back to latin-1.", file_path)
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as exc:
                raise ValueError(f"Failed to read Markdown file '{file_path}': {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to open Markdown file '{file_path}': {exc}") from exc

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

        # Extract metadata (from YAML frontmatter if present)
        content, metadata = self._extract_frontmatter(content)
        document.metadata = metadata

        # Extract content
        blocks, figures = self._extract_content(content)

        document.blocks = blocks
        document.figures = figures

        # Add processing history
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=f"Parsed Markdown: {len(blocks)} blocks, {len(figures)} figures",
        )

        return document

    def _extract_frontmatter(self, content: str) -> tuple:
        """Extract YAML frontmatter if present."""
        metadata = DocumentMetadata()

        # Check for YAML frontmatter (--- ... ---)
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter = match.group(1)
            content = content[match.end() :]

            # Simple YAML parsing (basic key: value)
            for line in frontmatter.split("\n"):
                if ":" in line:
                    try:
                        key, value = line.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()

                        if key == "title":
                            metadata.title = value
                        elif key == "author":
                            metadata.authors = [value]
                        elif key == "keywords":
                            metadata.keywords = [k.strip() for k in value.split(",") if k.strip()]
                    except Exception as exc:
                        logger.debug("Skipping malformed frontmatter line '%s': %s", line, exc)

        return content, metadata

    def _extract_content(self, content: str) -> tuple:
        """Extract blocks and figures from Markdown content."""
        blocks = []
        figures = []

        lines = content.split("\n")
        i = 0
        current_paragraph = []

        while i < len(lines):
            line = lines[i]

            # Code block (```language)
            if line.strip().startswith("```"):
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Extract code block
                code_lang = line.strip()[3:].strip()  # Language after ```
                code_lines = []
                i += 1

                # Collect until closing ```
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                # Create code block
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text="\n".join(code_lines),
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(),
                )
                block.metadata["is_code_block"] = True
                block.metadata["code_language"] = code_lang or "plaintext"
                blocks.append(block)

                i += 1  # Skip closing ```
                continue

            # Table (| Col | Col |)
            elif line.strip().startswith("|") and "|" in line.strip()[1:]:
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Extract table
                table_lines = [line]
                i += 1

                # Collect table rows
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1

                # Create table block (simplified - just store as text)
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text="\n".join(table_lines),
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(),
                )
                block.metadata["is_table"] = True
                blocks.append(block)
                continue

            # Blockquote (> quote)
            elif line.strip().startswith(">"):
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Extract blockquote
                quote_lines = [line.strip()[1:].strip()]  # Remove >
                i += 1

                # Collect consecutive quote lines
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quote_lines.append(lines[i].strip()[1:].strip())
                    i += 1

                # Create blockquote block
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text=" ".join(quote_lines),
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(italic=True),
                )
                block.metadata["is_blockquote"] = True
                blocks.append(block)
                continue

            # Heading
            elif line.startswith("#"):
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Create heading block
                heading_text = line.lstrip("#").strip()
                level = len(line) - len(line.lstrip("#"))

                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text=heading_text,
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(bold=True),
                )
                block.metadata["heading_level"] = level
                block.metadata["potential_heading"] = True
                blocks.append(block)

            # Horizontal rule (---, ***, ___)
            elif re.match(r"^[\-\*_]{3,}\s*$", line.strip()):
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []
                # Skip horizontal rules entirely - don't create a block

            # Footnote Definition ([^ref]: text)
            elif re.match(r"^\[\^[^\]]+\]:", line.strip()):
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Extract footnote
                footnote_text = line.strip()
                # If subsequent lines are indented, they belong to the footnote (simplified: just take one line or until next block)
                # Helper: just take the line for now, or accumulate if strictly indented?
                # Markdown footnotes can be multi-line if indented 4 spaces.
                # For simplicity/robustness, we'll treat it as a block.

                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text=footnote_text,  # Keep the definition marker or strip it? keep for now
                    index=self.block_counter * 100,
                    block_type=BlockType.FOOTNOTE,
                    style=TextStyle(font_size=10.0),  # Usually smaller
                )
                blocks.append(block)

            # Image ![alt](url)
            elif "![" in line:
                # Save previous paragraph
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

                # Extract image
                img_pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
                for match in re.finditer(img_pattern, line):
                    alt_text = match.group(1)
                    url = match.group(2)

                    figure_id = generate_figure_id(self.figure_counter)
                    self.figure_counter += 1

                    figure = Figure(
                        figure_id=figure_id,
                        index=self.figure_counter,
                        caption_text=alt_text,
                        image_format=ImageFormat.UNKNOWN,
                    )
                    figure.metadata["src"] = url
                    figures.append(figure)

            # Empty line (paragraph break)
            elif line.strip() == "":
                if current_paragraph:
                    blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))
                    current_paragraph = []

            # Regular text
            else:
                current_paragraph.append(line)

            i += 1

        # Save final paragraph
        if current_paragraph:
            blocks.append(self._create_paragraph_block("\n".join(current_paragraph)))

        return blocks, figures

    def _strip_markdown(self, text: str) -> str:
        """
        Strip markdown syntax and return clean text.

        Note: This removes markdown formatting but preserves emails and URLs.

        Returns:
            cleaned_text (string only, no style info)
        """
        cleaned = text

        # Protect Math (replace with placeholder)
        math_blocks = []

        def replace_math(match):
            math_blocks.append(match.group(0))
            return f"{{{{MATH_BLOCK_{len(math_blocks) - 1}}}}}"

        # Protect code blocks within text too (if any remaining)
        cleaned = re.sub(r"(\$\$[\s\S]*?\$\$|\$[^\$]*?\$)", replace_math, cleaned)

        # Remove bold (**text** or __text__)
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"__(.+?)__", r"\1", cleaned)

        # Remove italic (*text* or _text_) - but avoid underscores in emails/URLs
        cleaned = re.sub(r"\*([^\*]+?)\*", r"\1", cleaned)
        cleaned = re.sub(r"(?<!\S)_([^_]+?)_(?!\S)", r"\1", cleaned)

        # Remove strikethrough (~~text~~)
        cleaned = re.sub(r"~~(.+?)~~", r"\1", cleaned)

        # Remove inline code (`code`)
        cleaned = re.sub(r"`(.+?)`", r"\1", cleaned)

        # Remove links [text](url) -> keep text, but preserve bare URLs
        cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

        # Remove footnote refs [^1]
        cleaned = re.sub(r"\[\^[^\]]+\]", "", cleaned)

        # Remove list markers (but keep the text)
        cleaned = re.sub(r"^\s*[\*\-\+]\s+", "", cleaned)  # Unordered lists
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned)  # Ordered lists

        # Restore Math
        for i, block in enumerate(math_blocks):
            cleaned = cleaned.replace(f"{{{{MATH_BLOCK_{i}}}}}", block)

        return cleaned.strip()

    def _create_paragraph_block(self, text: str) -> Block:
        """Create a paragraph block from text."""
        block_id = generate_block_id(self.block_counter)
        self.block_counter += 1

        # Detect list items (before stripping)
        is_list = text.strip().startswith(("-", "*", "+")) or re.match(r"^\d+\.", text.strip())
        hyperlinks = [
            {"text": match.group(1).strip(), "url": match.group(2).strip()}
            for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text)
            if match.group(1).strip() and match.group(2).strip()
        ]
        footnote_refs = re.findall(r"\[\^([^\]]+)\]", text)

        # Strip markdown syntax (returns plain text only)
        cleaned_text = self._strip_markdown(text)

        # Don't apply block-level formatting - let Word handle it
        style = TextStyle()

        block = Block(
            block_id=block_id,
            text=cleaned_text,  # Use cleaned text without markdown syntax
            index=self.block_counter * 100,
            block_type=BlockType.UNKNOWN,
            style=style,
        )

        if is_list:
            block.metadata["is_list_item"] = True
        if hyperlinks:
            block.metadata["hyperlinks"] = hyperlinks
        if footnote_refs:
            block.metadata["footnote_refs"] = footnote_refs

        return block
