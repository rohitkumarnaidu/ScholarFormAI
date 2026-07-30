# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import patch, MagicMock, ANY
import pytest


# ─── PdfOCR ────────────────────────────────────────────────────────────────────

class TestPdfOCR:
    def test_init_defaults(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        assert ocr.text_threshold == 300
        assert ocr.paddle_language == "en"

    def test_init_custom(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR(text_threshold=500, paddle_language="ch")
        assert ocr.text_threshold == 500
        assert ocr.paddle_language == "ch"

    def test_normalize_backends_default(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        backends = ocr._normalize_backends(None)
        assert "tesseract" in backends

    def test_normalize_backends_custom_order(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        backends = ocr._normalize_backends(["paddle", "tesseract"])
        assert backends[0] == "paddle" if "paddle" in backends else True

    def test_normalize_backends_dedup(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        backends = ocr._normalize_backends(["tesseract", "tesseract"])
        assert backends == ["tesseract"]

    def test_normalize_backends_unknown_ignored(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        backends = ocr._normalize_backends(["invalid", "tesseract"])
        assert backends == ["tesseract"]

    def test_normalize_backends_removes_unavailable_tesseract(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            backends = ocr._normalize_backends(["tesseract", "paddle"])
            assert "tesseract" not in backends

    def test_normalize_backends_removes_unavailable_paddle(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            backends = ocr._normalize_backends(["tesseract", "paddle"])
            assert "paddle" not in backends

    def test_combine_pages_empty(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._combine_pages([]) == ""

    def test_combine_pages_single(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._combine_pages(["hello"]) == "hello"

    def test_combine_pages_multiple(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._combine_pages(["page1", "page2"]) == "page1\n\npage2"

    def test_combine_pages_skips_empty(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._combine_pages(["a", "", "b"]) == "a\n\nb"

    def test_sanitize_text(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._sanitize_text("hello\nworld\tok") == "hello\nworld\tok"

    def test_sanitize_text_removes_nonprintable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._sanitize_text("abc\x00def\x01") == "abcdef"

    def test_sanitize_text_empty(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._sanitize_text("") == ""
        assert PdfOCR._sanitize_text(None) == ""

    def test_is_scanned_pdfminer_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", False):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            assert PdfOCR().is_scanned("/tmp/test.pdf") is False

    def test_is_scanned_extract_fails(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", side_effect=Exception("corrupt")),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            assert PdfOCR().is_scanned("/tmp/test.pdf") is False

    def test_is_scanned_true(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value="short"),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            assert PdfOCR(text_threshold=300).is_scanned("/tmp/test.pdf") is True

    def test_is_scanned_false(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value="A" * 500),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            assert PdfOCR(text_threshold=300).is_scanned("/tmp/test.pdf") is False

    def test_extract_text_pdf2image_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", False):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().extract_text("/tmp/test.pdf")

    def test_extract_text_no_backends_selected(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False),
            patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().extract_text("/tmp/test.pdf")

    def test_extract_text_convert_fails(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", side_effect=Exception("poppler missing")),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().extract_text("/tmp/test.pdf")

    def test_extract_text_no_images(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().extract_text("/tmp/test.pdf")

    def test_extract_text_tesseract_success(self):
        mock_image = MagicMock()
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[mock_image]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
        ):
            mock_ts.image_to_string.return_value = "Hello OCR"
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            text, backend = PdfOCR().extract_text("/tmp/test.pdf")
            assert "Hello OCR" in text
            assert backend == "tesseract"

    def test_extract_text_tesseract_all_pages_fail(self):
        mock_image = MagicMock()
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[mock_image]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
        ):
            mock_ts.image_to_string.side_effect = Exception("tess error")
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception) as exc:
                PdfOCR().extract_text("/tmp/test.pdf")
            assert "All OCR backends failed" in str(exc.value)

    def test_extract_text_tesseract_empty_text_falls_to_paddle(self):
        mock_image = MagicMock()
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[mock_image]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
            patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as mock_paddle_cls,
        ):
            mock_ts.image_to_string.return_value = ""
            mock_paddle = MagicMock()
            mock_paddle_cls.return_value = mock_paddle
            mock_paddle.ocr.return_value = [[[[0, 0, 0, 0], ("Paddle text", 0.9)]]]
            import numpy
            with patch("app.pipeline.ocr.pdf_ocr.np", wraps=numpy):
                text, backend = PdfOCR().extract_text("/tmp/test.pdf")
                assert "Paddle text" in text
                assert backend == "paddle"

    def test_ocr_tesseract_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            with pytest.raises(Exception):
                PdfOCR()._ocr_tesseract([MagicMock()])

    def test_ocr_tesseract_success(self):
        mock_image = MagicMock()
        with (
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
        ):
            mock_ts.image_to_string.side_effect = ["Page 1 text", "Page 2 text"]
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            result = PdfOCR()._ocr_tesseract([mock_image, mock_image])
            assert len(result) == 2

    def test_ocr_paddle_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR()._ocr_paddle([MagicMock()])

    def test_ocr_paddle_numpy_unavailable(self):
        with (
            patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False),
        ):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR()._ocr_paddle([MagicMock()])

    def test_convert_to_docx_docx_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", False):
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().convert_to_docx("/tmp/test.pdf", "/tmp/out.docx")

    def test_convert_to_docx_success(self):
        mock_doc = MagicMock()
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
            patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.Document", return_value=mock_doc),
        ):
            mock_ts.image_to_string.return_value = "OCR text"
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            text = PdfOCR().convert_to_docx("/tmp/test.pdf", "/tmp/out.docx")
            assert "OCR text" in text
            mock_doc.add_paragraph.assert_called_once()
            mock_doc.save.assert_called_once_with("/tmp/out.docx")

    def test_convert_to_docx_save_fails(self):
        mock_doc = MagicMock()
        mock_doc.save.side_effect = Exception("disk full")
        with (
            patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]),
            patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.pytesseract") as mock_ts,
            patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.Document", return_value=mock_doc),
        ):
            mock_ts.image_to_string.return_value = "OCR text"
            from app.pipeline.ocr.pdf_ocr import PdfOCR
            with pytest.raises(Exception):
                PdfOCR().convert_to_docx("/tmp/test.pdf", "/tmp/out.docx")
