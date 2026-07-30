# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


class TestPDFExporter:
    def test_init_default_path(self):
        with patch("app.pipeline.export.pdf_exporter.settings") as mock_settings:
            mock_settings.LIBREOFFICE_PATH = ""
            with patch("app.pipeline.export.pdf_exporter.PDFExporter._find_libreoffice", return_value=None):
                from app.pipeline.export.pdf_exporter import PDFExporter
                p = PDFExporter()
                assert p.libreoffice_path is None

    def test_init_with_custom_path(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path="/custom/soffice")
        assert p.libreoffice_path == "/custom/soffice"

    def test_find_libreoffice_windows(self):
        with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Windows"), \
             patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True):
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter()
            path = p._find_libreoffice()
            assert path is not None
            assert "soffice.exe" in path

    def test_find_libreoffice_windows_not_found(self):
        with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Windows"), \
             patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=False):
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter()
            path = p._find_libreoffice()
            assert path is None

    def test_find_libreoffice_macos(self):
        with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Darwin"):
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter()
            path = p._find_libreoffice()
            assert "MacOS/soffice" in path

    def test_find_libreoffice_linux(self):
        with patch("app.pipeline.export.pdf_exporter.platform.system", return_value="Linux"):
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter()
            path = p._find_libreoffice()
            assert path == "libreoffice"

    def test_convert_to_pdf_no_docx(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path=None)
        with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=False):
            result = p.convert_to_pdf("nonexistent.docx", "/tmp")
            assert result is None

    def test_convert_to_pdf_libreoffice_success(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True), \
             patch("app.pipeline.export.pdf_exporter.subprocess.run") as mock_run, \
             patch("app.pipeline.export.pdf_exporter.os.path.exists") as mock_exists:
            mock_run.return_value.returncode = 0
            mock_exists.side_effect = [True, True]
            result = p.convert_to_pdf("test.docx", "/tmp")
            assert result is not None
            assert result.endswith(".pdf")

    def test_convert_to_pdf_libreoffice_fails_then_weasyprint(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path="/usr/bin/soffice")
        with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True), \
             patch("app.pipeline.export.pdf_exporter.subprocess.run") as mock_run, \
             patch.object(p, "_weasyprint_fallback", return_value="/tmp/test.pdf"):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error"
            result = p.convert_to_pdf("test.docx", "/tmp")
            assert result == "/tmp/test.pdf"

    def test_weasyprint_fallback_no_libs(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path=None)
        result = p._weasyprint_fallback("test.docx", "/tmp/test.pdf")
        assert result is None

    def test_weasyprint_fallback_success(self):
        import sys
        mock_weasy = MagicMock()
        mock_docx_mod = MagicMock()
        sys.modules["weasyprint"] = mock_weasy
        sys.modules["weasyprint.HTML"] = mock_weasy.HTML
        sys.modules["docx"] = mock_docx_mod
        sys.modules["docx.Document"] = mock_docx_mod.Document
        try:
            mock_docx_mod.Document.return_value.paragraphs = [MagicMock(text="Hello World")]
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter(libreoffice_path=None)
            with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True):
                result = p._weasyprint_fallback("test.docx", "/tmp/test.pdf")
                assert result == "/tmp/test.pdf"
        finally:
            sys.modules.pop("weasyprint", None)
            sys.modules.pop("weasyprint.HTML", None)
            sys.modules.pop("docx", None)
            sys.modules.pop("docx.Document", None)

    def test_weasyprint_fallback_empty_paragraphs(self):
        import sys
        mock_weasy = MagicMock()
        mock_docx_mod = MagicMock()
        sys.modules["weasyprint"] = mock_weasy
        sys.modules["weasyprint.HTML"] = mock_weasy.HTML
        sys.modules["docx"] = mock_docx_mod
        sys.modules["docx.Document"] = mock_docx_mod.Document
        try:
            mock_docx_mod.Document.return_value.paragraphs = []
            from app.pipeline.export.pdf_exporter import PDFExporter
            p = PDFExporter(libreoffice_path=None)
            with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True):
                result = p._weasyprint_fallback("test.docx", "/tmp/test.pdf")
                assert result == "/tmp/test.pdf"
        finally:
            sys.modules.pop("weasyprint", None)
            sys.modules.pop("weasyprint.HTML", None)
            sys.modules.pop("docx", None)
            sys.modules.pop("docx.Document", None)

    def test_convert_to_pdf_all_fail_raises(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path=None)
        with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True), \
             patch.object(p, "_weasyprint_fallback", return_value=None), \
             patch("app.pipeline.export.pdf_exporter.convert", side_effect=Exception("no docx2pdf"), create=True):
            with pytest.raises(RuntimeError, match="Both PDF export engines failed"):
                p.convert_to_pdf("test.docx", "/tmp")

    def test_no_libreoffice_tries_weasyprint_directly(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        p = PDFExporter(libreoffice_path=None)
        with patch("app.pipeline.export.pdf_exporter.os.path.exists", return_value=True), \
             patch.object(p, "_weasyprint_fallback", return_value="/tmp/test.pdf"):
            result = p.convert_to_pdf("test.docx", "/tmp")
            assert result == "/tmp/test.pdf"
