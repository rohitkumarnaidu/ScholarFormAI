# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestPdfOCR:
    def test_init_defaults(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        ocr = PdfOCR()
        assert ocr.text_threshold == 300
        assert ocr.paddle_language == "en"

    def test_init_custom(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        ocr = PdfOCR(text_threshold=500, paddle_language="zh")
        assert ocr.text_threshold == 500
        assert ocr.paddle_language == "zh"

    def test_is_scanned_pdfminer_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", False):
            ocr = PdfOCR()
            result = ocr.is_scanned("/fake.pdf")
            assert result is False

    def test_is_scanned_below_threshold(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value="short text"):
                ocr = PdfOCR(text_threshold=300)
                result = ocr.is_scanned("/fake.pdf")
                assert result is True

    def test_is_scanned_above_threshold(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value="A" * 500):
                ocr = PdfOCR(text_threshold=300)
                result = ocr.is_scanned("/fake.pdf")
                assert result is False

    def test_is_scanned_exception(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", side_effect=Exception("PDF error")):
                ocr = PdfOCR()
                result = ocr.is_scanned("/bad.pdf")
                assert result is False

    def test_is_scanned_none_text(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value=None):
                ocr = PdfOCR()
                result = ocr.is_scanned("/none.pdf")
                assert result is True

    def test_extract_text_pdf2image_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="pdf2image is unavailable"):
                ocr.extract_text("/fake.pdf")

    def test_extract_text_no_backends(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
                with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="No OCR backends"):
                        ocr.extract_text("/fake.pdf", backends=["tesseract"])

    def test_extract_text_convert_failure(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path", side_effect=Exception("Poppler missing")):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="Failed to convert"):
                        ocr.extract_text("/fake.pdf")

    def test_extract_text_no_images(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[]):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="no renderable pages"):
                        ocr.extract_text("/fake.pdf")

    def test_extract_text_tesseract_success(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        mock_tess = MagicMock()
        mock_tess.image_to_string.return_value = "Hello world"
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.pytesseract", mock_tess):
                    with patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]):
                        ocr = PdfOCR()
                        text, backend = ocr.extract_text("/fake.pdf")
                        assert "Hello" in text
                        assert backend == "tesseract"

    def test_extract_text_tesseract_empty_fallback(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        mock_tess = MagicMock()
        mock_tess.image_to_string.return_value = ""
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                    with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                        with patch("app.pipeline.ocr.pdf_ocr.pytesseract", mock_tess):
                            with patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]):
                                ocr = PdfOCR()
                                with pytest.raises(OCRError, match="All OCR backends failed"):
                                    ocr.extract_text("/fake.pdf", backends=["tesseract"])

    def test_extract_text_tesseract_exception(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        mock_tess = MagicMock()
        mock_tess.image_to_string.side_effect = Exception("Tesseract error")
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.pytesseract", mock_tess):
                    with patch("app.pipeline.ocr.pdf_ocr.convert_from_path", return_value=[MagicMock()]):
                        ocr = PdfOCR()
                        with pytest.raises(OCRError, match="All OCR backends failed"):
                            ocr.extract_text("/fake.pdf", backends=["tesseract"])

    def test_normalize_backends_default(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(None)
                    assert "tesseract" in result

    def test_normalize_backends_custom_order(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(["paddle", "tesseract"])
                    assert result[0] == "paddle"

    def test_normalize_backends_deduplicates(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            ocr = PdfOCR()
            result = ocr._normalize_backends(["tesseract", "tesseract"])
            assert result == ["tesseract"]

    def test_normalize_backends_unsupported_skipped(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        ocr = PdfOCR()
        result = ocr._normalize_backends(["unsupported"])
        assert result == []

    def test_normalize_backends_tesseract_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            ocr = PdfOCR()
            result = ocr._normalize_backends(["tesseract"])
            assert "tesseract" not in result

    def test_normalize_backends_paddle_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            ocr = PdfOCR()
            result = ocr._normalize_backends(["paddle"])
            assert "paddle" not in result

    def test_combine_pages(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        result = PdfOCR._combine_pages(["Page 1", "Page 2", ""])
        assert result == "Page 1\n\nPage 2"

    def test_sanitize_text(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        result = PdfOCR._sanitize_text("Hello\nWorld\tTest\x00Bad")
        assert "\x00" not in result
        assert "Hello" in result

    def test_ocr_tesseract_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="Tesseract backend unavailable"):
                ocr._ocr_tesseract([MagicMock()])

    def test_ocr_tesseract_success(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        mock_tess = MagicMock()
        mock_tess.image_to_string.return_value = "Hello"
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pytesseract", mock_tess):
                ocr = PdfOCR()
                pages = ocr._ocr_tesseract([MagicMock()])
                assert pages == ["Hello"]

    def test_ocr_tesseract_page_exception(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        mock_tess = MagicMock()
        mock_tess.image_to_string.side_effect = Exception("OCR error on page")
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pytesseract", mock_tess):
                ocr = PdfOCR()
                pages = ocr._ocr_tesseract([MagicMock()])
                assert pages == [""]

    def test_ocr_paddle_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="PaddleOCR backend unavailable"):
                ocr._ocr_paddle([MagicMock()])

    def test_ocr_paddle_numpy_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with (
            patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True),
            patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", MagicMock()),
            patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False),
        ):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="NumPy"):
                ocr._ocr_paddle([MagicMock()])

    def test_ocr_paddle_success(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        mock_np = MagicMock()
        mock_np.array.return_value = MagicMock()
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np", mock_np):
                    mock_paddle = MagicMock()
                    mock_paddle.ocr.return_value = [[[[0.1, 0.2, 0.3, 0.4], ("Hello", 0.95)]]]
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", return_value=mock_paddle):
                        ocr = PdfOCR()
                        pages = ocr._ocr_paddle([MagicMock()])
                        assert len(pages) == 1

    def test_ocr_paddle_page_exception(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        mock_np = MagicMock()
        mock_np.array.return_value = MagicMock()
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np", mock_np):
                    mock_paddle = MagicMock()
                    mock_paddle.ocr.side_effect = Exception("Paddle error on page")
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", return_value=mock_paddle):
                        ocr = PdfOCR()
                        pages = ocr._ocr_paddle([MagicMock()])
                        assert pages == [""]

    def test_convert_to_docx_docx_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="python-docx is unavailable"):
                ocr.convert_to_docx("/fake.pdf", "/out.docx")

    def test_convert_to_docx_success(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True):
            with patch.object(PdfOCR, "extract_text", return_value=("Hello world", "tesseract")):
                mock_doc = MagicMock()
                with patch("app.pipeline.ocr.pdf_ocr.Document", return_value=mock_doc):
                    ocr = PdfOCR()
                    text = ocr.convert_to_docx("/fake.pdf", "/out.docx")
                    assert text == "Hello world"
                    mock_doc.save.assert_called_with("/out.docx")

    def test_convert_to_docx_save_failure(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True):
            with patch.object(PdfOCR, "extract_text", return_value=("Hello", "tesseract")):
                mock_doc = MagicMock()
                mock_doc.save.side_effect = Exception("Save failed")
                with patch("app.pipeline.ocr.pdf_ocr.Document", return_value=mock_doc):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="Failed to save OCR DOCX"):
                        ocr.convert_to_docx("/fake.pdf", "/out.docx")

    def test_ocrexception(self):
        from app.pipeline.ocr.pdf_ocr import OCRError

        exc = OCRError("test error")
        assert isinstance(exc, Exception)
        assert "test error" in str(exc)
