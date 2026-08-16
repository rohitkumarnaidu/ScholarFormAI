# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.input_conversion.converter import ConversionError, InputConverter

# ===========================================================================
# ConversionError
# ===========================================================================


class TestConversionError:
    def test_is_exception(self):
        assert issubclass(ConversionError, Exception)

    def test_can_be_raised(self):
        with pytest.raises(ConversionError, match="boom"):
            raise ConversionError("boom")


# ===========================================================================
# InputConverter.__init__
# ===========================================================================


class TestInputConverterInit:
    def test_default_temp_dir(self):
        ic = InputConverter()
        assert ic.temp_dir == tempfile.gettempdir()

    def test_custom_temp_dir(self):
        ic = InputConverter(temp_dir="/custom/tmp")
        assert ic.temp_dir == "/custom/tmp"

    def test_supported_extensions_class_var(self):
        assert ".docx" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".doc" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".pdf" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".md" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".html" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".txt" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".tex" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".odt" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".rtf" in InputConverter.SUPPORTED_EXTENSIONS


# ===========================================================================
# convert_to_docx
# ===========================================================================

INPUT = "/path/file"
TMP = "/tmp/local/temp"


class TestConvertToDocx:
    def test_input_file_not_found(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError, match="not found"):
            ic.convert_to_docx(INPUT + ".docx", "job1")

    def test_unsupported_extension(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True), pytest.raises(ConversionError, match="Unsupported"):
            ic.convert_to_docx(INPUT + ".xyz", "job1")

    def test_pass_strategy_copies_file(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True), patch("os.makedirs"), patch("shutil.copy2") as m_copy:
            result = ic.convert_to_docx(INPUT + ".docx", "job1")
            m_copy.assert_called_once()
            assert result == TMP + "/job1/input.docx"

    def test_pandoc_strategy_calls_run_pandoc(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            with patch.object(ic, "_run_pandoc") as m_run:
                result = ic.convert_to_docx(INPUT + ".md", "job1")
                m_run.assert_called_once()
                assert result.endswith("input.docx")

    def test_libreoffice_strategy_non_pdf_calls_run(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, False]), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice") as m_lo:
                with pytest.raises(ConversionError):
                    ic.convert_to_docx(INPUT + ".doc", "job1")
                m_lo.assert_called_once()

    def test_libreoffice_renames_lo_output(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, True, True, True]), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice"):
                with patch("os.remove"):
                    with patch("os.rename") as m_rename:
                        ic.convert_to_docx(INPUT + ".doc", "job1")
                        m_rename.assert_called_once_with(TMP + "/job1/file.docx", TMP + "/job1/input.docx")

    def test_libreoffice_lo_output_not_found_raises(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice"):
                lo_path = TMP + "/job1/file.docx"
                with patch("os.path.exists") as m2:
                    m2.side_effect = lambda p: lo_path not in p
                    with pytest.raises(ConversionError, match="failed to produce"):
                        ic.convert_to_docx(INPUT + ".doc", "job1")

    def test_pdf_strategy_calls_handle_pdf(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            with patch.object(ic, "_handle_pdf", return_value="/out.docx") as m_h:
                result = ic.convert_to_docx(INPUT + ".pdf", "job1")
                m_h.assert_called_once()
                assert result == "/out.docx"


# ===========================================================================
# _get_libreoffice_cmd
# ===========================================================================


class TestGetLibreofficeCmd:
    def test_returns_first_found(self):
        ic = InputConverter()
        with patch("shutil.which", side_effect=lambda x: x if x == "soffice" else None):
            result = ic._get_libreoffice_cmd()
            assert result == "soffice"

    def test_returns_none_if_not_found(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None), patch("os.path.exists", return_value=False):
            result = ic._get_libreoffice_cmd()
            assert result is None

    def test_windows_path_exists(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with patch("os.path.exists", side_effect=lambda p: "LibreOffice" in p):
                with patch("os.name", "nt"):
                    result = ic._get_libreoffice_cmd()
                    assert result is not None
                    assert "LibreOffice" in result


# ===========================================================================
# _run_pandoc
# ===========================================================================


class TestRunPandoc:
    def test_pandoc_not_installed(self):
        ic = InputConverter()
        with patch("shutil.which", return_value=None):
            with pytest.raises(ConversionError, match="Pandoc not installed"):
                ic._run_pandoc("/in.md", "/out.docx")

    def test_pandoc_success(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"), patch("subprocess.run") as m_run:
            ic._run_pandoc("/in.md", "/out.docx")
            m_run.assert_called_once_with(
                ["pandoc", "/in.md", "-o", "/out.docx"], check=True, capture_output=True, timeout=120
            )

    def test_pandoc_timeout(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            with patch("subprocess.run", side_effect=TimeoutExpiredMock("pandoc", 120)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_pandoc("/in.md", "/out.docx")

    def test_pandoc_called_process_error(self):
        ic = InputConverter()
        with patch("shutil.which", return_value="pandoc"):
            with patch("subprocess.run", side_effect=CalledProcessErrorMock(1, "pandoc")):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_pandoc("/in.md", "/out.docx")


# ===========================================================================
# _run_libreoffice
# ===========================================================================


class TestRunLibreoffice:
    def test_soffice_not_installed(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="not installed"):
                ic._run_libreoffice("/in.pdf", "/outdir")

    def test_soffice_success(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"), patch("subprocess.run") as m_run:
            ic._run_libreoffice("/in.pdf", "/outdir")
            m_run.assert_called_once()
            args = m_run.call_args[0][0]
            assert "soffice" in args
            assert "--headless" in args
            assert "--convert-to" in args
            assert "docx" in args

    def test_soffice_timeout(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=TimeoutExpiredMock("soffice", 180)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_libreoffice("/in.pdf", "/outdir")

    def test_soffice_called_process_error(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=CalledProcessErrorMock(1, "soffice")):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice("/in.pdf", "/outdir")


# ===========================================================================
# _run_libreoffice_to_pdf
# ===========================================================================


class TestRunLibreofficeToPdf:
    def test_soffice_not_installed(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="not installed"):
                ic._run_libreoffice_to_pdf("/in.docx", "/outdir")

    def test_soffice_success(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"), patch("subprocess.run") as m_run:
            ic._run_libreoffice_to_pdf("/in.docx", "/outdir")
            args = m_run.call_args[0][0]
            assert "pdf" in args

    def test_soffice_timeout(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=TimeoutExpiredMock("soffice", 180)):
                with pytest.raises(ConversionError, match="timed out"):
                    ic._run_libreoffice_to_pdf("/in.docx", "/outdir")

    def test_soffice_called_process_error(self):
        ic = InputConverter()
        with patch.object(ic, "_get_libreoffice_cmd", return_value="soffice"):
            with patch("subprocess.run", side_effect=CalledProcessErrorMock(1, "soffice")):
                with pytest.raises(ConversionError, match="failed"):
                    ic._run_libreoffice_to_pdf("/in.docx", "/outdir")


# ===========================================================================
# _handle_pdf
# ===========================================================================

PDF = "/docs/input.pdf"


class TestHandlePdf:
    def test_ocr_disabled_uses_libreoffice(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice"):
                with patch("os.remove"):
                    with patch("os.rename"):
                        result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=False)
                        assert result == TMP + "/job1/input.docx"

    def test_ocr_disabled_by_profile(self):
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
                                result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=True)
                                assert result == TMP + "/job1/input.docx"

    def test_ocr_enabled_scanned_success(self):
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
                with patch("os.path.exists", return_value=True), patch("os.makedirs"):
                    result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=True)
                    m_ocr.convert_to_docx.assert_called_once()
                    assert result == TMP + "/job1/input.docx"

    def test_ocr_enabled_scanned_fails_fallsback(self):
        ic = InputConverter(temp_dir=TMP)
        enh_mock = MagicMock()
        enh_mock.profile.enabled = True
        enh_mock.profile.ocr_enabled = True
        enh_mock.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", enh_mock):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as m_ocr_cls:
                m_ocr = MagicMock()
                m_ocr.is_scanned.return_value = True
                m_ocr.convert_to_docx.side_effect = Exception("OCR error")
                m_ocr_cls.return_value = m_ocr
                with patch("os.path.exists", return_value=True), patch("os.makedirs"):
                    with patch.object(ic, "_run_libreoffice"):
                        with patch("os.remove"):
                            with patch("os.rename"):
                                result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=True)
                                assert result == TMP + "/job1/input.docx"

    def test_ocr_enabled_not_scanned(self):
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
                with patch("os.path.exists", return_value=True), patch("os.makedirs"):
                    with patch.object(ic, "_run_libreoffice"):
                        with patch("os.remove"):
                            with patch("os.rename"):
                                result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=True)
                                assert result == TMP + "/job1/input.docx"

    def test_ocr_enabled_no_backends(self):
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
                                result = ic._handle_pdf(PDF, TMP + "/job1", "job1", enable_ocr=True)
                                assert result == TMP + "/job1/input.docx"


# ===========================================================================
# convert_to_pdf
# ===========================================================================


class TestConvertToPdf:
    def test_input_not_found(self):
        ic = InputConverter()
        with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError, match="not found"):
            ic.convert_to_pdf(INPUT + ".docx", "job1")

    def test_input_already_pdf_copies(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True), patch("os.makedirs"), patch("shutil.copy2") as m_copy:
            result = ic.convert_to_pdf(PDF, "job1")
            m_copy.assert_called_once()
            assert result == TMP + "/job1/input.pdf"

    def test_non_pdf_converts_via_libreoffice(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice_to_pdf") as m_lo:
                with patch("os.remove"):
                    with patch("os.rename"):
                        result = ic.convert_to_pdf(INPUT + ".docx", "job1")
                        m_lo.assert_called_once()
                        assert result == TMP + "/job1/input.pdf"

    def test_lo_output_not_found_raises(self):
        ic = InputConverter(temp_dir=TMP)
        with patch("os.path.exists", side_effect=[True, False]), patch("os.makedirs"):
            with patch.object(ic, "_run_libreoffice_to_pdf"):
                with pytest.raises(ConversionError, match="failed to generate"):
                    ic.convert_to_pdf(INPUT + ".docx", "job1")


# ===========================================================================
# Helpers
# ===========================================================================


class TimeoutExpiredMock(subprocess.TimeoutExpired):
    def __init__(self, cmd, timeout):
        super().__init__(cmd, timeout)


class CalledProcessErrorMock(subprocess.CalledProcessError):
    def __init__(self, returncode, cmd):
        self.returncode = returncode
        self.cmd = cmd
        self.stderr = b"error details"
