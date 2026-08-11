# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
PDF Parser - Extract content from PDF files.

Uses PyMuPDF (fitz) to extract text, images, and basic structure from PDF documents.
Converts to internal Document model for processing through the pipeline.
"""

import hashlib
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)
from datetime import UTC, datetime
from pathlib import Path

try:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.25.0
    except ImportError:
        import fitz  # PyMuPDF < 1.25.0

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from app.models import (
    Block,
    BlockType,
    DocumentMetadata,
    Figure,
    ImageFormat,
    Table,
    TableCell,
    TextStyle,
)
from app.models import (
    PipelineDocument as Document,
)
from app.pipeline.parsing.base_parser import BaseParser
from app.utils.id_generator import generate_block_id, generate_figure_id, generate_table_id


class PdfParser(BaseParser):
    """Parses PDF files into Document model instances."""

    def __init__(self):
        """Initialize the PDF parser."""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF is required for PDF parsing. Install with: pip install PyMuPDF")
        self.block_counter = 0
        self.figure_counter = 0
        self.table_counter = 0

    def supports_format(self, file_extension: str) -> bool:
        """Check if this parser supports PDF format."""
        return file_extension.lower() == ".pdf"

    def parse(self, file_path: str, document_id: str) -> Document:
        """
        Parse a PDF file into a Document model.

        Args:
            file_path: Path to the .pdf file
            document_id: Unique identifier for this document

        Returns:
            Document instance with all extracted content

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a valid PDF
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        # Reset counters
        self.block_counter = 0
        self.figure_counter = 0
        self.table_counter = 0

        # Open PDF document
        try:
            pdf_doc = fitz.open(file_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {e}")

        # FIX #15: Check for password-protected/encrypted PDFs
        if pdf_doc.is_encrypted:
            # Try decrypting with empty password (some PDFs are "owner-locked" but readable)
            if not pdf_doc.authenticate(""):
                pdf_doc.close()
                raise ValueError("This PDF is password-protected. Please remove the password and re-upload.")

        # Convert document_id to string if needed
        if not isinstance(document_id, str):
            document_id = str(document_id)

        # Initialize document
        document = Document(
            document_id=document_id,
            original_filename=Path(file_path).name,
            source_path=file_path,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Extract metadata
        document.metadata = self._extract_metadata(pdf_doc)

        # Extract content
        blocks, figures, tables = self._extract_content(pdf_doc)
        blocks, ocr_backend = self._maybe_apply_ocr_fallback(file_path, pdf_doc, blocks)

        document.blocks = blocks
        document.figures = figures
        document.tables = tables

        # Add processing history
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=(
                f"Parsed PDF: {len(blocks)} blocks, {len(figures)} figures, "
                f"{len(tables)} tables from {len(pdf_doc)} pages"
                + (f" (OCR fallback backend: {ocr_backend})" if ocr_backend else "")
            ),
        )

        pdf_doc.close()
        return document

    def _extract_metadata(self, pdf_doc) -> DocumentMetadata:
        """Extract metadata from PDF document."""
        metadata = DocumentMetadata()

        pdf_metadata = pdf_doc.metadata
        if pdf_metadata:
            if pdf_metadata.get("title"):
                metadata.title = pdf_metadata["title"]
            if pdf_metadata.get("author"):
                metadata.authors = [pdf_metadata["author"]]
            if pdf_metadata.get("subject"):
                metadata.abstract = pdf_metadata["subject"]
            if pdf_metadata.get("keywords"):
                keywords_raw = pdf_metadata.get("keywords", "")
                metadata.keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

        return metadata

    @staticmethod
    def _should_attempt_ocr_fallback(blocks: list[Block], page_count: int) -> bool:
        """
        Determine whether OCR fallback should run for sparse-text PDFs.
        """
        if page_count <= 0:
            return False

        text_chars = sum(len((block.text or "").strip()) for block in blocks)
        chars_per_page = text_chars / max(1, page_count)

        # Conservative threshold: avoid unnecessary OCR for normal searchable PDFs.
        return text_chars < 300 or chars_per_page < 80

    def _maybe_apply_ocr_fallback(
        self,
        file_path: str,
        pdf_doc,
        parsed_blocks: list[Block],
    ) -> tuple[list[Block], str | None]:
        """
        When a PDF is likely scanned/image-based, extract OCR text and replace sparse blocks.
        Keeps core parser path unchanged if OCR is unavailable/fails.
        """
        try:
            from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
            from app.services.enhancement_manager import enhancement_manager
        except Exception as exc:
            logger.debug("OCR fallback imports unavailable: %s", exc)
            return parsed_blocks, None

        profile = enhancement_manager.profile
        if not (profile.enabled and profile.ocr_enabled):
            return parsed_blocks, None

        if not self._should_attempt_ocr_fallback(parsed_blocks, len(pdf_doc)):
            return parsed_blocks, None

        backends = [name for name in enhancement_manager.get_ocr_backends() if name in {"tesseract", "paddle"}]
        if not backends:
            return parsed_blocks, None

        ocr = PdfOCR(text_threshold=300)
        is_scanned = ocr.is_scanned(file_path)
        if not is_scanned and parsed_blocks:
            # Keep parsed text if this doesn't strongly look scanned and parser produced content.
            return parsed_blocks, None

        try:
            extracted_text, backend_used = ocr.extract_text(file_path, backends=backends)
            ocr_blocks = self._build_ocr_blocks(extracted_text, backend_used)
            if not ocr_blocks:
                return parsed_blocks, None

            logger.info(
                "PDF OCR fallback applied for %s using backend=%s (blocks: %d -> %d)",
                file_path,
                backend_used,
                len(parsed_blocks),
                len(ocr_blocks),
            )
            return ocr_blocks, backend_used
        except OCRError as exc:
            logger.warning("PDF OCR fallback failed for %s: %s", file_path, exc)
            return parsed_blocks, None
        except Exception as exc:
            logger.warning("Unexpected PDF OCR fallback error for %s: %s", file_path, exc)
            return parsed_blocks, None

    def _build_ocr_blocks(self, extracted_text: str, backend_used: str) -> list[Block]:
        """
        Build body blocks from OCR text while preserving parser Block model semantics.
        """
        cleaned_text = (extracted_text or "").strip()
        if not cleaned_text:
            return []

        # Paragraph-aware splitting first; fallback to line splitting.
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned_text) if part.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in cleaned_text.splitlines() if line.strip()]

        ocr_blocks: list[Block] = []
        for paragraph in paragraphs:
            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1
            ocr_blocks.append(
                Block(
                    block_id=block_id,
                    text=paragraph,
                    index=self.block_counter * 100,
                    block_type=BlockType.BODY,
                    page_number=None,
                    metadata={
                        "ocr_generated": True,
                        "ocr_backend": backend_used,
                    },
                )
            )
        return ocr_blocks

    def _calculate_font_stats(self, pdf_doc) -> float:
        """
        Calculate the most frequent font size (body text size) in the document.

        Returns:
            float: The body text font size (default 11.0 if detection fails)
        """
        font_sizes = {}

        # Scan a subset of pages (up to 5) to estimate font statistics
        # Scanning all pages might be too slow for large docs
        pages_to_scan = min(5, len(pdf_doc))

        for i in range(pages_to_scan):
            try:
                page = pdf_doc[i]
                text_dict = page.get_text("dict")

                for block in text_dict.get("blocks", []):
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                size = round(span.get("size", 0), 1)
                                if size > 0:
                                    font_sizes[size] = font_sizes.get(size, 0) + len(span.get("text", ""))
            except Exception:
                continue

        if not font_sizes:
            return 11.0

        # Return the font size with the most characters (weighted mode)
        body_size = max(font_sizes.items(), key=lambda x: x[1])[0]
        return body_size

    def _is_header_footer(self, block_bbox: list, page_rect: list) -> bool:
        """
        Check if a block is likely a header or footer based on position.
        """
        if not block_bbox or not page_rect:
            return False

        page_height = page_rect[3] - page_rect[1]
        if page_height <= 0:
            return False

        y0, y1 = block_bbox[1], block_bbox[3]

        # Thresholds: Top 7% or Bottom 7%
        top_threshold = page_rect[1] + (page_height * 0.07)
        bottom_threshold = page_rect[3] - (page_height * 0.07)

        # If block is strictly within top or bottom margins
        is_top = y1 <= top_threshold
        is_bottom = y0 >= bottom_threshold

        return is_top or is_bottom

    def _normalize_margin_text(self, text: str) -> str:
        """Canonical form used for repeated header/footer suppression."""
        text = (text or "").lower()
        text = re.sub(r"\bpage\s+\d+\b", " ", text)
        text = re.sub(r"\d+", " ", text)
        text = re.sub(r"\b[ivxlcdm]+\b", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _sanitize_cell_text(self, value: Any) -> str:
        """Normalize table cell value to a clean single-line string."""
        if value is None:
            return ""
        return str(value).replace("\n", " ").strip()

    def _build_table_model(
        self,
        rows: list[list[str]],
        page_number: int,
        block_index: int,
    ) -> Table | None:
        """Create a Table model from raw extracted rows."""
        if not rows:
            return None

        num_cols = max((len(r) for r in rows), default=0)
        if num_cols == 0:
            return None

        normalized_rows: list[list[str]] = []
        for row in rows:
            cleaned = [self._sanitize_cell_text(cell) for cell in row]
            if len(cleaned) < num_cols:
                cleaned.extend([""] * (num_cols - len(cleaned)))
            normalized_rows.append(cleaned)

        num_rows = len(normalized_rows)
        has_header = any(bool(v) for v in normalized_rows[0]) if normalized_rows else False
        cells: list[TableCell] = []
        for r_idx, row_vals in enumerate(normalized_rows):
            for c_idx, text in enumerate(row_vals):
                cells.append(
                    TableCell(
                        row=r_idx,
                        col=c_idx,
                        text=text,
                        is_header=(has_header and r_idx == 0),
                        bold=(has_header and r_idx == 0),
                    )
                )

        table = Table(
            table_id=generate_table_id(self.table_counter),
            index=self.table_counter,
            block_index=max(0, int(block_index)),
            page_number=page_number,
            num_rows=num_rows,
            num_cols=num_cols,
            cells=cells,
            data=normalized_rows,
            rows=normalized_rows,
            has_header=has_header,
            has_header_row=has_header,
            header_rows=1 if has_header else 0,
        )
        self.table_counter += 1
        return table

    def _extract_content(self, pdf_doc) -> tuple[list[Block], list[Figure], list[Table]]:
        """Extract text blocks, tables, and images from PDF."""
        blocks = []
        figures = []
        tables = []
        seen_margin_texts: set[str] = set()
        seen_image_hashes: set[str] = set()

        # 0. Content Analysis (Dynamic Font Sizing)
        # ------------------------------------------------
        body_font_size = self._calculate_font_stats(pdf_doc)

        # Define adaptive thresholds
        h1_threshold = body_font_size * 1.6  # e.g., 11 * 1.6 = 17.6
        h2_threshold = body_font_size * 1.3  # e.g., 11 * 1.3 = 14.3
        h3_threshold = body_font_size * 1.1  # e.g., 11 * 1.1 = 12.1 (+ bold usually)

        logger.debug(
            "PDF Analysis: Body Size=%.1fpt, H1>%.1fpt, H2>%.1fpt",
            body_font_size,
            h1_threshold,
            h2_threshold,
        )

        for page_num, page in enumerate(pdf_doc):
            # 1. Extract Tables first (PyMuPDF find_tables)
            # ------------------------------------------------
            table_rects = []
            page_tables: list[dict[str, Any]] = []
            try:
                page_tables_raw = page.find_tables()
                for table in page_tables_raw:
                    # Get table bounding box to exclude raw text later
                    table_rects.append(table.bbox)

                    header_names: list[str] = []
                    header = getattr(table, "header", None)
                    if header and hasattr(header, "names") and header.names:
                        header_names = [self._sanitize_cell_text(h) for h in header.names]

                    extracted_rows = table.extract() or []
                    normalized_rows = [[self._sanitize_cell_text(cell) for cell in row] for row in extracted_rows]
                    if header_names:
                        if normalized_rows and normalized_rows[0] == header_names:
                            normalized_rows = normalized_rows[1:]
                        normalized_rows = [header_names] + normalized_rows

                    table_model = self._build_table_model(
                        normalized_rows,
                        page_number=page_num + 1,
                        block_index=self.block_counter * 100,
                    )
                    if table_model:
                        bbox = table.bbox if table.bbox else (0.0, float("inf"), 0.0, float("inf"))
                        page_tables.append(
                            {
                                "table": table_model,
                                "y0": float(bbox[1]),
                            }
                        )
            except Exception as exc:
                logger.warning("PDF table extraction failed on page %d: %s", page_num + 1, exc)

            # 2. Extract Text (excluding tables)
            # ------------------------------------------------
            # Extract text with formatting details
            try:
                text_dict = page.get_text("dict")
            except Exception as exc:
                logger.warning("Failed to get text dict on page %d: %s", page_num + 1, exc)
                text_dict = {"blocks": []}

            page_text_positions: list[tuple[int, float]] = []
            last_text_key = ""

            # Process each block in the page
            for raw_block in text_dict.get("blocks", []):
                if raw_block.get("type") == 0:  # Text block
                    # Check if block overlaps significantly with any table
                    block_bbox = raw_block.get("bbox")
                    is_in_table = False

                    if block_bbox:
                        # specific logic: check if center of block is inside a table rect
                        b_x0, b_y0, b_x1, b_y1 = block_bbox
                        b_center_x = (b_x0 + b_x1) / 2
                        b_center_y = (b_y0 + b_y1) / 2

                        for t_rect in table_rects:
                            # t_rect is (x0, y0, x1, y1)
                            if t_rect[0] <= b_center_x <= t_rect[2] and t_rect[1] <= b_center_y <= t_rect[3]:
                                is_in_table = True
                                break

                    if is_in_table:
                        continue  # Skip text that is part of a table

                    block_text_parts = []
                    avg_font_size = 0
                    font_sizes = []
                    is_bold = False
                    is_italic = False

                    # Extract text and analyze styles from spans
                    for line in raw_block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            line_text += span_text

                            # Track font size for heading detection
                            font_size = span.get("size", 0)
                            if font_size > 0:
                                font_sizes.append(font_size)

                            # Check font flags for bold/italic
                            flags = span.get("flags", 0)
                            if flags & 16:  # Bold
                                is_bold = True
                            if flags & 2:  # Italic
                                is_italic = True

                        if line_text.strip():
                            block_text_parts.append(line_text.strip())

                    text = " ".join(block_text_parts).strip()

                    if text:
                        # Suppress repeated headers/footers without dropping first occurrence
                        is_margin_region = bool(block_bbox and self._is_header_footer(block_bbox, page.rect))
                        is_header = False
                        is_footer = False
                        if is_margin_region and block_bbox:
                            page_mid_y = (page.rect.y0 + page.rect.y1) / 2
                            block_mid_y = (block_bbox[1] + block_bbox[3]) / 2
                            is_header = block_mid_y < page_mid_y
                            is_footer = not is_header

                            # Keep likely title material on page 1
                            if page_num == 0 and is_header and len(text.split()) > 3:
                                is_margin_region = False
                                is_header = False
                                is_footer = False

                        if is_margin_region:
                            margin_key = self._normalize_margin_text(text)
                            if margin_key and margin_key in seen_margin_texts:
                                continue
                            if margin_key:
                                seen_margin_texts.add(margin_key)

                        text_key = " ".join(text.lower().split())
                        if text_key and text_key == last_text_key and len(text_key) > 20:
                            continue
                        last_text_key = text_key

                        block_id = generate_block_id(self.block_counter)
                        self.block_counter += 1

                        # Calculate average font size
                        if font_sizes:
                            avg_font_size = sum(font_sizes) / len(font_sizes)

                        # Create text style
                        style = TextStyle(
                            bold=is_bold,
                            italic=is_italic,
                            font_size=(avg_font_size if avg_font_size > 0 else None),
                        )

                        text_block = Block(
                            block_id=block_id,
                            text=text,
                            index=self.block_counter * 100,
                            block_type=BlockType.UNKNOWN,
                            style=style,
                            page_number=page_num + 1,
                        )

                        if is_header:
                            text_block.metadata["is_header"] = True
                        if is_footer:
                            text_block.metadata["is_footer"] = True

                        if block_bbox:
                            text_block.metadata["bbox"] = [
                                float(block_bbox[0]),
                                float(block_bbox[1]),
                                float(block_bbox[2]),
                                float(block_bbox[3]),
                            ]
                            page_text_positions.append((text_block.index, float(block_bbox[1])))

                        # Detect potential headings using ADAPTIVE thresholds
                        # Logic:
                        # - H1: Significantly larger than body (e.g. > 1.6x)
                        # - H2: Moderately larger (e.g. > 1.3x)
                        # - H3: Slightly larger (> 1.1x) OR (Bold AND Same Size)

                        if avg_font_size >= h3_threshold or (is_bold and avg_font_size >= body_font_size):
                            text_block.metadata["potential_heading"] = True

                            if avg_font_size >= h1_threshold:
                                text_block.metadata["heading_level"] = 1
                            elif avg_font_size >= h2_threshold:
                                text_block.metadata["heading_level"] = 2
                            else:
                                text_block.metadata["heading_level"] = 3

                        text_block.metadata["font_size"] = avg_font_size
                        text_block.metadata["relative_size"] = (
                            avg_font_size / body_font_size if body_font_size > 0 else 1.0
                        )
                        blocks.append(text_block)

            # Assign robust table anchors using nearest preceding text block
            for t_info in sorted(page_tables, key=lambda item: item["y0"]):
                table_obj: Table = t_info["table"]
                y0 = t_info["y0"]
                if page_text_positions:
                    before = [idx for idx, by in page_text_positions if by <= y0]
                    if before:
                        table_obj.block_index = before[-1] + 1
                    else:
                        table_obj.block_index = max(0, page_text_positions[0][0] - 1)
                else:
                    table_obj.block_index = max(0, self.block_counter * 100 + 1)
                tables.append(table_obj)

            # 3. Extract Images
            # ------------------------------------------------
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = pdf_doc.extract_image(xref)
                    image_data = base_image.get("image")
                    image_ext = base_image.get("ext", "")
                    if not image_data:
                        continue

                    image_hash = hashlib.sha1(image_data, usedforsecurity=False).hexdigest()
                    if image_hash in seen_image_hashes:
                        continue
                    seen_image_hashes.add(image_hash)

                    # Map extension to ImageFormat
                    format_map = {
                        "png": ImageFormat.PNG,
                        "jpg": ImageFormat.JPEG,
                        "jpeg": ImageFormat.JPEG,
                        "gif": ImageFormat.GIF,
                        "bmp": ImageFormat.BMP,
                    }
                    image_format = format_map.get(image_ext.lower(), ImageFormat.UNKNOWN)

                    figure_id = generate_figure_id(self.figure_counter)
                    self.figure_counter += 1

                    figure = Figure(
                        figure_id=figure_id,
                        index=self.figure_counter - 1,
                        image_data=image_data,
                        image_format=image_format,
                    )
                    figure.metadata["page_number"] = page_num + 1

                    anchor_index = max(0, self.block_counter * 100)
                    try:
                        image_rects = page.get_image_rects(xref)
                    except Exception:
                        image_rects = []
                    if image_rects:
                        first_rect = image_rects[0]
                        figure.width = float(first_rect.width) if hasattr(first_rect, "width") else None
                        figure.height = float(first_rect.height) if hasattr(first_rect, "height") else None
                        if page_text_positions:
                            above = [idx for idx, y in page_text_positions if y <= float(first_rect.y0)]
                            anchor_index = above[-1] if above else page_text_positions[0][0]
                        figure.metadata["bbox"] = [
                            float(first_rect.x0),
                            float(first_rect.y0),
                            float(first_rect.x1),
                            float(first_rect.y1),
                        ]

                    figure.metadata["block_index"] = anchor_index
                    figures.append(figure)
                except Exception as exc:
                    logger.warning("Failed to extract image on page %d (img %d): %s", page_num + 1, img_index, exc)

            # Fallback path for image blocks not exposed by get_images()
            if not image_list:
                for raw_block in text_dict.get("blocks", []):
                    if raw_block.get("type") != 1:
                        continue
                    try:
                        image_data = raw_block.get("image")
                        if not isinstance(image_data, (bytes, bytearray)):
                            continue
                        image_hash = hashlib.sha1(image_data, usedforsecurity=False).hexdigest()
                        if image_hash in seen_image_hashes:
                            continue
                        seen_image_hashes.add(image_hash)

                        image_ext = str(raw_block.get("ext", "png")).lower()
                        format_map = {
                            "png": ImageFormat.PNG,
                            "jpg": ImageFormat.JPEG,
                            "jpeg": ImageFormat.JPEG,
                            "gif": ImageFormat.GIF,
                            "bmp": ImageFormat.BMP,
                        }
                        figure = Figure(
                            figure_id=generate_figure_id(self.figure_counter),
                            index=self.figure_counter,
                            image_data=bytes(image_data),
                            image_format=format_map.get(image_ext, ImageFormat.UNKNOWN),
                            width=float(raw_block.get("width", 0) or 0) or None,
                            height=float(raw_block.get("height", 0) or 0) or None,
                        )
                        self.figure_counter += 1
                        figure.metadata["page_number"] = page_num + 1
                        figure.metadata["block_index"] = max(0, self.block_counter * 100)
                        if raw_block.get("bbox"):
                            bbox = raw_block["bbox"]
                            figure.metadata["bbox"] = [
                                float(bbox[0]),
                                float(bbox[1]),
                                float(bbox[2]),
                                float(bbox[3]),
                            ]
                        figures.append(figure)
                    except Exception as exc:
                        logger.warning("Failed to parse image block on page %d: %s", page_num + 1, exc)

        return blocks, figures, tables
