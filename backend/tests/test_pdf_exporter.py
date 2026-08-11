from unittest.mock import MagicMock, patch


class TestFindLibreOffice:
    def test_windows_paths(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="skip") # to avoid auto-find in init
        with patch("platform.system", return_value="Windows"):
            with patch("os.path.exists", side_effect=[False, True]):
                result = exporter._find_libreoffice()
        assert "LibreOffice" in result

    def test_windows_not_found(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="skip")
        with patch("platform.system", return_value="Windows"), patch("os.path.exists", return_value=False):
            result = exporter._find_libreoffice()
        assert result is None

    def test_macos_path(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="skip")
        with patch("platform.system", return_value="Darwin"):
            result = exporter._find_libreoffice()
        assert "LibreOffice.app" in result

    def test_linux_default(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="skip")
        with patch("platform.system", return_value="Linux"):
            result = exporter._find_libreoffice()
        assert result == "libreoffice"


class TestConvertToPdf:
    def test_file_not_found(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="/fake/soffice")
        with patch("os.path.exists", return_value=False):
            result = exporter.convert_to_pdf("/nonexistent.docx", "/tmp")
        assert result is None

    def test_libreoffice_success(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="/fake/soffice")
        with patch("os.path.exists", return_value=True), patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            result = exporter.convert_to_pdf("/tmp/test.docx", "/tmp")
        assert result is not None

    def test_libreoffice_failure_falls_to_weasyprint(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path="/fake/soffice")
        with patch("os.path.exists", return_value=True), patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error"
            mock_run.return_value = mock_result
            with patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/test.pdf"):
                result = exporter.convert_to_pdf("/tmp/test.docx", "/tmp")
        assert result == "/tmp/test.pdf"

    def test_no_libreoffice_uses_weasyprint(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter(libreoffice_path=None)
        with patch("os.path.exists", return_value=True):
            with patch.object(exporter, "_weasyprint_fallback", return_value="/tmp/test.pdf"):
                result = exporter.convert_to_pdf("/tmp/test.docx", "/tmp")
        assert result == "/tmp/test.pdf"


class TestWeasyprintFallback:
    def _setup_weasyprint_mocks(self):
        """Set up mock weasyprint module to avoid system DLL issues."""
        import sys
        mock_wp = MagicMock()
        mock_wp.HTML = MagicMock()
        mock_wp.HTML.return_value.write_pdf = MagicMock()
        sys.modules["weasyprint"] = mock_wp
        return mock_wp

    def _teardown_weasyprint_mocks(self):
        import sys
        sys.modules.pop("weasyprint", None)

    def test_missing_deps_returns_none(self):
        from app.pipeline.export.pdf_exporter import PDFExporter
        exporter = PDFExporter()
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result = exporter._weasyprint_fallback("/tmp/test.docx", "/tmp/test.pdf")
        assert result is None

    def test_successful_conversion(self):
        self._setup_weasyprint_mocks()
        try:
            from app.pipeline.export.pdf_exporter import PDFExporter
            exporter = PDFExporter()
            mock_docx = MagicMock()
            para = MagicMock()
            para.text = "Hello world"
            mock_docx.return_value.paragraphs = [para]
            with patch("docx.Document", mock_docx), patch("os.path.exists", return_value=True):
                result = exporter._weasyprint_fallback("/tmp/test.docx", "/tmp/test.pdf")
            assert result == "/tmp/test.pdf"
        finally:
            self._teardown_weasyprint_mocks()

    def test_no_paragraphs(self):
        self._setup_weasyprint_mocks()
        try:
            from app.pipeline.export.pdf_exporter import PDFExporter
            exporter = PDFExporter()
            mock_docx = MagicMock()
            mock_docx.return_value.paragraphs = []
            with patch("docx.Document", mock_docx), patch("os.path.exists", return_value=True):
                result = exporter._weasyprint_fallback("/tmp/test.docx", "/tmp/test.pdf")
            assert result == "/tmp/test.pdf"
        finally:
            self._teardown_weasyprint_mocks()

    def test_exception_during_conversion(self):
        mock_wp = self._setup_weasyprint_mocks()
        try:
            from app.pipeline.export.pdf_exporter import PDFExporter
            exporter = PDFExporter()
            mock_docx = MagicMock()
            para = MagicMock()
            para.text = "Hello"
            mock_docx.return_value.paragraphs = [para]
            mock_wp.HTML.side_effect = Exception("fail")
            with patch("docx.Document", mock_docx):
                result = exporter._weasyprint_fallback("/tmp/test.docx", "/tmp/test.pdf")
            assert result is None
        finally:
            self._teardown_weasyprint_mocks()
