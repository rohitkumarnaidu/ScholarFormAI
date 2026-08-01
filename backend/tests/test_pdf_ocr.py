from unittest.mock import MagicMock, patch

import pytest


class TestConstructor:
    def test_default_values(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        assert ocr.text_threshold == 300
        assert ocr.paddle_language == "en"

    def test_custom_values(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR(text_threshold=100, paddle_language="zh")
        assert ocr.text_threshold == 100
        assert ocr.paddle_language == "zh"


class TestIsScanned:
    @patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", False)
    def test_returns_false_when_pdfminer_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        assert not ocr.is_scanned("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text")
    def test_returns_true_when_text_below_threshold(self, mock_extract):
        mock_extract.return_value = "short"
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR(text_threshold=300)
        assert ocr.is_scanned("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text")
    def test_returns_false_when_text_above_threshold(self, mock_extract):
        mock_extract.return_value = "word " * 200
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR(text_threshold=300)
        assert not ocr.is_scanned("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text")
    def test_handle_exception(self, mock_extract):
        mock_extract.side_effect = Exception("parse error")
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        assert not ocr.is_scanned("test.pdf")


class TestNormalizeBackends:
    def test_default_backends(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        result = ocr._normalize_backends(None)
        assert isinstance(result, list)

    def test_custom_order(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    result = ocr._normalize_backends(["paddle", "tesseract"])
                    assert result == ["paddle", "tesseract"]

    def test_removes_duplicates(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            result = ocr._normalize_backends(["tesseract", "tesseract"])
            assert result == ["tesseract"]

    def test_filters_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    result = ocr._normalize_backends(["tesseract", "paddle"])
                    assert result == ["paddle"]

    def test_skips_unsupported_backend(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        result = ocr._normalize_backends(["invalid"])
        assert result == []


class TestExtractText:
    @patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", False)
    def test_raises_when_pdf2image_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
        ocr = PdfOCR()
        with pytest.raises(OCRError, match="pdf2image is unavailable"):
            ocr.extract_text("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.convert_from_path")
    @patch("app.pipeline.ocr.pdf_ocr.PdfOCR._normalize_backends")
    def test_raises_when_no_backends(self, mock_norm, mock_convert):
        mock_norm.return_value = []
        mock_convert.return_value = [MagicMock()]
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
        ocr = PdfOCR()
        with pytest.raises(OCRError, match="No OCR backends"):
            ocr.extract_text("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.convert_from_path")
    def test_raises_when_convert_fails(self, mock_convert):
        mock_convert.side_effect = Exception("Poppler missing")
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
        ocr = PdfOCR()
        with pytest.raises(OCRError, match="Failed to convert"):
            ocr.extract_text("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.convert_from_path")
    def test_raises_when_no_pages(self, mock_convert):
        mock_convert.return_value = []
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
        ocr = PdfOCR()
        with pytest.raises(OCRError, match="no renderable pages"):
            ocr.extract_text("test.pdf")

    @patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.convert_from_path")
    @patch("app.pipeline.ocr.pdf_ocr.PdfOCR._ocr_tesseract")
    @patch("app.pipeline.ocr.pdf_ocr.PdfOCR._normalize_backends")
    def test_tesseract_success(self, mock_norm, mock_tess, mock_convert):
        mock_norm.return_value = ["tesseract"]
        mock_tess.return_value = ["Page 1 text"]
        mock_convert.return_value = [MagicMock()]
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        text, backend = ocr.extract_text("test.pdf")
        assert "Page 1 text" in text
        assert backend == "tesseract"


class TestConvertToDocx:
    @patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", False)
    def test_raises_when_docx_unavailable(self):
        from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR
        ocr = PdfOCR()
        with pytest.raises(OCRError, match="python-docx is unavailable"):
            ocr.convert_to_docx("test.pdf", "out.docx")

    @patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True)
    @patch("app.pipeline.ocr.pdf_ocr.Document")
    @patch("app.pipeline.ocr.pdf_ocr.PdfOCR.extract_text")
    def test_creates_docx(self, mock_extract, mock_docx_cls):
        mock_extract.return_value = ("Hello", "tesseract")
        mock_doc = MagicMock()
        mock_docx_cls.return_value = mock_doc
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        ocr = PdfOCR()
        result = ocr.convert_to_docx("test.pdf", "out.docx")
        assert result == "Hello"
        mock_doc.add_paragraph.assert_called_once()
        mock_doc.save.assert_called_once_with("out.docx")


class TestCombinePages:
    def test_combines_pages(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        result = PdfOCR._combine_pages(["Page 1", "Page 2"])
        assert result == "Page 1\n\nPage 2"

    def test_skips_empty(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        result = PdfOCR._combine_pages(["Page 1", "", "Page 3"])
        assert result == "Page 1\n\nPage 3"

    def test_returns_empty_for_all_empty(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        result = PdfOCR._combine_pages(["", None, ""])
        assert result == ""


class TestSanitizeText:
    def test_removes_non_printable(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        result = PdfOCR._sanitize_text("Hello\x00World\x01")
        assert result == "HelloWorld"

    def test_preserves_newlines(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        result = PdfOCR._sanitize_text("Line1\nLine2\r\nLine3")
        assert "Line1\nLine2" in result

    def test_handles_none(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert PdfOCR._sanitize_text(None) == ""


class TestOCRError:
    def test_is_exception(self):
        from app.pipeline.ocr.pdf_ocr import OCRError
        assert issubclass(OCRError, Exception)


class TestSupportedBackends:
    def test_has_tesseract_and_paddle(self):
        from app.pipeline.ocr.pdf_ocr import PdfOCR
        assert {"tesseract", "paddle"} == PdfOCR.SUPPORTED_BACKENDS
