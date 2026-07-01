# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import os
import subprocess
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import pytest
from app.pipeline.input_conversion.converter import InputConverter, ConversionError


# ===========================================================================
# Helpers
# ===========================================================================

INPUT = r"C:\path\file"
TMP = r"C:\Users\test\AppData\Local\Temp"


@pytest.fixture
def converter():
    return InputConverter()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ===========================================================================
# __init__ gap coverage (line 41)
# ===========================================================================

class TestInitGaps:
    """Line 41: temp_dir assignment."""

    def test_default_temp_dir(self):
        ic = InputConverter()
        assert ic.temp_dir == tempfile.gettempdir()

    def test_custom_temp_dir(self):
        ic = InputConverter(temp_dir="/custom/tmp")
        assert ic.temp_dir == "/custom/tmp"

    def test_temp_dir_empty_string_uses_default(self):
        ic = InputConverter(temp_dir="")
        assert ic.temp_dir == tempfile.gettempdir()


# ===========================================================================
# convert_to_docx gap coverage (lines 58-108)
# ===========================================================================

class TestConvertToDocxGaps:
    """Full convert_to_docx coverage."""

    def test_input_not_found_raises(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="not found"):
                ic.convert_to_docx(INPUT + ".docx", "job1")

    def test_unsupported_extension_raises(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with pytest.raises(ConversionError, match="Unsupported"):
                ic.convert_to_docx(INPUT + ".xyz", "job1")

    def test_pass_strategy_copies_file(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch("shutil.copy2") as m_copy:
                    result = ic.convert_to_docx(INPUT + ".docx", "job1")
                    m_copy.assert_called_once()
                    assert result == TMP + r"\job1\input.docx"

    def test_pandoc_strategy_calls_run_pandoc(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_pandoc") as m_run:
                    result = ic.convert_to_docx(INPUT + ".md", "job1")
                    m_run.assert_called_once()
                    assert result.endswith("input.docx")

    def test_pandoc_html_strategy(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_pandoc") as m_run:
                    result = ic.convert_to_docx(INPUT + ".html", "job1")
                    m_run.assert_called_once()

    def test_pandoc_txt_strategy(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_pandoc") as m_run:
                    result = ic.convert_to_docx(INPUT + ".txt", "job1")
                    m_run.assert_called_once()

    def test_pandoc_tex_strategy(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_pandoc") as m_run:
                    result = ic.convert_to_docx(INPUT + ".tex", "job1")
                    m_run.assert_called_once()

    def test_libreoffice_non_pdf_strategy_raises_when_output_missing(self):
        """Lines 89-106: libreoffice strategy for .doc when LO output not found."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, False]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with pytest.raises(ConversionError, match="failed to produce"):
                        ic.convert_to_docx(INPUT + ".doc", "job1")

    def test_libreoffice_non_pdf_renames_output(self):
        """LibreOffice output is renamed to input.docx."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True, True]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic.convert_to_docx(INPUT + ".doc", "job1")
                            m_rename.assert_called_once_with(
                                TMP + r"\job1\file.docx",
                                TMP + r"\job1\input.docx"
                            )
                            assert result == TMP + r"\job1\input.docx"

    def test_libreoffice_odt_strategy(self):
        """ODT file uses libreoffice strategy."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True, True]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic.convert_to_docx(INPUT + ".odt", "job1")
                            m_rename.assert_called_once()

    def test_libreoffice_rtf_strategy(self):
        """RTF file uses libreoffice strategy."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True, True]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic.convert_to_docx(INPUT + ".rtf", "job1")
                            m_rename.assert_called_once()

    def test_libreoffice_odt_output_not_found_raises(self):
        """ODT: LO output not found."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.path.exists") as m2:
                        m2.side_effect = lambda p: "file.docx" not in p
                        with pytest.raises(ConversionError, match="failed to produce"):
                            ic.convert_to_docx(INPUT + ".odt", "job1")

    def test_pdf_strategy_calls_handle_pdf(self):
        """PDF file calls _handle_pdf."""
        ic = InputConverter()
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_handle_pdf", return_value=r"D:\out.docx") as m_h:
                    result = ic.convert_to_docx(INPUT + ".pdf", "job1")
                    m_h.assert_called_once()
                    assert result == r"D:\out.docx"

    def test_path_absolute_conversion(self):
        """Input path is made absolute."""
        ic = InputConverter()
        with patch("os.path.abspath", return_value=INPUT + ".docx"):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch("shutil.copy2"):
                        result = ic.convert_to_docx("relative.docx", "job1")
                        # Should not raise

    def test_job_dir_created(self):
        """Job directory is created."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs") as m_mkdir:
                with patch("shutil.copy2"):
                    ic.convert_to_docx(INPUT + ".docx", "job1")
                    m_mkdir.assert_called_once_with(TMP + r"\job1", exist_ok=True)


# ===========================================================================
# _handle_pdf gap coverage (lines 115-168)
# ===========================================================================

class TestHandlePdfGaps:
    """Full _handle_pdf coverage."""

    PDF = r"C:\docs\input.pdf"

    def test_ocr_disabled_by_param(self):
        """Line 121: enable_ocr=False disables OCR."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.remove"):
                        with patch("os.rename"):
                            result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=False)
                            assert result == TMP + r"\job1\input.docx"

    def test_ocr_disabled_by_profile(self):
        """Line 120-125: profile disabled disables OCR."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = False
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch.object(ic, "_run_libreoffice"):
                        with patch("os.remove"):
                            with patch("os.rename"):
                                result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                assert result == TMP + r"\job1\input.docx"

    def test_ocr_disabled_by_profile_ocr(self):
        """Line 120: ocr_enabled=False in profile disables OCR."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = False
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch.object(ic, "_run_libreoffice"):
                        with patch("os.remove"):
                            with patch("os.rename"):
                                result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_scanned_success(self):
        """Lines 130-140: OCR enabled, scanned, success."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = True
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                        m_ocr.convert_to_docx.assert_called_once()
                        assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_scanned_ocr_error_fallback(self):
        """Lines 141-142: OCR fails with OCRError, falls back to LibreOffice."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                from app.pipeline.ocr.pdf_ocr import OCRError
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = True
                m_ocr.convert_to_docx.side_effect = OCRError("OCR engine failed")
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        with patch.object(ic, "_run_libreoffice"):
                            with patch("os.remove"):
                                with patch("os.rename"):
                                    result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                    assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_scanned_generic_exception_fallback(self):
        """Lines 143-144: OCR fails with generic Exception, falls back."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = True
                m_ocr.convert_to_docx.side_effect = Exception("unexpected")
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        with patch.object(ic, "_run_libreoffice"):
                            with patch("os.remove"):
                                with patch("os.rename"):
                                    result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                    assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_not_scanned(self):
        """Lines 130-144: OCR enabled but not scanned, falls to LibreOffice."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = False
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        with patch.object(ic, "_run_libreoffice"):
                            with patch("os.remove"):
                                with patch("os.rename"):
                                    result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                    assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_no_backends(self):
        """Lines 145-150: OCR enabled but no backends available."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = []
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch.object(ic, "_run_libreoffice"):
                        with patch("os.remove"):
                            with patch("os.rename"):
                                result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                                assert result == TMP + r"\job1\input.docx"

    def test_ocr_enabled_unsupported_backends_filtered(self):
        """Only tesseract/paddle backends are supported."""
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract", "paddle", "ocrmypdf", "unknown"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = True
                m_ocr.convert_to_docx.return_value = True
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=True)
                        # tesseract and paddle only
                        m_ocr.convert_to_docx.assert_called_once()
                        # backends should be ["tesseract", "paddle"]
                        call_args = m_ocr.convert_to_docx.call_args
                        assert len(call_args[1]["backends"]) == 2

    def test_libreoffice_output_already_matches(self):
        """When lo_output == output_path, rename is skipped."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=False)
                            m_rename.assert_not_called()
                            assert result == TMP + r"\job1\input.docx"

    def test_libreoffice_output_not_found_raises(self):
        """Lines 165-166: LO output not found raises."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice"):
                    with patch("os.path.exists") as m2:
                        m2.side_effect = lambda p: "input.docx" not in p
                        with pytest.raises(ConversionError, match="output not found"):
                            ic._handle_pdf(self.PDF, TMP + r"\job1", "job1", enable_ocr=False)

    def test_libreoffice_output_different_path_renamed(self):
        """LO output renamed to input.docx when stems differ."""
        ic = InputConverter(temp_dir=TMP)
        pdf_path = r"C:\docs\different.pdf"
        lo_output = TMP + r"\job1\different.docx"
        expected = TMP + r"\job1\input.docx"
        with patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice"):
                with patch("os.path.exists", side_effect=lambda p: p == lo_output or p == expected):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic._handle_pdf(pdf_path, TMP + r"\job1", "job1", enable_ocr=False)
                            m_rename.assert_called_once_with(lo_output, expected)
                            assert result == expected


# ===========================================================================
# convert_to_pdf gap coverage (lines 182-214)
# ===========================================================================

class TestConvertToPdfGaps:
    """Full convert_to_pdf coverage."""

    def test_input_not_found_raises(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="not found"):
                ic.convert_to_pdf(INPUT + ".docx", "job1")

    def test_input_already_pdf_copies(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch("shutil.copy2") as m_copy:
                    result = ic.convert_to_pdf(INPUT + ".pdf", "job1")
                    m_copy.assert_called_once()
                    assert result == TMP + r"\job1\input.pdf"

    def test_docx_converts_via_libreoffice(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice_to_pdf") as m_lo:
                    with patch("os.remove"):
                        with patch("os.rename"):
                            result = ic.convert_to_pdf(INPUT + ".docx", "job1")
                            m_lo.assert_called_once()
                            assert result == TMP + r"\job1\input.pdf"

    def test_lo_output_not_found_raises(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, False]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice_to_pdf"):
                    with pytest.raises(ConversionError, match="failed to generate"):
                        ic.convert_to_pdf(INPUT + ".docx", "job1")

    def test_lo_output_found_renamed(self):
        """LO output is renamed to input.pdf."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice_to_pdf"):
                    with patch("os.remove"):
                        with patch("os.rename") as m_rename:
                            result = ic.convert_to_pdf(INPUT + ".docx", "job1")
                            m_rename.assert_called_once()

    def test_md_converts_to_pdf_via_libreoffice_to_pdf(self):
        """Markdown also goes through LibreOffice for PDF."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice_to_pdf") as m_lo:
                    with patch("os.remove"):
                        with patch("os.rename"):
                            result = ic.convert_to_pdf(INPUT + ".md", "job1")
                            m_lo.assert_called_once()

    def test_remove_existing_output_path_exception_caught(self):
        """Line 207-210: remove exception caught."""
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True]):
            with patch("os.makedirs"):
                with patch.object(ic, "_run_libreoffice_to_pdf"):
                    with patch("os.remove", side_effect=PermissionError("denied")):
                        with patch("os.rename"):
                            # Should not raise
                            result = ic.convert_to_pdf(INPUT + ".docx", "job1")
                            assert result is not None


# ===========================================================================
# _run_libreoffice_to_pdf gap coverage (lines 218-236)
# ===========================================================================

class TestRunLibreofficeToPdfGaps:
    """Full _run_libreoffice_to_pdf coverage."""

    def test_soffice_not_installed_raises(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="not installed"):
                ic._run_libreoffice_to_pdf("/in.docx", "/outdir")

    def test_soffice_success(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run") as m_run:
                m_run.return_value = MagicMock()
                ic._run_libreoffice_to_pdf("/in.docx", "/outdir")
                args = m_run.call_args[0][0]
                assert "soffice" in args
                assert "--headless" in args
                assert "--convert-to" in args
                assert "pdf" in args
                assert "--outdir" in args

    def test_soffice_timeout(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 180)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_libreoffice_to_pdf("/in.docx", "/outdir")

    def test_soffice_called_process_error(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            err = subprocess.CalledProcessError(1, "soffice", stderr=b"error details")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice_to_pdf("/in.docx", "/outdir")

    def test_soffice_called_process_error_no_stderr(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            err = subprocess.CalledProcessError(1, "soffice", stderr=b"")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice_to_pdf("/in.docx", "/outdir")


# ===========================================================================
# _run_pandoc gap coverage (lines 245-255)
# ===========================================================================

class TestRunPandocGaps:
    """Full _run_pandoc coverage."""

    def test_pandoc_not_installed_raises(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with pytest.raises(ConversionError, match="Pandoc not installed"):
                ic._run_pandoc("/in.md", "/out.docx")

    def test_pandoc_success(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            with patch("subprocess.run") as m_run:
                m_run.return_value = MagicMock()
                ic._run_pandoc("/in.md", "/out.docx")
                m_run.assert_called_once_with(
                    ["pandoc", "/in.md", "-o", "/out.docx"],
                    check=True, capture_output=True, timeout=120
                )

    def test_pandoc_timeout(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pandoc", 120)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_pandoc("/in.md", "/out.docx")

    def test_pandoc_called_process_error(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            err = subprocess.CalledProcessError(1, "pandoc", stderr=b"error details")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_pandoc("/in.md", "/out.docx")

    def test_pandoc_called_process_error_no_stderr(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            err = subprocess.CalledProcessError(1, "pandoc", stderr=b"")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_pandoc("/in.md", "/out.docx")


# ===========================================================================
# _run_libreoffice gap coverage (lines 260-278)
# ===========================================================================

class TestRunLibreofficeGaps:
    """Full _run_libreoffice coverage."""

    def test_soffice_not_installed_raises(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="not installed"):
                ic._run_libreoffice("/in.pdf", "/outdir")

    def test_soffice_success(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run") as m_run:
                m_run.return_value = MagicMock()
                ic._run_libreoffice("/in.pdf", "/outdir")
                args = m_run.call_args[0][0]
                assert "soffice" in args
                assert "--headless" in args
                assert "--convert-to" in args
                assert "docx" in args
                assert "--outdir" in args

    def test_soffice_timeout(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 180)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_libreoffice("/in.pdf", "/outdir")

    def test_soffice_called_process_error(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            err = subprocess.CalledProcessError(1, "soffice", stderr=b"error")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice("/in.pdf", "/outdir")

    def test_soffice_called_process_error_no_stderr(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            err = subprocess.CalledProcessError(1, "soffice", stderr=b"")
            with patch("subprocess.run", side_effect=err):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice("/in.pdf", "/outdir")


# ===========================================================================
# _get_libreoffice_cmd gap coverage (lines 282-296)
# ===========================================================================

class TestGetLibreofficeCmdGaps:
    """Full _get_libreoffice_cmd coverage."""

    def test_returns_first_found_soffice(self):
        ic = InputConverter()
        with patch("shutil.which", side_effect=lambda x: x if x == "soffice" else None):
            result = ic._get_libreoffice_cmd()
            assert result == "soffice"

    def test_returns_first_found_libreoffice(self):
        ic = InputConverter()
        with patch("shutil.which", side_effect=lambda x: x if x == "libreoffice" else None):
            result = ic._get_libreoffice_cmd()
            assert result == "libreoffice"

    def test_returns_none_if_not_found(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with patch("os.path.exists", return_value=False):
                result = ic._get_libreoffice_cmd()
                assert result is None

    def test_windows_path_64bit_exists(self):
        ic = InputConverter()
        path64 = r"C:\Program Files\LibreOffice\program\soffice.exe"
        with patch("shutil.which", return_value=None):
            with patch("os.name", "nt"):
                with patch("os.path.exists", side_effect=lambda p: p == path64):
                    result = ic._get_libreoffice_cmd()
                    assert result == path64

    def test_windows_path_86bit_exists(self):
        ic = InputConverter()
        path86 = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        with patch("shutil.which", return_value=None):
            with patch("os.name", "nt"):
                with patch("os.path.exists", side_effect=lambda p: p == path86):
                    result = ic._get_libreoffice_cmd()
                    assert result == path86

    def test_windows_both_paths_exist_returns_first(self):
        ic = InputConverter()
        path64 = r"C:\Program Files\LibreOffice\program\soffice.exe"
        with patch("shutil.which", return_value=None):
            with patch("os.name", "nt"):
                with patch("os.path.exists", side_effect=lambda p: p == path64):
                    result = ic._get_libreoffice_cmd()
                    assert result == path64

    def test_windows_no_paths_exist_returns_none(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with patch("os.name", "nt"):
                with patch("os.path.exists", return_value=False):
                    result = ic._get_libreoffice_cmd()
                    assert result is None

    def test_non_windows_checks_which_and_path(self):
        """On non-Windows, checks shutil.which and doesn't check file paths."""
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with patch("os.name", "posix"):
                result = ic._get_libreoffice_cmd()
                assert result is None

    def test_shutil_which_libreoffice(self):
        """shutil.which finds libreoffice but not soffice."""
        ic = InputConverter()
        with patch("shutil.which", side_effect=lambda x: "libreoffice" if x == "libreoffice" else None):
            result = ic._get_libreoffice_cmd()
            assert result == "libreoffice"


# ===========================================================================
# Integration-style conversion flow tests
# ===========================================================================

class TestConversionFlow:
    """End-to-end conversion scenarios."""

    def test_docx_copy_flow(self, temp_dir):
        """Full flow: docx file through convert_to_docx."""
        src = os.path.join(temp_dir, "test.docx")
        Path(src).write_text("fake docx")
        ic = InputConverter(temp_dir=temp_dir)
        result = ic.convert_to_docx(src, "jobflow")
        assert os.path.exists(result)
        assert result.endswith("input.docx")
        assert Path(result).read_text() == "fake docx"

    def test_pdf_not_found_raises(self):
        ic = InputConverter()
        with pytest.raises(FileNotFoundError, match="not found"):
            ic.convert_to_pdf("/nonexistent/file.pdf", "job1")
