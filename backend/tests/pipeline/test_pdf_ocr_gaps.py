# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Gap-filling tests for PdfOCR to reach 100% line coverage.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.ocr.pdf_ocr import OCRError, PdfOCR

# ===================================================================
# Module-level import error paths (lines 16-18, 23-25, 30-32, 37-39, 44-46, 51-53)
# ===================================================================

class TestModuleImportPaths:
    """Test behavior when import dependencies are unavailable."""

    def test_pdfminer_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", False):
            ocr = PdfOCR()
            assert ocr.is_scanned("test.pdf") is False

    def test_pdf2image_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="pdf2image"):
                ocr.extract_text("test.pdf")

    def test_tesseract_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="Tesseract"):
                ocr._ocr_tesseract(["img1"])

    def test_paddleocr_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="PaddleOCR"):
                ocr._ocr_paddle(["img1"])

    def test_numpy_unavailable_for_paddle(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", MagicMock()):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="NumPy"):
                        ocr._ocr_paddle(["img1"])

    def test_docx_unavailable(self):
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="python-docx"):
                ocr.convert_to_docx("in.pdf", "out.docx")


# ===================================================================
# OCRError (basic exception test)
# ===================================================================

class TestOCRErrorGaps:

    def test_is_exception(self):
        assert issubclass(OCRError, Exception)

    def test_can_be_raised_with_message(self):
        with pytest.raises(OCRError, match="test error"):
            raise OCRError("test error")


# ===================================================================
# PdfOCR.__init__ (lines 66-67)
# ===================================================================

class TestPdfOCRInitGaps:

    def test_defaults(self):
        ocr = PdfOCR()
        assert ocr.text_threshold == 300
        assert ocr.paddle_language == "en"

    def test_custom_values(self):
        ocr = PdfOCR(text_threshold=500, paddle_language="zh")
        assert ocr.text_threshold == 500
        assert ocr.paddle_language == "zh"

    def test_supported_backends_set(self):
        assert {"tesseract", "paddle"} == PdfOCR.SUPPORTED_BACKENDS


# ===================================================================
# is_scanned — full branch coverage (lines 74-84)
# ===================================================================

class TestIsScannedGaps:

    def test_pdfminer_unavailable_returns_false(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", False):
            ocr = PdfOCR()
            assert ocr.is_scanned("test.pdf") is False

    def test_below_threshold_returns_true(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value="short"):
                ocr = PdfOCR(text_threshold=100)
                assert ocr.is_scanned("test.pdf") is True

    def test_above_threshold_returns_false(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text",
                       return_value="a" * 500):
                ocr = PdfOCR(text_threshold=100)
                assert ocr.is_scanned("test.pdf") is False

    def test_extraction_exception_logs_and_returns_false(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text",
                       side_effect=RuntimeError("no pdf")):
                ocr = PdfOCR()
                assert ocr.is_scanned("bad.pdf") is False

    def test_none_text_returns_true(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text",
                       return_value=None):
                ocr = PdfOCR(text_threshold=100)
                assert ocr.is_scanned("empty.pdf") is True

    def test_empty_text_returns_true(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDFMINER_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pdf_extract_text", return_value=""):
                ocr = PdfOCR(text_threshold=100)
                assert ocr.is_scanned("empty.pdf") is True


# ===================================================================
# extract_text — full branch coverage (lines 97-131)
# ===================================================================

class TestExtractTextGaps:

    def test_pdf2image_unavailable_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="pdf2image"):
                ocr.extract_text("test.pdf")

    def test_no_backends_selected_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends", return_value=[]):
                with pytest.raises(OCRError, match="No OCR backends"):
                    ocr.extract_text("test.pdf")

    def test_convert_from_path_fails_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends", return_value=["tesseract"]):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                           side_effect=RuntimeError("poppler missing")):
                    with pytest.raises(OCRError, match="Poppler"):
                        ocr.extract_text("test.pdf")

    def test_no_images_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends", return_value=["tesseract"]):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                           return_value=[]):
                    with pytest.raises(OCRError, match="no renderable"):
                        ocr.extract_text("test.pdf")

    def test_tesseract_success(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            images = ["img1", "img2"]
            with patch.object(ocr, "_normalize_backends", return_value=["tesseract"]):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                           return_value=images):
                    with patch.object(ocr, "_ocr_tesseract",
                                      return_value=["page1", "page2"]):
                        with patch.object(ocr, "_combine_pages",
                                          return_value="page1\n\npage2"):
                            text, backend = ocr.extract_text("test.pdf")
                            assert backend == "tesseract"
                            assert text == "page1\n\npage2"

    def test_fallback_to_next_backend(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            images = ["img1"]
            with patch.object(ocr, "_normalize_backends",
                              return_value=["tesseract", "paddle"]), patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                       return_value=images), patch.object(ocr, "_ocr_tesseract",
                              return_value=[""]), patch.object(ocr, "_ocr_paddle",
                              return_value=["text"]), patch.object(ocr, "_combine_pages",
                              side_effect=["", "text"]):
                text, backend = ocr.extract_text("test.pdf")
                assert backend == "paddle"

    def test_all_backends_fail_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends",
                              return_value=["tesseract", "paddle"]), patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                       return_value=["img1"]), patch.object(ocr, "_ocr_tesseract",
                              side_effect=OCRError("tess crash")), patch.object(ocr, "_ocr_paddle",
                              side_effect=OCRError("paddle crash")):
                with pytest.raises(OCRError, match="All OCR backends failed"):
                    ocr.extract_text("test.pdf")

    def test_combined_empty_falls_through(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends",
                              return_value=["tesseract", "paddle"]), patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                       return_value=["img1"]), patch.object(ocr, "_ocr_tesseract",
                              return_value=["   "]), patch.object(ocr, "_ocr_paddle",
                              return_value=["real text"]), patch.object(ocr, "_combine_pages",
                              side_effect=["", "real text"]):
                text, backend = ocr.extract_text("test.pdf")
                assert backend == "paddle"
                assert text == "real text"

    def test_unknown_backend_skipped(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends",
                              return_value=["unknown_backend", "tesseract"]):
                with patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                           return_value=["img1"]):
                    with patch.object(ocr, "_ocr_tesseract",
                                      return_value=["page1"]):
                        with patch.object(ocr, "_combine_pages",
                                          return_value="page1"):
                            text, backend = ocr.extract_text("test.pdf")
                            assert backend == "tesseract"

    def test_backend_exception_caught(self):
        with patch("app.pipeline.ocr.pdf_ocr.PDF2IMAGE_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "_normalize_backends",
                              return_value=["tesseract", "paddle"]), patch("app.pipeline.ocr.pdf_ocr.convert_from_path",
                       return_value=["img1"]), patch.object(ocr, "_ocr_tesseract",
                              side_effect=OCRError("tess fail")), patch.object(ocr, "_ocr_paddle",
                              return_value=["text"]):
                text, backend = ocr.extract_text("test.pdf")
                assert backend == "paddle"
                assert text == "text"


# ===================================================================
# convert_to_docx — full branch coverage (lines 140-151)
# ===================================================================

class TestConvertToDocxGaps:

    def test_docx_unavailable_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="python-docx"):
                ocr.convert_to_docx("in.pdf", "out.docx")

    def test_success(self):
        mock_doc = MagicMock()
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True), patch("app.pipeline.ocr.pdf_ocr.Document",
                   return_value=mock_doc):
            ocr = PdfOCR()
            with patch.object(ocr, "extract_text",
                              return_value=("hello world", "tesseract")):
                text = ocr.convert_to_docx("in.pdf", "out.docx")
                assert text == "hello world"
                mock_doc.add_paragraph.assert_called_once()
                mock_doc.save.assert_called_once_with("out.docx")

    def test_extract_text_failure_propagates(self):
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True):
            ocr = PdfOCR()
            with patch.object(ocr, "extract_text",
                              side_effect=OCRError("no text")), pytest.raises(OCRError, match="no text"):
                ocr.convert_to_docx("in.pdf", "out.docx")

    def test_save_failure_raises(self):
        mock_doc = MagicMock()
        mock_doc.save.side_effect = PermissionError("denied")
        with patch("app.pipeline.ocr.pdf_ocr.DOCX_AVAILABLE", True), patch("app.pipeline.ocr.pdf_ocr.Document",
                   return_value=mock_doc):
            ocr = PdfOCR()
            with patch.object(ocr, "extract_text",
                              return_value=("text", "tesseract")), pytest.raises(OCRError, match="Failed to save"):
                ocr.convert_to_docx("in.pdf", "out.docx")


# ===================================================================
# _normalize_backends — full branch coverage (lines 154-171)
# ===================================================================

class TestNormalizeBackendsGaps:

    def test_default_order(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(None)
                    assert result == ["tesseract", "paddle"]

    def test_dedup_and_ordering(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(
                        ["paddle", "tesseract", "paddle"])
                    assert result == ["paddle", "tesseract"]

    def test_unsupported_backend_filtered(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            ocr = PdfOCR()
            result = ocr._normalize_backends(["tesseract", "invalid"])
            assert result == ["tesseract"]

    def test_tesseract_unavailable_removed(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(["tesseract", "paddle"])
                    assert result == ["paddle"]

    def test_paddle_unavailable_removed(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
                ocr = PdfOCR()
                result = ocr._normalize_backends(["paddle", "tesseract"])
                assert result == ["tesseract"]

    def test_paddle_numpy_unavailable_removed(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(["paddle", "tesseract"])
                    assert result == ["tesseract"]

    def test_strip_and_lower(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(["  Tesseract  "])
                    assert result == ["tesseract"]

    def test_tesseract_available_paddle_unavailable_default(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(None)
                    assert result == ["tesseract"]

    def test_both_unavailable_returns_empty(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False):
                    ocr = PdfOCR()
                    result = ocr._normalize_backends(None)
                    assert result == []


# ===================================================================
# _combine_pages (line 175)
# ===================================================================

class TestCombinePagesGaps:

    def test_basic(self):
        result = PdfOCR._combine_pages(["page1", "page2", "page3"])
        assert result == "page1\n\npage2\n\npage3"

    def test_empty_entries_skipped(self):
        result = PdfOCR._combine_pages(["page1", "", " ", "page2"])
        assert result == "page1\n\npage2"

    def test_none_entries_skipped(self):
        result = PdfOCR._combine_pages(["page1", None, "page2"])
        assert result == "page1\n\npage2"

    def test_all_empty(self):
        result = PdfOCR._combine_pages(["", None, "  "])
        assert result == ""

    def test_empty_list(self):
        result = PdfOCR._combine_pages([])
        assert result == ""


# ===================================================================
# _sanitize_text (line 179)
# ===================================================================

class TestSanitizeTextGaps:

    def test_printable_preserved(self):
        result = PdfOCR._sanitize_text("Hello World 123")
        assert result == "Hello World 123"

    def test_non_printable_removed(self):
        result = PdfOCR._sanitize_text("Hello\x00World\x01Test")
        assert result == "HelloWorldTest"

    def test_newlines_tabs_carriage_preserved(self):
        result = PdfOCR._sanitize_text("Line1\nLine2\r\nLine3\tTab")
        assert result == "Line1\nLine2\r\nLine3\tTab"

    def test_empty_string(self):
        assert PdfOCR._sanitize_text("") == ""

    def test_none_becomes_empty(self):
        assert PdfOCR._sanitize_text(None) == ""


# ===================================================================
# _ocr_tesseract — full branch coverage (lines 182-192)
# ===================================================================

class TestOcrTesseractGaps:

    def test_tesseract_unavailable_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="Tesseract"):
                ocr._ocr_tesseract(["img1"])

    def test_success_all_pages(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pytesseract") as m_ts:
                m_ts.image_to_string.side_effect = ["page1", "page2"]
                ocr = PdfOCR()
                result = ocr._ocr_tesseract(["img1", "img2"])
                assert result == ["page1", "page2"]

    def test_per_page_failure_appends_empty(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pytesseract") as m_ts:
                m_ts.image_to_string.side_effect = ["ok", RuntimeError("bad page")]
                ocr = PdfOCR()
                result = ocr._ocr_tesseract(["img1", "img2"])
                assert result == ["ok", ""]

    def test_empty_result_from_image_to_string(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.pytesseract") as m_ts:
                m_ts.image_to_string.side_effect = [None, "valid"]
                ocr = PdfOCR()
                result = ocr._ocr_tesseract(["img1", "img2"])
                assert result[0] == ""
                assert result[1] == "valid"

    def test_empty_images_list(self):
        with patch("app.pipeline.ocr.pdf_ocr.TESSERACT_AVAILABLE", True):
            ocr = PdfOCR()
            result = ocr._ocr_tesseract([])
            assert result == []


# ===================================================================
# _ocr_paddle — full branch coverage (lines 195-233)
# ===================================================================

class TestOcrPaddleGaps:

    def test_paddle_unavailable_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", False):
            ocr = PdfOCR()
            with pytest.raises(OCRError, match="PaddleOCR"):
                ocr._ocr_paddle(["img1"])

    def test_numpy_unavailable_raises(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", MagicMock()):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", False):
                    ocr = PdfOCR()
                    with pytest.raises(OCRError, match="NumPy"):
                        ocr._ocr_paddle(["img1"])

    def test_success(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    img_mock = MagicMock(ndim=3)
                    img_mock.shape = (100, 200, 3)
                    m_np.array.return_value = img_mock
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 10, 10], ("hello", 0.9)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert len(result) == 1
                        assert "hello" in result[0]

    def test_per_page_failure_appends_empty(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.side_effect = [RuntimeError("bad img"),
                                              MagicMock(ndim=3)]
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("text", 0.9)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1", "img2"])
                        assert result[0] == ""
                        assert "text" in result[1]

    def test_nested_result_structure(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("word1", 0.8)],
                             [[1, 1, 2, 2], ("word2", 0.7)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert "word1" in result[0]
                        assert "word2" in result[0]

    def test_entry_less_than_2_skipped(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("valid", 0.9)],
                             ["invalid_short_entry"]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert "valid" in result[0]
                        assert "invalid_short_entry" not in result[0]

    def test_flat_list_result(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("flattext", 0.85)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert "flattext" in result[0]

    def test_bgr_conversion_with_rgb(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                m_np_arr = MagicMock()
                m_np_arr.ndim = 3
                m_np_arr.shape = (100, 200, 3)
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = m_np_arr
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("word", 0.9)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        ocr._ocr_paddle(["img1"])
                        assert m_np_arr.__getitem__.called

    def test_not_3d_image_no_bgr_conversion(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                m_np_arr = MagicMock()
                m_np_arr.ndim = 2
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = m_np_arr
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("word", 0.9)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        ocr._ocr_paddle(["img1"])

    def test_empty_result_from_ocr(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [[]]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert result[0] == ""

    def test_result_is_none(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = None
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert result[0] == ""

    def test_empty_images_list(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR", MagicMock()):
                with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                    ocr = PdfOCR()
                    result = ocr._ocr_paddle([])
                    assert result == []

    def test_entry_with_empty_text_skipped(self):
        with patch("app.pipeline.ocr.pdf_ocr.PADDLE_AVAILABLE", True):
            with patch("app.pipeline.ocr.pdf_ocr.NUMPY_AVAILABLE", True):
                with patch("app.pipeline.ocr.pdf_ocr.np") as m_np:
                    m_np.array.return_value = MagicMock(ndim=3)
                    m_np.array.return_value.shape = (100, 100, 3)
                    with patch("app.pipeline.ocr.pdf_ocr.PaddleOCR") as m_ocr:
                        m_instance = MagicMock()
                        m_instance.ocr.return_value = [
                            [[[0, 0, 1, 1], ("", 0.9)]]
                        ]
                        m_ocr.return_value = m_instance
                        ocr = PdfOCR()
                        result = ocr._ocr_paddle(["img1"])
                        assert result[0] == ""
