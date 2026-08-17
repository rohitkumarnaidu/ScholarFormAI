# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestFindLibreOffice:
    def test_windows_found(self):
        with (
            patch("platform.system", return_value="Windows"),
            patch("os.path.exists", side_effect=lambda p: p.endswith("soffice.exe")),
        ):
            from app.pipeline.export.pdf_exporter import PDFExporter

            result = PDFExporter(libreoffice_path="")._find_libreoffice()
            assert result
            assert "soffice.exe" in result

    def test_windows_not_found(self):
        with (
            patch("platform.system", return_value="Windows"),
            patch("os.path.exists", return_value=False),
        ):
            from app.pipeline.export.pdf_exporter import PDFExporter

            assert PDFExporter(libreoffice_path="")._find_libreoffice() is None

    def test_macos(self):
        with patch("platform.system", return_value="Darwin"):
            from app.pipeline.export.pdf_exporter import PDFExporter

            result = PDFExporter(libreoffice_path="")._find_libreoffice()
            assert "LibreOffice.app" in result

    def test_linux(self):
        with patch("platform.system", return_value="Linux"):
            from app.pipeline.export.pdf_exporter import PDFExporter

            assert PDFExporter(libreoffice_path="")._find_libreoffice() == "libreoffice"


class TestInit:
    def test_explicit_path(self):
        with patch("app.pipeline.export.pdf_exporter.settings") as mock_settings:
            mock_settings.LIBREOFFICE_PATH = ""
            from app.pipeline.export.pdf_exporter import PDFExporter

            exporter = PDFExporter(libreoffice_path="/custom/soffice")
            assert exporter.libreoffice_path == "/custom/soffice"

    def test_fallback_to_find(self):
        with patch("app.pipeline.export.pdf_exporter.settings") as mock_settings:
            mock_settings.LIBREOFFICE_PATH = ""
            from app.pipeline.export.pdf_exporter import PDFExporter

            with patch.object(PDFExporter, "_find_libreoffice", return_value="/found/soffice"):
                exporter = PDFExporter()
                assert exporter.libreoffice_path == "/found/soffice"

    def test_settings_path(self):
        with patch("app.pipeline.export.pdf_exporter.settings") as mock_settings:
            mock_settings.LIBREOFFICE_PATH = "/settings/soffice"
            from app.pipeline.export.pdf_exporter import PDFExporter

            exporter = PDFExporter()
            assert "settings" in exporter.libreoffice_path


class TestWeasyPrintFallback:
    def test_import_fails_returns_none(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="")
        with patch("docx.Document", side_effect=Exception("no docx")):
            result = exporter._weasyprint_fallback("/tmp/in.docx", "/tmp/out.pdf")
            assert result is None


class TestConvertToPdf:
    def test_file_not_found(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with patch("os.path.exists", return_value=False):
            assert exporter.convert_to_pdf("/nonexistent.docx", "/tmp") is None

    def test_libreoffice_success(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock(returncode=0, stdout="", stderr="")
            mock_run.return_value = mock_result
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result
            assert result.endswith(".pdf")

    def test_libreoffice_fails_fallback_succeeds(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run") as mock_run,
            patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/out/doc.pdf"),
        ):
            mock_result = MagicMock(returncode=1, stdout="", stderr="error")
            mock_run.return_value = mock_result
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result == "/tmp/out/doc.pdf"

    def test_libreoffice_timeout_fallback_succeeds(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=30)),
            patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/out/doc.pdf"),
        ):
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result == "/tmp/out/doc.pdf"

    def test_libreoffice_not_found(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/out/doc.pdf"),
        ):
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result == "/tmp/out/doc.pdf"

    @pytest.mark.skip(reason="docx2pdf may not be installed in CI")
    def test_all_engines_fail(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run") as mock_run,
            patch.object(exporter, "_weasyprint_fallback", return_value=None),
            patch("docx2pdf.convert", side_effect=Exception("docx2pdf failed")),
        ):
            mock_result = MagicMock(returncode=1, stdout="", stderr="err")
            mock_run.return_value = mock_result
            with pytest.raises(RuntimeError, match="Both PDF export engines failed"):
                exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")

    def test_libreoffice_oserror(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run", side_effect=OSError("permission denied")),
            patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/out/doc.pdf"),
        ):
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result == "/tmp/out/doc.pdf"

    @pytest.mark.skip(reason="docx2pdf may not be installed in CI")
    def test_docx2pdf_fallback_success(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run") as mock_run,
            patch.object(exporter, "_weasyprint_fallback", return_value=None),
            patch("docx2pdf.convert"),
        ):
            mock_result = MagicMock(returncode=1, stdout="", stderr="err")
            mock_run.return_value = mock_result
            result = exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
            assert result
            assert result.endswith(".pdf")

    @pytest.mark.skip(reason="docx2pdf may not be installed in CI")
    def test_docx2pdf_fails_runtime_error(self):
        from app.pipeline.export.pdf_exporter import PDFExporter

        exporter = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with (
            patch("os.path.exists", side_effect=lambda p: p.endswith(".docx") or p.endswith(".pdf")),
            patch("subprocess.run") as mock_run,
            patch.object(exporter, "_weasyprint_fallback", return_value=None),
            patch("docx2pdf.convert", side_effect=Exception("failed")),
        ):
            mock_result = MagicMock(returncode=1, stdout="", stderr="err")
            mock_run.return_value = mock_result
            with pytest.raises(RuntimeError, match="Both PDF export engines failed"):
                exporter.convert_to_pdf("/tmp/doc.docx", "/tmp/out")
