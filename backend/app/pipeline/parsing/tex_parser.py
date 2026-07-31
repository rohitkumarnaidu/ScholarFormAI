# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

r"""
LaTeX Parser - Extract content from LaTeX (.tex) files.

Parses LaTeX source to extract:
- Document metadata (\title, \author, \date)
- Sections and subsections
- Paragraphs
- Figures (\begin{figure})
- Tables (\begin{table})
- Equations
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
)
from app.utils.id_generator import generate_block_id


class TexParser(BaseParser):
    """Parses LaTeX (.tex) files into Document model instances."""

    def __init__(self):
        """Initialize the LaTeX parser."""
        self.block_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        """Check if this parser supports LaTeX format."""
        return file_extension.lower() in [".tex", ".latex"]

    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse a LaTeX file into a Document model.

        Args:
            file_path: Path to the .tex file
            document_id: Unique identifier for this document

        Returns:
            Document instance with all extracted content

        Raises:
            FileNotFoundError: If LaTeX file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LaTeX file not found: {file_path}")

        # Reset counters
        self.block_counter = 0

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
                raise ValueError(f"Failed to read LaTeX file '{file_path}': {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Failed to open LaTeX file '{file_path}': {exc}") from exc

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
        document.metadata = self._extract_metadata(content)

        # Extract content
        blocks = self._extract_content(content)
        document.blocks = blocks

        # Add processing history
        document.add_processing_stage(
            stage_name="parsing", status="success", message=f"Parsed LaTeX: {len(blocks)} blocks"
        )

        return document

    def _extract_metadata(self, content: str) -> DocumentMetadata:
        """Extract metadata from LaTeX preamble."""
        # Remove comments first to avoid false matches
        content = self._remove_comments(content)

        metadata = DocumentMetadata()

        # Extract title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            metadata.title = self._clean_latex(title_match.group(1))

        # Extract author
        author_match = re.search(r"\\author\{([^}]+)\}", content)
        if author_match:
            author_text = self._clean_latex(author_match.group(1))
            metadata.authors = [a.strip() for a in author_text.split("\\and")]

        # Extract abstract
        abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL)
        if abstract_match:
            metadata.abstract = self._clean_latex(abstract_match.group(1)).strip()

        return metadata

    def _extract_content(self, content: str) -> List[Block]:
        """Extract blocks from LaTeX content."""
        # Remove comments first
        content = self._remove_comments(content)

        blocks = []

        # Extract document body
        doc_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, re.DOTALL)
        if doc_match:
            body = doc_match.group(1)
        else:
            body = content

        # Extract lists (itemize and enumerate)
        itemize_pattern = r"\\begin\{(itemize|enumerate)\}(.*?)\\end\{\1\}"
        for match in re.finditer(itemize_pattern, body, re.DOTALL):
            list_type = match.group(1)  # itemize or enumerate
            list_content = match.group(2)

            # Extract items
            item_pattern = r"\\item\s+([^\\]+)"
            for item_match in re.finditer(item_pattern, list_content):
                item_text = self._clean_latex(item_match.group(1)).strip()
                if item_text:
                    block_id = generate_block_id(self.block_counter)
                    self.block_counter += 1

                    block = Block(
                        block_id=block_id,
                        text=item_text,
                        index=self.block_counter * 100,
                        block_type=BlockType.UNKNOWN,
                        style=TextStyle(),
                    )
                    block.metadata["is_list_item"] = True
                    block.metadata["list_type"] = "ordered" if list_type == "enumerate" else "unordered"
                    blocks.append(block)

        # Extract tables
        table_pattern = r"\\begin\{(table|tabular)\}(.*?)\\end\{\1\}"
        for match in re.finditer(table_pattern, body, re.DOTALL):
            table_content = match.group(2)

            # Extract rows (separated by \\)
            rows = [r.strip() for r in table_content.split("\\\\") if r.strip()]
            table_text_rows = []

            for row in rows:
                # Split cells by &
                cells = [self._clean_latex(c.strip()) for c in row.split("&")]
                table_text_rows.append(" | ".join(cells))

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

        # Extract images (\includegraphics)
        img_pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^\}]+)\}"
        for match in re.finditer(img_pattern, body):
            img_filename = match.group(1)

            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1

            block = Block(
                block_id=block_id,
                text=f"Image: {img_filename}",
                index=self.block_counter * 100,
                block_type=BlockType.UNKNOWN,
                style=TextStyle(),
            )
            block.metadata["is_image_reference"] = True
            block.metadata["image_source"] = img_filename
            blocks.append(block)

        # Extract equations (display math: \[ \], equation environment)
        # Display math: \[ ... \]
        disp_math_pattern = r"\\\[(.*?)\\\]"
        for match in re.finditer(disp_math_pattern, body, re.DOTALL):
            math_content = match.group(1).strip()
            if math_content:
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text=math_content,
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(),
                )
                block.metadata["is_equation"] = True
                blocks.append(block)

        # Equation environment
        eq_pattern = r"\\begin\{equation\}(.*?)\\end\{equation\}"
        for match in re.finditer(eq_pattern, body, re.DOTALL):
            math_content = match.group(1).strip()
            if math_content:
                block_id = generate_block_id(self.block_counter)
                self.block_counter += 1

                block = Block(
                    block_id=block_id,
                    text=math_content,
                    index=self.block_counter * 100,
                    block_type=BlockType.UNKNOWN,
                    style=TextStyle(),
                )
                block.metadata["is_equation"] = True
                blocks.append(block)

        # Extract sections
        section_pattern = r"\\(section|subsection|subsubsection)\{([^}]+)\}"
        for match in re.finditer(section_pattern, body):
            section_type = match.group(1)
            section_title = self._clean_latex(match.group(2))

            # Determine heading level
            level_map = {"section": 1, "subsection": 2, "subsubsection": 3}
            level = level_map.get(section_type, 1)

            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1

            block = Block(
                block_id=block_id,
                text=section_title,
                index=self.block_counter * 100,
                block_type=BlockType.UNKNOWN,
                style=TextStyle(bold=True),
            )
            block.metadata["heading_level"] = level
            block.metadata["potential_heading"] = True
            blocks.append(block)

        # Extract paragraphs (text between sections)
        # Remove LaTeX commands and environments
        try:
            cleaned_body = self._clean_latex(body)
        except Exception as exc:
            logger.warning("Failed to clean LaTeX body: %s", exc)
            cleaned_body = body

        # Split into paragraphs
        paragraphs = cleaned_body.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Skip very short fragments
                try:
                    block_id = generate_block_id(self.block_counter)
                    self.block_counter += 1

                    block = Block(
                        block_id=block_id,
                        text=para,
                        index=self.block_counter * 100,
                        block_type=BlockType.UNKNOWN,
                        style=TextStyle(),
                    )
                    blocks.append(block)
                except Exception as exc:
                    logger.warning("Failed to create paragraph block: %s", exc)

        return blocks

    def _remove_comments(self, text: str) -> str:
        r"""Remove LaTeX comments (starting with %) but keep escaped \%."""
        # Simple regex: match % that is NOT preceded by \
        return re.sub(r"(?<!\\)%.*", "", text)

    def _clean_latex(self, text: str) -> str:
        """Remove LaTeX commands and keep plain text."""
        # Comments are handled by _remove_comments separately
        # but _clean_latex might be called on snippets too, so we keep a basic check?
        # Ideally, we clean structure FIRST, then clean commands.
        # But for 'clean latex', we just want text.

        # Remove common environments
        text = re.sub(r"\\begin\{[^}]+\}", "", text)
        text = re.sub(r"\\end\{[^}]+\}", "", text)

        # Remove common commands (keep their content)
        text = re.sub(r"\\textbf\{([^}]+)\}", r"\1", text)
        text = re.sub(r"\\textit\{([^}]+)\}", r"\1", text)
        text = re.sub(r"\\emph\{([^}]+)\}", r"\1", text)

        # Remove other commands
        text = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", "", text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()
