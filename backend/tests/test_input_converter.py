import pytest
from unittest.mock import patch
import os


class TestConstructor:
    def test_default_temp_dir(self):
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        assert conv.temp_dir is not None

    def test_custom_temp_dir(self):
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter(temp_dir="/custom/tmp")
        assert conv.temp_dir == "/custom/tmp"


class TestSupportedExtensions:
    def test_docx_is_pass(self):
        from app.pipeline.input_conversion.converter import InputConverter
        assert InputConverter.SUPPORTED_EXTENSIONS[".docx"] == "pass"

    def test_md_is_pandoc(self):
        from app.pipeline.input_conversion.converter import InputConverter
        assert InputConverter.SUPPORTED_EXTENSIONS[".md"] == "pandoc"

    def test_pdf_is_libreoffice(self):
        from app.pipeline.input_conversion.converter import InputConverter
        assert InputConverter.SUPPORTED_EXTENSIONS[".pdf"] == "libreoffice"


class TestConvertToDocx:
    def test_file_not_found_raises(self):
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        with pytest.raises(FileNotFoundError):
            conv.convert_to_docx("/nonexistent/file.docx", "job1")

    def test_unsupported_extension_raises(self, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter, ConversionError
        f = tmp_path / "test.xyz"
        f.write_text("dummy")
        conv = InputConverter(temp_dir=str(tmp_path))
        with pytest.raises(ConversionError, match="Unsupported file format"):
            conv.convert_to_docx(str(f), "job1")

    @patch("shutil.copy2")
    def test_docx_copies_file(self, mock_copy, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.docx"
        src.write_text("dummy")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_docx(str(src), "job1")
        mock_copy.assert_called_once()
        assert "input.docx" in result

    @patch("app.pipeline.input_conversion.converter.InputConverter._run_pandoc")
    def test_markdown_uses_pandoc(self, mock_run, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.md"
        src.write_text("# Hello")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_docx(str(src), "job1")
        mock_run.assert_called_once()
        assert "input.docx" in result

    @patch("app.pipeline.input_conversion.converter.InputConverter._run_pandoc")
    def test_html_uses_pandoc(self, mock_run, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.html"
        src.write_text("<p>Hello</p>")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_docx(str(src), "job1")
        mock_run.assert_called_once()

    @patch("app.pipeline.input_conversion.converter.InputConverter._run_pandoc")
    def test_txt_uses_pandoc(self, mock_run, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.txt"
        src.write_text("Hello")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_docx(str(src), "job1")
        mock_run.assert_called_once()

    @patch("app.pipeline.input_conversion.converter.InputConverter._handle_pdf")
    def test_pdf_delegates_to_handler(self, mock_handle, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.pdf"
        src.write_text("%PDF")
        mock_handle.return_value = str(tmp_path / "job1" / "input.docx")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_docx(str(src), "job1")
        mock_handle.assert_called_once()

    def test_doc_uses_libreoffice(self, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        import unittest.mock as um
        src = tmp_path / "mydoc.doc"
        src.write_text("dummy")
        # Pre-create LO output as if _run_libreoffice succeeded
        job_dir = os.path.join(str(tmp_path), "job1")
        os.makedirs(job_dir)
        lo_output = os.path.join(job_dir, "mydoc.docx")
        open(lo_output, "w").close()
        conv = InputConverter(temp_dir=str(tmp_path))
        with um.patch.object(InputConverter, '_run_libreoffice'):
            result = conv.convert_to_docx(str(src), "job1")
        assert "input.docx" in result


class TestConvertToPdf:
    def test_file_not_found_raises(self):
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        with pytest.raises(FileNotFoundError):
            conv.convert_to_pdf("/nonexistent/file.docx", "job1")

    @patch("shutil.copy2")
    def test_pdf_input_copies(self, mock_copy, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.pdf"
        src.write_text("%PDF")
        conv = InputConverter(temp_dir=str(tmp_path))
        result = conv.convert_to_pdf(str(src), "job1")
        mock_copy.assert_called_once()
        assert result.endswith(".pdf")

    @patch("app.pipeline.input_conversion.converter.InputConverter._run_libreoffice_to_pdf")
    def test_docx_converted_via_libreoffice(self, mock_lo, tmp_path):
        from app.pipeline.input_conversion.converter import InputConverter
        src = tmp_path / "input.docx"
        src.write_text("dummy")
        conv = InputConverter(temp_dir=str(tmp_path))
        with pytest.raises(Exception):
            conv.convert_to_pdf(str(src), "job1")


class TestRunPandoc:
    @patch("shutil.which")
    def test_pandoc_not_found_raises(self, mock_which):
        mock_which.return_value = None
        from app.pipeline.input_conversion.converter import InputConverter, ConversionError
        conv = InputConverter()
        with pytest.raises(ConversionError, match="Pandoc not installed"):
            conv._run_pandoc("in.md", "out.docx")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_pandoc_success(self, mock_run, mock_which):
        mock_which.return_value = "pandoc"
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        conv._run_pandoc("in.md", "out.docx")
        mock_run.assert_called_once()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_pandoc_timeout_raises(self, mock_run, mock_which):
        from subprocess import TimeoutExpired
        mock_which.return_value = "pandoc"
        mock_run.side_effect = TimeoutExpired("pandoc", 120)
        from app.pipeline.input_conversion.converter import InputConverter, ConversionError
        conv = InputConverter()
        with pytest.raises(ConversionError, match="timed out"):
            conv._run_pandoc("in.md", "out.docx")


class TestRunLibreOffice:
    @patch("app.pipeline.input_conversion.converter.InputConverter._get_libreoffice_cmd")
    def test_soffice_not_found(self, mock_get):
        mock_get.return_value = None
        from app.pipeline.input_conversion.converter import InputConverter, ConversionError
        conv = InputConverter()
        with pytest.raises(ConversionError, match="not installed"):
            conv._run_libreoffice("in.pdf", "/tmp")

    @patch("app.pipeline.input_conversion.converter.InputConverter._get_libreoffice_cmd")
    @patch("subprocess.run")
    def test_soffice_success(self, mock_run, mock_get):
        mock_get.return_value = "soffice"
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        conv._run_libreoffice("in.pdf", "/tmp")
        mock_run.assert_called_once()


class TestGetLibreOfficeCmd:
    @patch("shutil.which")
    def test_finds_soffice(self, mock_which):
        mock_which.return_value = "soffice"
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        assert conv._get_libreoffice_cmd() == "soffice"

    @patch("shutil.which")
    @patch("os.path.exists")
    def test_returns_none_when_not_found(self, mock_exists, mock_which):
        mock_which.return_value = None
        mock_exists.return_value = False
        from app.pipeline.input_conversion.converter import InputConverter
        conv = InputConverter()
        assert conv._get_libreoffice_cmd() is None


class TestConversionError:
    def test_is_exception(self):
        from app.pipeline.input_conversion.converter import ConversionError
        assert issubclass(ConversionError, Exception)
