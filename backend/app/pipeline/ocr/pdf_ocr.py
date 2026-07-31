# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""PDF OCR module with fallback-first backend chain support."""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

logger = logging.getLogger(__name__)

try:
    from pdfminer.high_level import extract_text as pdf_extract_text

    PDFMINER_AVAILABLE = True
except Exception:
    pdf_extract_text = None  # type: ignore[assignment]
    PDFMINER_AVAILABLE = False

try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except Exception:
    convert_from_path = None  # type: ignore[assignment]
    PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None  # type: ignore[assignment]
    TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR

    PADDLE_AVAILABLE = True
except Exception:
    PaddleOCR = None  # type: ignore[assignment]
    PADDLE_AVAILABLE = False

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except Exception:
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

try:
    from docx import Document

    DOCX_AVAILABLE = True
except Exception:
    Document = None  # type: ignore[assignment]
    DOCX_AVAILABLE = False


class OCRError(Exception):
    """Raised when OCR processing fails and no fallback backend can recover."""


class PdfOCR:
    """OCR handler for scanned PDFs with backend fallback chain."""

    SUPPORTED_BACKENDS = {"tesseract", "paddle"}

    def __init__(self, text_threshold: int = 300, paddle_language: str = "en") -> None:
        self.text_threshold = text_threshold
        self.paddle_language = paddle_language

    def is_scanned(self, pdf_path: str) -> bool:
        """
        Heuristic scanned detection using extractable PDF text.
        Returns False if detector dependencies are unavailable.
        """
        if not PDFMINER_AVAILABLE or pdf_extract_text is None:
            logger.debug("PdfOCR.is_scanned skipped: pdfminer not available.")
            return False

        try:
            text = pdf_extract_text(pdf_path)
            clean_text = "".join((text or "").split())
            return len(clean_text) < self.text_threshold
        except Exception as exc:
            logger.warning("PdfOCR.is_scanned failed for '%s': %s", pdf_path, exc)
            return False

    def extract_text(self, pdf_path: str, backends: Sequence[str] | None = None) -> Tuple[str, str]:
        """
        Extract text from a scanned PDF using backend fallback order.

        Args:
            pdf_path: PDF file path.
            backends: Ordered list of backends (subset of {'tesseract','paddle'}).

        Returns:
            Tuple: (combined_text, backend_used)
        """
        if not PDF2IMAGE_AVAILABLE or convert_from_path is None:
            raise OCRError("pdf2image is unavailable. Install pdf2image + Poppler for OCR workflows.")

        selected_backends = self._normalize_backends(backends)
        if not selected_backends:
            raise OCRError("No OCR backends selected. Expected one of: tesseract, paddle.")

        try:
            images = convert_from_path(pdf_path)
        except Exception as exc:
            raise OCRError(f"Failed to convert PDF to images (Poppler missing?): {exc}") from exc

        if not images:
            raise OCRError("PDF contains no renderable pages for OCR.")

        failures: List[str] = []
        for backend in selected_backends:
            try:
                if backend == "tesseract":
                    page_text = self._ocr_tesseract(images)
                elif backend == "paddle":
                    page_text = self._ocr_paddle(images)
                else:
                    continue

                combined = self._combine_pages(page_text)
                if combined.strip():
                    logger.info("PdfOCR extracted text using backend=%s", backend)
                    return combined, backend
                failures.append(f"{backend}: no text")
            except Exception as exc:
                logger.warning("PdfOCR backend '%s' failed: %s", backend, exc)
                failures.append(f"{backend}: {exc}")

        raise OCRError(f"All OCR backends failed: {' | '.join(failures)}")

    def convert_to_docx(
        self,
        pdf_path: str,
        output_path: str,
        backends: Sequence[str] | None = None,
    ) -> str:
        """Extract OCR text and write it into a DOCX file."""
        if not DOCX_AVAILABLE or Document is None:
            raise OCRError("python-docx is unavailable. Install python-docx to export OCR output.")

        text, backend_used = self.extract_text(pdf_path, backends=backends)
        try:
            document = Document()
            document.add_paragraph(self._sanitize_text(text))
            document.save(output_path)
            logger.info("PdfOCR wrote DOCX via backend=%s to %s", backend_used, output_path)
            return text
        except Exception as exc:
            raise OCRError(f"Failed to save OCR DOCX: {exc}") from exc

    def _normalize_backends(self, backends: Sequence[str] | None) -> List[str]:
        ordered = [str(name).strip().lower() for name in (backends or ["tesseract", "paddle"])]
        cleaned: List[str] = []
        for backend in ordered:
            if backend not in self.SUPPORTED_BACKENDS:
                continue
            if backend in cleaned:
                continue
            cleaned.append(backend)

        # Remove unavailable backends but preserve order.
        available: List[str] = []
        for backend in cleaned:
            if backend == "tesseract" and not TESSERACT_AVAILABLE:
                continue
            if backend == "paddle" and (not PADDLE_AVAILABLE or not NUMPY_AVAILABLE):
                continue
            available.append(backend)
        return available

    @staticmethod
    def _combine_pages(page_text: Sequence[str]) -> str:
        return "\n\n".join((entry or "").strip() for entry in page_text if (entry or "").strip())

    @staticmethod
    def _sanitize_text(text: str) -> str:
        return "".join(ch for ch in (text or "") if ch.isprintable() or ch in "\n\r\t")

    def _ocr_tesseract(self, images: Sequence[object]) -> List[str]:
        if not TESSERACT_AVAILABLE or pytesseract is None:
            raise OCRError("Tesseract backend unavailable (install pytesseract + binary).")

        page_text: List[str] = []
        for index, image in enumerate(images):
            try:
                page_text.append(pytesseract.image_to_string(image) or "")
            except Exception as exc:
                logger.warning("Tesseract OCR failed on page %d: %s", index + 1, exc)
                page_text.append("")
        return page_text

    def _ocr_paddle(self, images: Sequence[object]) -> List[str]:
        if not PADDLE_AVAILABLE or PaddleOCR is None:
            raise OCRError("PaddleOCR backend unavailable (install paddleocr).")
        if not NUMPY_AVAILABLE or np is None:
            raise OCRError("NumPy is required for PaddleOCR backend.")

        ocr = PaddleOCR(use_angle_cls=True, lang=self.paddle_language, show_log=False)
        page_text: List[str] = []

        for index, image in enumerate(images):
            try:
                image_np = np.array(image)
                if image_np.ndim == 3 and image_np.shape[2] == 3:
                    image_np = image_np[:, :, ::-1]  # RGB -> BGR

                result = ocr.ocr(image_np, cls=True)
                lines: List[str] = []

                # paddleocr may return: [ [ [bbox, (text, score)], ... ] ]
                page_candidates = []
                if isinstance(result, list) and result:
                    if isinstance(result[0], list):
                        page_candidates = result[0]
                    else:
                        page_candidates = result

                for entry in page_candidates:
                    if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                        continue
                    raw_text = entry[1][0] if isinstance(entry[1], (list, tuple)) and entry[1] else ""
                    text = str(raw_text or "").strip()
                    if text:
                        lines.append(text)

                page_text.append("\n".join(lines))
            except Exception as exc:
                logger.warning("PaddleOCR failed on page %d: %s", index + 1, exc)
                page_text.append("")

        return page_text
