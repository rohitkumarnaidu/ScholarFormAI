# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Docling Layout Analysis Client.

This module provides a client for IBM Docling library to extract advanced
layout information from PDF documents, including bounding boxes, font sizes,
and structural elements like headers/footers.

Docling excels at:
- Preserving document layout and reading order
- Detecting bounding boxes for all document elements
- Identifying tables, figures, headings, and paragraphs
- Extracting font information and styles
"""

from __future__ import annotations

import importlib.util
import logging
import warnings
from contextlib import contextmanager
from typing import Any

from app.config.settings import settings
from app.pipeline.safety import safe_function

logger = logging.getLogger(__name__)

_DOCLING_WARNING_FILTERS = (
    "This field is deprecated. Use `generate_page_images=True` and call `TableItem.get_image()` to extract table images from page images.*",
    "^deprecated$",
    "builtin type SwigPyPacked has no __module__ attribute",
    "builtin type SwigPyObject has no __module__ attribute",
    "builtin type swigvarlink has no __module__ attribute",
)

# Apply narrow global suppression for known third-party deprecation noise.
for _pattern in _DOCLING_WARNING_FILTERS:
    warnings.filterwarnings("ignore", message=_pattern, category=DeprecationWarning)


@contextmanager
def _suppress_docling_warnings():
    """Suppress known third-party deprecation noise from Docling/PyMuPDF stack."""
    with warnings.catch_warnings():
        for pattern in _DOCLING_WARNING_FILTERS:
            warnings.filterwarnings("ignore", message=pattern, category=DeprecationWarning)
        yield


def _docling_enabled() -> bool:
    if not getattr(settings, "USE_DOCLING_FALLBACK", False):
        return False
    return not settings.LOW_MEMORY_MODE


# Backward-compatible availability flag used by tests and external callers.
try:
    DOCLING_AVAILABLE = _docling_enabled() and importlib.util.find_spec("docling") is not None
except Exception:
    DOCLING_AVAILABLE = False


def _load_docling_converter():
    if not DOCLING_AVAILABLE:
        return None
    try:
        import os

        # Windows Symlink Fix: Disable warning and force copy
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        with _suppress_docling_warnings():
            from docling.document_converter import DocumentConverter
        return DocumentConverter
    except Exception as exc:
        logger.warning("Docling import failed: %s", exc)
        return None


class BoundingBox:
    """Represents a bounding box for a document element."""

    def __init__(self, x0: float, y0: float, x1: float, y1: float, page: int = 0):
        self.x0 = x0  # Left
        self.y0 = y0  # Top
        self.x1 = x1  # Right
        self.y1 = y1  # Bottom
        self.page = page

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center_y(self) -> float:
        """Vertical center position."""
        return (self.y0 + self.y1) / 2

    def to_dict(self) -> dict[str, float]:
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page": self.page,
            "width": self.width,
            "height": self.height,
        }


class LayoutElement:
    """Represents a layout element with bounding box and metadata."""

    def __init__(
        self,
        text: str,
        bbox: BoundingBox,
        element_type: str,
        font_size: float | None = None,
        is_bold: bool = False,
        is_italic: bool = False,
        confidence: float = 1.0,
    ):
        self.text = text
        self.bbox = bbox
        self.element_type = element_type  # title, paragraph, heading, table, figure, etc.
        self.font_size = font_size
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "type": self.element_type,
            "font_size": self.font_size,
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "confidence": self.confidence,
        }


class DoclingClient:
    """
    Client for IBM Docling library to perform advanced PDF layout analysis.

    Features:
    - Bounding box extraction for all elements
    - Font size and style detection
    - Header/footer identification
    - Table and figure detection
    - Reading order preservation
    """

    def __init__(self):
        """Initialize the Docling client."""
        self.converter = None
        self._available = False
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        
        self._initialized = True
        docling_converter = _load_docling_converter()
        if docling_converter is None:
            logger.warning("Docling not available - layout analysis will be limited")
            return

        try:
            # Initialize DocumentConverter with defaults
            with _suppress_docling_warnings():
                self.converter = docling_converter()
            self._available = True
            logger.info("Docling client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            self.converter = None
            self._available = False

    def is_available(self) -> bool:
        """Check if Docling is available and initialized."""
        self._ensure_initialized()
        return self._available and self.converter is not None

    @safe_function(
        fallback_value={
            "elements": [],
            "headers": [],
            "footers": [],
            "tables": [],
            "figures": [],
            "confidence": 0.0,
            "pages": 0,
        },
        error_message="DoclingClient.analyze_layout",
    )
    def analyze_layout(self, file_path: str) -> dict[str, Any]:
        """
        Analyze the layout of a PDF file using Docling.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dictionary containing layout information (elements, boxes, etc.)
        """
        if not self.is_available():
            logger.warning("Docling is not installed or failed to load.")
            return self._empty_layout()

        try:
            logger.info(f"Starting Docling layout analysis for: {file_path}")

            try:
                with _suppress_docling_warnings():
                    doc_converter = self.converter
                    if doc_converter is None:
                        logger.warning("Docling converter is unavailable during layout analysis.")
                        return self._empty_layout()
                    doc = doc_converter.convert(file_path).document

            except Exception as e:
                logger.error(f"Docling conversion failed: {e}")
                return self._empty_layout()

            # Extract layout data from the Docling document object
            elements = []

            # Iterate through all elements in the document
            # Note: Docling's object model might vary by version
            # We map main text items, headers, tables, etc.

            # Text items (Paragraphs, Headings, etc.)
            for item in doc.texts:
                # Extract bounding box
                bbox = None
                if item.prov and item.prov[0].bbox:
                    b = item.prov[0].bbox
                    # Normalize: Docling uses bottom-up/top-down depending on backend?
                    # Usually top-left origin for PDF analysis in this context
                    bbox = {"x0": b.l, "y0": b.t, "x1": b.r, "y1": b.b, "page": item.prov[0].page_no}

                elements.append(
                    {
                        "text": item.text,
                        "type": item.label,  # e.g., 'text', 'title', 'section_header'
                        "bbox": bbox,
                        "level": getattr(item, "level", 0),  # Headings structure
                    }
                )

            # Tables
            for table in doc.tables:
                if table.prov and table.prov[0].bbox:
                    b = table.prov[0].bbox
                    bbox = {"x0": b.l, "y0": b.t, "x1": b.r, "y1": b.b, "page": table.prov[0].page_no}
                    elements.append(
                        {
                            "type": "table",
                            "bbox": bbox,
                            "rows": len(table.data.grid),
                            "cols": len(table.data.grid[0]) if table.data.grid else 0,
                        }
                    )

            # Safe handling of num_pages which can be a method or property depending on version
            num_pages = 1
            if hasattr(doc, "num_pages"):
                np = doc.num_pages
                num_pages = np() if callable(np) else np

            result = {"elements": elements, "pages": num_pages}

            logger.info(f"Docling analysis complete. Found {len(elements)} elements.")
            return result

        except Exception as e:
            logger.error(f"Docling analysis failed: {e}")
            return self._empty_layout()

    def _extract_elements(self, document) -> list[LayoutElement]:
        """Extract layout elements from Docling document."""
        elements = []

        try:
            # Iterate through document items
            for item in document.iterate_items():
                # Get bounding box
                bbox_data = item.bbox if hasattr(item, "bbox") else None
                if not bbox_data:
                    continue

                bbox = BoundingBox(
                    x0=bbox_data.l,
                    y0=bbox_data.t,
                    x1=bbox_data.r,
                    y1=bbox_data.b,
                    page=bbox_data.page if hasattr(bbox_data, "page") else 0,
                )

                # Get text content
                text = item.text if hasattr(item, "text") else ""

                # Get element type (title, paragraph, heading, etc.)
                element_type = item.label if hasattr(item, "label") else "paragraph"

                # Get font information (if available)
                font_size = None
                is_bold = False
                is_italic = False

                if hasattr(item, "prov") and item.prov:
                    for prov in item.prov:
                        if hasattr(prov, "font_size"):
                            font_size = prov.font_size
                        if hasattr(prov, "font_weight") and prov.font_weight > 600:
                            is_bold = True
                        if hasattr(prov, "font_style") and "italic" in str(prov.font_style).lower():
                            is_italic = True

                # Create layout element
                element = LayoutElement(
                    text=text,
                    bbox=bbox,
                    element_type=element_type,
                    font_size=font_size,
                    is_bold=is_bold,
                    is_italic=is_italic,
                    confidence=0.9,  # Docling has high confidence
                )

                elements.append(element)

        except Exception as e:
            logger.error(f"Failed to extract elements: {e}")

        return elements

    def _detect_headers_footers(self, elements: list[LayoutElement]) -> tuple[list[LayoutElement], list[LayoutElement]]:
        """
        Detect headers and footers based on position.

        Headers: Top 10% of page
        Footers: Bottom 10% of page
        """
        headers = []
        footers = []

        if not elements:
            return headers, footers

        # Group elements by page
        pages: dict[int, list[LayoutElement]] = {}
        for elem in elements:
            page = elem.bbox.page
            if page not in pages:
                pages[page] = []
            pages[page].append(elem)

        # For each page, identify headers/footers
        for _page_num, page_elements in pages.items():
            if not page_elements:
                continue

            # Find page height (max y1)
            page_height = max(elem.bbox.y1 for elem in page_elements)

            # Header threshold: top 10%
            header_threshold = page_height * 0.1

            # Footer threshold: bottom 10%
            footer_threshold = page_height * 0.9

            for elem in page_elements:
                # Check if in header region
                if elem.bbox.y1 < header_threshold:
                    headers.append(elem)
                # Check if in footer region
                elif elem.bbox.y0 > footer_threshold:
                    footers.append(elem)

        return headers, footers

    def _extract_tables(self, document) -> list[dict[str, Any]]:
        """Extract table information."""
        tables = []

        try:
            for item in document.iterate_items():
                if hasattr(item, "label") and item.label == "table":
                    table_data = {
                        "text": item.text if hasattr(item, "text") else "",
                        "bbox": item.bbox.to_dict() if hasattr(item, "bbox") else None,
                        "rows": getattr(item, "num_rows", 0),
                        "cols": getattr(item, "num_cols", 0),
                    }
                    tables.append(table_data)
        except Exception as e:
            logger.error(f"Failed to extract tables: {e}")

        return tables

    def _extract_figures(self, document) -> list[dict[str, Any]]:
        """Extract figure information."""
        figures = []

        try:
            for item in document.iterate_items():
                if hasattr(item, "label") and item.label in ["figure", "picture"]:
                    figure_data = {
                        "text": item.text if hasattr(item, "text") else "",
                        "bbox": item.bbox.to_dict() if hasattr(item, "bbox") else None,
                        "caption": getattr(item, "caption", ""),
                    }
                    figures.append(figure_data)
        except Exception as e:
            logger.error(f"Failed to extract figures: {e}")

        return figures

    def _calculate_confidence(self, elements: list[LayoutElement]) -> float:
        """Calculate overall confidence score."""
        if not elements:
            return 0.0

        # Average confidence of all elements
        total_confidence = sum(elem.confidence for elem in elements)
        return total_confidence / len(elements)

    def _empty_layout(self) -> dict[str, Any]:
        """Return empty layout structure."""
        return {
            "elements": [],
            "headers": [],
            "footers": [],
            "tables": [],
            "figures": [],
            "confidence": 0.0,
            "pages": 0,
        }

    def find_title_with_logo_tolerance(
        self, elements: list[LayoutElement], logo_y_threshold: float = 150.0
    ) -> LayoutElement | None:
        """
        Find title element, accounting for logos at the top.

        Args:
            elements: List of layout elements
            logo_y_threshold: Y position below which to start looking for title

        Returns:
            Title element or None
        """
        # Filter elements below logo threshold
        candidate_elements = [elem for elem in elements if elem.bbox.y0 > logo_y_threshold and elem.text.strip()]

        if not candidate_elements:
            return None

        # Find element with largest font size
        title_element = max(
            candidate_elements,
            key=lambda e: (e.font_size or 0, -e.bbox.y0),  # Largest font, highest position
        )

        return title_element
