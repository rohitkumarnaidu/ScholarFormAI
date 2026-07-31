# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
OCR Engine — Surya OCR for scanned academic PDF processing.

Provides three capabilities:
  1. Text extraction (OCR) for scanned / image-based PDFs
  2. Layout analysis (headers, figures, tables, text regions)
  3. Reading order detection for multi-column academic papers

Falls back gracefully if Surya is not installed.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from app.utils.singleton import get_or_create_catching

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Optional imports
# --------------------------------------------------------------------------- #
SURYA_AVAILABLE = False
_load_error: Optional[str] = None

try:
    from surya.ocr import run_ocr
    from surya.detection import batch_text_detection
    from surya.layout import batch_layout_detection
    from surya.ordering import batch_ordering
    from surya.model.detection.model import load_model as load_det_model
    from surya.model.detection.model import load_processor as load_det_processor
    from surya.model.recognition.model import load_model as load_rec_model
    from surya.model.recognition.processor import load_processor as load_rec_processor
    from surya.model.ordering.model import load_model as load_order_model
    from surya.model.ordering.processor import load_processor as load_order_processor

    SURYA_AVAILABLE = True
except ImportError as exc:
    _load_error = str(exc)
    logger.info(
        "Surya OCR not installed (%s). Install with: pip install surya-ocr",
        exc,
    )


class OCREngine:
    """
    OCR + Layout + Reading Order engine powered by Surya.

    All models are lazy-loaded on first use and cached in ModelStore.
    """

    def __init__(self):
        if not SURYA_AVAILABLE:
            raise ImportError(f"Surya OCR unavailable: {_load_error}. Install with: pip install surya-ocr")
        # Model state (lazy)
        self._det_model = None
        self._det_processor = None
        self._rec_model = None
        self._rec_processor = None
        self._order_model = None
        self._order_processor = None
        self._loaded_det = False
        self._loaded_rec = False
        self._loaded_order = False

    # ------------------------------------------------------------------ #
    #  Lazy model loading
    # ------------------------------------------------------------------ #
    def _ensure_detection_loaded(self):
        if self._loaded_det:
            return
        from app.services.model_store import model_store

        if model_store.is_loaded("surya_det_model"):
            self._det_model = model_store.get_model("surya_det_model")
            self._det_processor = model_store.get_model("surya_det_processor")
        else:
            logger.info("OCREngine: Loading Surya text detection model...")
            self._det_model = load_det_model()
            self._det_processor = load_det_processor()
            model_store.set_model("surya_det_model", self._det_model)
            model_store.set_model("surya_det_processor", self._det_processor)
            logger.info("OCREngine: Detection model loaded.")
        self._loaded_det = True

    def _ensure_recognition_loaded(self):
        if self._loaded_rec:
            return
        from app.services.model_store import model_store

        if model_store.is_loaded("surya_rec_model"):
            self._rec_model = model_store.get_model("surya_rec_model")
            self._rec_processor = model_store.get_model("surya_rec_processor")
        else:
            logger.info("OCREngine: Loading Surya text recognition model...")
            self._rec_model = load_rec_model()
            self._rec_processor = load_rec_processor()
            model_store.set_model("surya_rec_model", self._rec_model)
            model_store.set_model("surya_rec_processor", self._rec_processor)
            logger.info("OCREngine: Recognition model loaded.")
        self._loaded_rec = True

    def _ensure_ordering_loaded(self):
        if self._loaded_order:
            return
        from app.services.model_store import model_store

        if model_store.is_loaded("surya_order_model"):
            self._order_model = model_store.get_model("surya_order_model")
            self._order_processor = model_store.get_model("surya_order_processor")
        else:
            logger.info("OCREngine: Loading Surya reading-order model...")
            self._order_model = load_order_model()
            self._order_processor = load_order_processor()
            model_store.set_model("surya_order_model", self._order_model)
            model_store.set_model("surya_order_processor", self._order_processor)
            logger.info("OCREngine: Reading-order model loaded.")
        self._loaded_order = True

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def detect_text(
        self,
        images: List[Any],
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run OCR on a list of page images.

        Args:
            images: List of PIL Images (one per page).
            languages: Language codes (default: ["en"]).

        Returns:
            List of page results, each containing detected text lines with
            bounding boxes and confidence scores.
        """
        self._ensure_detection_loaded()
        self._ensure_recognition_loaded()

        langs = languages or ["en"]
        # Surya's run_ocr expects languages per image
        lang_list = [langs] * len(images)

        results = run_ocr(
            images,
            lang_list,
            self._det_model,
            self._det_processor,
            self._rec_model,
            self._rec_processor,
        )

        pages = []
        for page_result in results:
            lines = []
            for line in page_result.text_lines:
                lines.append(
                    {
                        "text": line.text,
                        "confidence": round(line.confidence, 4),
                        "bbox": line.bbox,
                    }
                )
            pages.append(
                {
                    "lines": lines,
                    "full_text": "\n".join(l["text"] for l in lines),
                }
            )

        return pages

    def detect_layout(self, images: List[Any]) -> List[List[Dict[str, Any]]]:
        """
        Detect page layout regions (headers, figures, tables, text blocks).

        Args:
            images: List of PIL Images.

        Returns:
            List of pages, each containing a list of layout regions with
            label, bbox, and confidence.
        """
        self._ensure_detection_loaded()

        # Surya layout detection
        det_results = batch_text_detection(images, self._det_model, self._det_processor)
        layout_results = batch_layout_detection(images, self._det_model, self._det_processor, det_results)

        pages = []
        for page_layout in layout_results:
            regions = []
            for region in page_layout.bboxes:
                regions.append(
                    {
                        "label": region.label,
                        "bbox": region.bbox,
                        "confidence": round(region.confidence, 4) if hasattr(region, "confidence") else None,
                    }
                )
            pages.append(regions)

        return pages

    def detect_reading_order(self, images: List[Any]) -> List[List[Dict[str, Any]]]:
        """
        Detect the correct reading order for multi-column pages.

        Args:
            images: List of PIL Images.

        Returns:
            List of pages, each containing ordered text regions.
        """
        self._ensure_detection_loaded()
        self._ensure_ordering_loaded()

        # Need text detections first
        det_results = batch_text_detection(images, self._det_model, self._det_processor)

        order_results = batch_ordering(images, det_results, self._order_model, self._order_processor)

        pages = []
        for page_order in order_results:
            ordered = []
            for item in page_order.bboxes:
                ordered.append(
                    {
                        "bbox": item.bbox,
                        "position": item.position,
                        "label": getattr(item, "label", "text"),
                    }
                )
            # Sort by reading-order position
            ordered.sort(key=lambda x: x.get("position", 0))
            pages.append(ordered)

        return pages

    def is_scanned_pdf(self, text_from_pymupdf: str, page_count: int) -> bool:
        """
        Heuristic: determine if a PDF is scanned (image-based) by checking
        how little text PyMuPDF extracted.

        Args:
            text_from_pymupdf: All text extracted by PyMuPDF.
            page_count: Number of pages in the PDF.

        Returns:
            True if the PDF appears to be scanned.
        """
        if page_count <= 0:
            return False
        chars_per_page = len(text_from_pymupdf.strip()) / max(page_count, 1)
        # If less than 50 characters per page on average, likely scanned
        return chars_per_page < 50


# --------------------------------------------------------------------------- #
#  Singleton
# --------------------------------------------------------------------------- #
_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine() -> Optional[OCREngine]:
    """Get or create an OCREngine instance. Returns None if Surya is unavailable."""
    global _ocr_engine
    _ocr_engine = get_or_create_catching(
        _ocr_engine,
        OCREngine,
        exceptions=(ImportError,),
    )
    return _ocr_engine
