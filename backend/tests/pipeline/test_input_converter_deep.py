# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for Input Converter pipeline stage.
Covers convert_to_docx, convert_to_pdf, format dispatch,
pandoc/libreoffice/OCR fallback chains, error handling.
"""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
import pytest
import os
import subprocess
import tempfile
from pathlib import Path
from app.pipeline.input_conversion.converter import InputConverter, ConversionError


@pytest.fixture
def converter():
    return InputConverter()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def docx_file(temp_dir):
    p = os.path.join(temp_dir, "test.docx")
    Path(p).write_text("fake docx content")
    return p


@pytest.fixture
def md_file(temp_dir):
    p = os.path.join(temp_dir, "test.md")
    Path(p).write_text("# Hello\nworld")
    return p


@pytest.fixture
def html_file(temp_dir):
    p = os.path.join(temp_dir, "test.html")
    Path(p).write_text("<html><body><p>Hello</p></body></html>")
    return p


@pytest.fixture
def pdf_file(temp_dir):
    p = os.path.join(temp_dir, "test.pdf")
    Path(p).write_text("%PDF-1.4 fake")
    return p


@pytest.fixture
def tex_file(temp_dir):
    p = os.path.join(temp_dir, "test.tex")
    Path(p).write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}")
    return p


class TestSupportedExtensions:
    def test_docx_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".docx") == "pass"

    def test_doc_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".doc") == "libreoffice"

    def test_pdf_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".pdf") == "libreoffice"

    def test_md_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".md") == "pandoc"

    def test_html_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".html") == "pandoc"

    def test_txt_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".txt") == "pandoc"

    def test_tex_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".tex") == "pandoc"

    def test_odt_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".odt") == "libreoffice"

    def test_rtf_supported(self):
        assert InputConverter.SUPPORTED_EXTENSIONS.get(".rtf") == "libreoffice"

    def test_unsupported_raises(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.xyz")
        Path(p).write_text("data")
        with pytest.raises(ConversionError, match="Unsupported file format"):
            converter.convert_to_docx(p, "job1")


class TestConvertToDocx:
    def test_docx_copies_file(self, converter, docx_file, temp_dir):
        result = converter.convert_to_docx(docx_file, "jobcopy")
        assert os.path.exists(result)
        assert result.endswith("input.docx")

    def test_docx_source_not_found(self, converter):
        with pytest.raises(FileNotFoundError):
            converter.convert_to_docx("/nonexistent/path.docx", "job1")

    def test_md_uses_pandoc(self, converter, md_file):
        with patch.object(converter, "_run_pandoc") as mock_pandoc:
            result = converter.convert_to_docx(md_file, "jobmd")
            mock_pandoc.assert_called_once()

    def test_html_uses_pandoc(self, converter, html_file):
        with patch.object(converter, "_run_pandoc") as mock_pandoc:
            result = converter.convert_to_docx(html_file, "jobhtml")
            mock_pandoc.assert_called_once()

    def test_tex_uses_pandoc(self, converter, tex_file):
        with patch.object(converter, "_run_pandoc") as mock_pandoc:
            result = converter.convert_to_docx(tex_file, "jobtex")
            mock_pandoc.assert_called_once()

    def test_pdf_uses_handle_pdf(self, converter, pdf_file):
        with patch.object(converter, "_handle_pdf") as mock_handle:
            mock_handle.return_value = "/tmp/input.docx"
            result = converter.convert_to_docx(pdf_file, "jobpdf")
            mock_handle.assert_called_once()

    def test_doc_uses_libreoffice(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake doc content")
        converter.temp_dir = temp_dir
        lo_output = os.path.join(temp_dir, "jobdoc", "test.docx")
        Path(lo_output).parent.mkdir(parents=True, exist_ok=True)
        Path(lo_output).write_text("lo output")
        with patch.object(converter, "_run_libreoffice"):
            result = converter.convert_to_docx(p, "jobdoc")
            assert result.endswith("input.docx")

    def test_odt_uses_libreoffice(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.odt")
        Path(p).write_text("fake odt content")
        converter.temp_dir = temp_dir
        lo_output = os.path.join(temp_dir, "jobodt", "test.docx")
        Path(lo_output).parent.mkdir(parents=True, exist_ok=True)
        Path(lo_output).write_text("lo output")
        with patch.object(converter, "_run_libreoffice"):
            result = converter.convert_to_docx(p, "jobodt")
            assert result.endswith("input.docx")

    def test_rtf_uses_libreoffice(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.rtf")
        Path(p).write_text("fake rtf content")
        converter.temp_dir = temp_dir
        lo_output = os.path.join(temp_dir, "jobrtf", "test.docx")
        Path(lo_output).parent.mkdir(parents=True, exist_ok=True)
        Path(lo_output).write_text("lo output")
        with patch.object(converter, "_run_libreoffice"):
            result = converter.convert_to_docx(p, "jobrtf")
            assert result.endswith("input.docx")

    def test_libreoffice_output_not_found_raises(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake doc content")
        converter.temp_dir = temp_dir
        with patch.object(converter, "_run_libreoffice"):
            with pytest.raises(ConversionError, match="failed to produce"):
                converter.convert_to_docx(p, "jobloerr")


class TestConvertToPdf:
    def test_pdf_copies_file(self, converter, pdf_file, temp_dir):
        result = converter.convert_to_pdf(pdf_file, "jobpdfconv")
        assert os.path.exists(result)
        assert result.endswith("input.pdf")

    def test_docx_uses_libreoffice(self, converter, docx_file, temp_dir):
        converter.temp_dir = temp_dir
        lo_output = os.path.join(temp_dir, "jobdocxpdf", "test.pdf")
        Path(lo_output).parent.mkdir(parents=True, exist_ok=True)
        Path(lo_output).write_text("lo pdf output")
        with patch.object(converter, "_run_libreoffice_to_pdf"):
            result = converter.convert_to_pdf(docx_file, "jobdocxpdf")
            assert result.endswith("input.pdf")

    def test_source_not_found_raises(self, converter):
        with pytest.raises(FileNotFoundError):
            converter.convert_to_pdf("/nonexistent/path.docx", "job1")

    def test_libreoffice_output_not_found_raises(self, converter, docx_file, temp_dir):
        converter.temp_dir = temp_dir
        with patch.object(converter, "_run_libreoffice_to_pdf"):
            with pytest.raises(ConversionError, match="failed to generate"):
                converter.convert_to_pdf(docx_file, "jobloerr")


class TestHandlePdf:
    def test_ocr_enabled_and_scanned(self, converter, pdf_file, temp_dir):
        converter.temp_dir = temp_dir
        with (
            patch.object(converter, "_run_libreoffice") as mock_lo,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as mock_ocr_cls,
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            mock_em.get_ocr_backends.return_value = ["tesseract"]
            mock_ocr = MagicMock()
            mock_ocr.is_scanned.return_value = True
            mock_ocr_cls.return_value = mock_ocr
            result = converter._handle_pdf(pdf_file, temp_dir, "jobocr", True)
            mock_ocr.convert_to_docx.assert_called_once()

    def test_ocr_disabled_uses_libreoffice(self, converter, pdf_file, temp_dir):
        converter.temp_dir = temp_dir
        mock_lo_result = os.path.join(temp_dir, "test.docx")
        Path(mock_lo_result).write_text("lo result")
        with (
            patch.object(converter, "_run_libreoffice") as mock_lo,
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
        ):
            mock_em.profile.enabled = False
            result = converter._handle_pdf(pdf_file, temp_dir, "jobnoocr", True)
            mock_lo.assert_called_once()

    def test_ocr_falls_back_on_failure(self, converter, pdf_file, temp_dir):
        converter.temp_dir = temp_dir
        mock_lo_result = os.path.join(temp_dir, "test.docx")
        Path(mock_lo_result).write_text("fallback result")
        with (
            patch.object(converter, "_run_libreoffice") as mock_lo,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as mock_ocr_cls,
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            mock_em.get_ocr_backends.return_value = ["tesseract"]
            mock_ocr = MagicMock()
            mock_ocr.is_scanned.return_value = True
            mock_ocr.convert_to_docx.side_effect = Exception("OCR failed")
            mock_ocr_cls.return_value = mock_ocr
            result = converter._handle_pdf(pdf_file, temp_dir, "jobocrfall", True)
            mock_lo.assert_called_once()

    def test_not_scanned_uses_libreoffice(self, converter, pdf_file, temp_dir):
        converter.temp_dir = temp_dir
        mock_lo_result = os.path.join(temp_dir, "test.docx")
        Path(mock_lo_result).write_text("lo result")
        with (
            patch.object(converter, "_run_libreoffice") as mock_lo,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as mock_ocr_cls,
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            mock_em.get_ocr_backends.return_value = ["tesseract"]
            mock_ocr = MagicMock()
            mock_ocr.is_scanned.return_value = False
            mock_ocr_cls.return_value = mock_ocr
            result = converter._handle_pdf(pdf_file, temp_dir, "jobnotscan", True)
            mock_lo.assert_called_once()

    def test_no_backends_uses_libreoffice(self, converter, pdf_file, temp_dir):
        converter.temp_dir = temp_dir
        mock_lo_result = os.path.join(temp_dir, "test.docx")
        Path(mock_lo_result).write_text("lo result")
        with (
            patch.object(converter, "_run_libreoffice") as mock_lo,
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            mock_em.get_ocr_backends.return_value = []
            result = converter._handle_pdf(pdf_file, temp_dir, "jobnoback", True)
            mock_lo.assert_called_once()


class TestGetLibreofficeCmd:
    def test_returns_none_when_not_found(self, converter):
        with patch("shutil.which", return_value=None):
            with patch("os.path.exists", return_value=False):
                result = converter._get_libreoffice_cmd()
                assert result is None

    def test_finds_soffice(self, converter):
        with patch("shutil.which", return_value="soffice"):
            result = converter._get_libreoffice_cmd()
            assert result == "soffice"

    def test_checks_windows_paths(self, converter):
        with patch("shutil.which", return_value=None):
            with patch("os.name", "nt"):
                with patch("os.path.exists") as mock_exists:
                    mock_exists.side_effect = lambda x: x == r"C:\Program Files\LibreOffice\program\soffice.exe"
                    result = converter._get_libreoffice_cmd()
                    assert result == r"C:\Program Files\LibreOffice\program\soffice.exe"


class TestRunPandoc:
    def test_pandoc_called(self, converter, md_file, temp_dir):
        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock()
                output = os.path.join(temp_dir, "out.docx")
                converter._run_pandoc(md_file, output)
                mock_run.assert_called_once()

    def test_pandoc_not_installed(self, converter, md_file, temp_dir):
        with patch("shutil.which", return_value=None):
            with pytest.raises(ConversionError, match="Pandoc not installed"):
                converter._run_pandoc(md_file, os.path.join(temp_dir, "out.docx"))

    def test_pandoc_timed_out(self, converter, md_file, temp_dir):
        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pandoc", timeout=120)):
                with pytest.raises(ConversionError, match="timed out"):
                    converter._run_pandoc(md_file, os.path.join(temp_dir, "out.docx"))

    def test_pandoc_failed(self, converter, md_file, temp_dir):
        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "pandoc", stderr=b"error")):
                with pytest.raises(ConversionError, match="failed"):
                    converter._run_pandoc(md_file, os.path.join(temp_dir, "out.docx"))


class TestRunLibreoffice:
    def test_libreoffice_called(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake")
        with patch.object(converter, "_get_libreoffice_cmd", return_value="/usr/bin/soffice"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock()
                converter._run_libreoffice(p, temp_dir)
                mock_run.assert_called_once()

    def test_libreoffice_not_installed(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake")
        with patch.object(converter, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="LibreOffice not installed"):
                converter._run_libreoffice(p, temp_dir)

    def test_libreoffice_timed_out(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake")
        with patch.object(converter, "_get_libreoffice_cmd", return_value="/usr/bin/soffice"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=180)):
                with pytest.raises(ConversionError, match="timed out"):
                    converter._run_libreoffice(p, temp_dir)

    def test_libreoffice_failed(self, converter, temp_dir):
        p = os.path.join(temp_dir, "test.doc")
        Path(p).write_text("fake")
        with patch.object(converter, "_get_libreoffice_cmd", return_value="/usr/bin/soffice"):
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "soffice", stderr=b"error")):
                with pytest.raises(ConversionError, match="failed"):
                    converter._run_libreoffice(p, temp_dir)


class TestRunLibreofficeToPdf:
    def test_pdf_conversion_called(self, converter, docx_file, temp_dir):
        with patch.object(converter, "_get_libreoffice_cmd", return_value="/usr/bin/soffice"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock()
                converter._run_libreoffice_to_pdf(docx_file, temp_dir)
                mock_run.assert_called_once()

    def test_pdf_not_installed(self, converter, docx_file, temp_dir):
        with patch.object(converter, "_get_libreoffice_cmd", return_value=None):
            with pytest.raises(ConversionError, match="LibreOffice not installed"):
                converter._run_libreoffice_to_pdf(docx_file, temp_dir)

    def test_pdf_timed_out(self, converter, docx_file, temp_dir):
        with patch.object(converter, "_get_libreoffice_cmd", return_value="/usr/bin/soffice"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=180)):
                with pytest.raises(ConversionError, match="timed out"):
                    converter._run_libreoffice_to_pdf(docx_file, temp_dir)


class TestInitialization:
    def test_default_temp_dir(self):
        converter = InputConverter()
        assert converter.temp_dir == tempfile.gettempdir()

    def test_custom_temp_dir(self, temp_dir):
        converter = InputConverter(temp_dir=temp_dir)
        assert converter.temp_dir == temp_dir
