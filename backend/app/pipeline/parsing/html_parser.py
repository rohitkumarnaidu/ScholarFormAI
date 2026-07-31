# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
HTML Parser - Extract content from HTML files.

Uses BeautifulSoup to parse HTML and extract:
- Headings (h1, h2, h3, etc.)
- Paragraphs
- Images
- Tables
- Lists
"""

import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

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


class HtmlParser(BaseParser):
    """Parses HTML files into Document model instances."""

    def __init__(self):
        """Initialize the HTML parser."""
        if not BS4_AVAILABLE:
            raise ImportError("BeautifulSoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")
        self.block_counter = 0
        self.figure_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        """Check if this parser supports HTML format."""
        return file_extension.lower() in [".html", ".htm"]

    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse an HTML file into a Document model.

        Args:
            file_path: Path to the .html file
            document_id: Unique identifier for this document

        Returns:
            Document instance with all extracted content

        Raises:
            FileNotFoundError: If HTML file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HTML file not found: {file_path}")

        # Reset counters
        self.block_counter = 0
        self.figure_counter = 0

        # Read and parse HTML
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed for '%s'; falling back to latin-1.", file_path)
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    soup = BeautifulSoup(f, "html.parser")
            except Exception as exc:
                raise ValueError(f"Failed to read HTML file '{file_path}': {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to open HTML file '{file_path}': {exc}") from exc

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

        # Extract metadata
        document.metadata = self._extract_metadata(soup)

        # Extract content
        blocks, figures = self._extract_content(soup)

        document.blocks = blocks
        document.figures = figures

        # Add processing history
        document.add_processing_stage(
            stage_name="parsing", status="success", message=f"Parsed HTML: {len(blocks)} blocks, {len(figures)} figures"
        )

        return document

    def _extract_metadata(self, soup) -> DocumentMetadata:
        """Extract metadata from HTML head."""
        metadata = DocumentMetadata()

        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            metadata.title = title_tag.get_text().strip()

        # Extract meta tags
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            metadata.authors = [meta_author["content"]]

        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description and meta_description.get("content"):
            metadata.abstract = meta_description["content"]

        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            metadata.keywords = [k.strip() for k in meta_keywords["content"].split(",")]

        return metadata

    def _extract_content(self, soup) -> Tuple[List[Block], List[Figure]]:
        """Extract blocks and figures from HTML body."""
        blocks = []
        figures = []

        # Security/Cleanliness: Remove script and style tags
        for script in soup(["script", "style"]):
            script.decompose()

        # Find body or use whole document
        body = soup.find("body") or soup

        # Extract content in order
        for element in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "img", "pre", "code", "table"]):
            try:
                if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    # Heading
                    text = element.get_text().strip()
                    if text:
                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        level = int(element.name[1])  # h1 -> 1, h2 -> 2, etc.

                        block = Block(
                            block_id=block_id,
                            text=text,
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=TextStyle(bold=True),
                        )
                        block.metadata["heading_level"] = level
                        block.metadata["potential_heading"] = True
                        blocks.append(block)

                elif element.name == "p":
                    # Paragraph - check for formatting
                    text = element.get_text().strip()
                    if text:
                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        # Detect formatting
                        has_bold = element.find(["b", "strong"]) is not None
                        has_italic = element.find(["i", "em"]) is not None

                        # Extract links
                        links = []
                        for link in element.find_all("a"):
                            href = link.get("href", "")
                            if href:
                                links.append(href)

                        block = Block(
                            block_id=block_id,
                            text=text,
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=TextStyle(bold=has_bold, italic=has_italic),
                        )

                        if links:
                            block.metadata["links"] = links

                        blocks.append(block)

                elif element.name == "li":
                    # List item
                    text = element.get_text().strip()
                    if text:
                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        # Check if parent is ordered or unordered
                        parent = element.parent
                        is_ordered = parent.name == "ol" if parent else False

                        block = Block(
                            block_id=block_id,
                            text=text,
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=TextStyle(),
                        )
                        block.metadata["is_list_item"] = True
                        block.metadata["list_type"] = "ordered" if is_ordered else "unordered"
                        blocks.append(block)

                elif element.name in ["pre", "code"]:
                    # Code block
                    text = element.get_text()
                    if text.strip():
                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        # Try to detect language from class (e.g., class="language-python")
                        code_lang = "plaintext"
                        classes = element.get("class", [])
                        for cls in classes:
                            if cls.startswith("language-"):
                                code_lang = cls.replace("language-", "")
                                break

                        block = Block(
                            block_id=block_id,
                            text=text,
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=TextStyle(),
                        )
                        block.metadata["is_code_block"] = True
                        block.metadata["code_language"] = code_lang
                        blocks.append(block)

                elif element.name == "table":
                    # Table extraction
                    table_text_rows = []

                    for row in element.find_all("tr"):
                        cells = row.find_all(["th", "td"])
                        row_text = " | ".join([cell.get_text().strip() for cell in cells])
                        if row_text:
                            table_text_rows.append(row_text)

                    if table_text_rows:
                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        block = Block(
                            block_id=block_id,
                            text="\n".join(table_text_rows),
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=TextStyle(),
                        )
                        block.metadata["is_table"] = True
                        blocks.append(block)

                elif element.name == "img":
                    # Image (placeholder - actual image data would need to be fetched)
                    src = element.get("src", "")
                    alt = element.get("alt", "")

                    figure_id = generate_figure_id(self.figure_counter)
                    self.figure_counter += 1

                    figure = Figure(
                        figure_id=figure_id,
                        index=self.figure_counter,
                        caption_text=alt,
                        image_format=ImageFormat.UNKNOWN,
                    )
                    figure.metadata["src"] = src
                    figures.append(figure)
            except Exception as exc:
                logger.warning("Failed to extract element <%s>: %s", getattr(element, "name", "?"), exc)

        return blocks, figures
