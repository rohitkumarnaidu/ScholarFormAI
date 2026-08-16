# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestInputConverter:
    def test_init_default_temp(self):
        from app.pipeline.input_conversion.converter import InputConverter

        ic = InputConverter()
        assert ic.temp_dir is not None

    def test_init_custom_temp(self):
        from app.pipeline.input_conversion.converter import InputConverter

        ic = InputConverter(temp_dir="/tmp/myconv")
        assert ic.temp_dir == "/tmp/myconv"

    def test_supported_extensions(self):
        from app.pipeline.input_conversion.converter import InputConverter

        assert ".docx" in InputConverter.SUPPORTED_EXTENSIONS
        assert ".pdf" in InputConverter.SUPPORTED_EXTENSIONS

    def test_get_libreoffice_cmd_path(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with patch("shutil.which", return_value="soffice"):
            assert InputConverter()._get_libreoffice_cmd() == "soffice"

    def test_get_libreoffice_cmd_not_found(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("shutil.which", return_value=None),
            patch("os.path.exists", return_value=False),
        ):
            assert InputConverter()._get_libreoffice_cmd() is None

    def test_get_libreoffice_cmd_windows_path(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("shutil.which", return_value=None),
            patch("os.name", "nt"),
        ):
            cmd = InputConverter()._get_libreoffice_cmd()
            assert cmd is not None
            assert "soffice.exe" in cmd

    def test_convert_to_docx_file_not_found(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError):
            InputConverter().convert_to_docx("/nonexistent.docx", "job1")

    def test_convert_to_docx_unsupported(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.xzy"),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.xzy", "job1")

    def test_convert_to_docx_docx_pass(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.docx"),
            patch("shutil.copy2") as mock_copy,
            patch("os.makedirs"),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.docx", "job1")
            assert "input.docx" in result
            mock_copy.assert_called_once()

    def test_convert_to_docx_pandoc_success(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.md"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("subprocess.run") as mock_run,
        ):
            result = InputConverter().convert_to_docx("/tmp/f.md", "job1")
            assert "input.docx" in result
            mock_run.assert_called_once()

    def test_convert_to_docx_pandoc_not_installed(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.md"),
            patch("os.makedirs"),
            patch("shutil.which", return_value=None),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.md", "job1")

    def test_convert_to_docx_pandoc_timeout(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.md"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pandoc", 120)),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.md", "job1")

    def test_convert_to_docx_pandoc_calledprocess_error(self):
        from app.pipeline.input_conversion.converter import InputConverter

        err = subprocess.CalledProcessError(1, "pandoc", stderr=b"parse error")
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.md"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("subprocess.run", side_effect=err),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.md", "job1")

    def test_convert_to_docx_libreoffice_success(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", side_effect=[True, True, True, True]),
            patch("os.path.abspath", return_value="/tmp/f.doc"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("os.rename"),
            patch("os.remove"),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.doc", "job1")
            assert "input.docx" in result

    def test_convert_to_docx_libreoffice_output_not_found(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", side_effect=[True, True, False]),
            patch("os.path.abspath", return_value="/tmp/f.doc"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.doc", "job1")

    def test_convert_to_docx_libreoffice_timeout(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.doc"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 180)),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.doc", "job1")

    def test_convert_to_docx_libreoffice_calledprocess_error(self):
        from app.pipeline.input_conversion.converter import InputConverter

        err = subprocess.CalledProcessError(1, "soffice", stderr=b"error")
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.doc"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run", side_effect=err),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.doc", "job1")

    def test_handle_pdf_ocr_disabled_by_profile(self):
        from app.pipeline.input_conversion.converter import InputConverter

        mock_enh_mgr = MagicMock()
        mock_enh_mgr.profile.enabled = True
        mock_enh_mgr.profile.ocr_enabled = False
        with (
            patch("os.path.exists", side_effect=[True, True, True, True]),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("app.services.enhancement_manager.enhancement_manager", mock_enh_mgr),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("os.rename"),
            patch("os.remove"),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.pdf", "job1", enable_ocr=True)
            assert "input.docx" in result

    def test_handle_pdf_ocr_success(self):
        from app.pipeline.input_conversion.converter import InputConverter

        mock_enh_mgr = MagicMock()
        mock_enh_mgr.profile.enabled = True
        mock_enh_mgr.profile.ocr_enabled = True
        mock_enh_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_pdf_ocr = MagicMock()
        mock_pdf_ocr.is_scanned.return_value = True
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("app.services.enhancement_manager.enhancement_manager", mock_enh_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_pdf_ocr),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.pdf", "job1", enable_ocr=True)
            assert "input.docx" in result
            mock_pdf_ocr.convert_to_docx.assert_called_once()

    def test_handle_pdf_not_scanned(self):
        from app.pipeline.input_conversion.converter import InputConverter

        mock_enh_mgr = MagicMock()
        mock_enh_mgr.profile.enabled = True
        mock_enh_mgr.profile.ocr_enabled = True
        mock_enh_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_pdf_ocr = MagicMock()
        mock_pdf_ocr.is_scanned.return_value = False
        with (
            patch("os.path.exists", side_effect=[True, True, True, True]),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("os.rename"),
            patch("os.remove"),
            patch("app.services.enhancement_manager.enhancement_manager", mock_enh_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_pdf_ocr),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.pdf", "job1", enable_ocr=True)
            assert "input.docx" in result

    def test_handle_pdf_ocr_fails_falls_to_libreoffice(self):
        from app.pipeline.input_conversion.converter import InputConverter

        mock_enh_mgr = MagicMock()
        mock_enh_mgr.profile.enabled = True
        mock_enh_mgr.profile.ocr_enabled = True
        mock_enh_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_pdf_ocr = MagicMock()
        mock_pdf_ocr.is_scanned.return_value = True
        mock_pdf_ocr.convert_to_docx.side_effect = Exception("OCR failed")
        with (
            patch("os.path.exists", side_effect=[True, True, True, True, False]),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("app.services.enhancement_manager.enhancement_manager", mock_enh_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_pdf_ocr),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_docx("/tmp/f.pdf", "job1", enable_ocr=True)

    def test_handle_pdf_no_supported_ocr_backends(self):
        from app.pipeline.input_conversion.converter import InputConverter

        mock_enh_mgr = MagicMock()
        mock_enh_mgr.profile.enabled = True
        mock_enh_mgr.profile.ocr_enabled = True
        mock_enh_mgr.get_ocr_backends.return_value = ["invalid_ocr"]
        with (
            patch("os.path.exists", side_effect=[True, True, True, True]),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("os.rename"),
            patch("os.remove"),
            patch("app.services.enhancement_manager.enhancement_manager", mock_enh_mgr),
        ):
            result = InputConverter().convert_to_docx("/tmp/f.pdf", "job1", enable_ocr=True)
            assert "input.docx" in result

    def test_convert_to_pdf_file_not_found(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with patch("os.path.exists", return_value=False), pytest.raises(FileNotFoundError):
            InputConverter().convert_to_pdf("/nonexistent.docx", "job1")

    def test_convert_to_pdf_already_pdf(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.pdf"),
            patch("os.makedirs"),
            patch("shutil.copy2") as mock_copy,
        ):
            result = InputConverter().convert_to_pdf("/tmp/f.pdf", "job1")
            assert "input.pdf" in result
            mock_copy.assert_called_once()

    def test_convert_to_pdf_libreoffice_success(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", side_effect=[True, True, True, False]),
            patch("os.path.abspath", return_value="/tmp/f.docx"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            patch("os.rename"),
        ):
            result = InputConverter().convert_to_pdf("/tmp/f.docx", "job1")
            assert "input.pdf" in result

    def test_convert_to_pdf_libreoffice_timeout(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.docx"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("soffice", 180)),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_pdf("/tmp/f.docx", "job1")

    def test_convert_to_pdf_libreoffice_output_not_found(self):
        from app.pipeline.input_conversion.converter import InputConverter

        with (
            patch("os.path.exists", side_effect=[True, False]),
            patch("os.path.abspath", return_value="/tmp/f.docx"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run"),
            patch.object(Path, "stem", return_value="f"),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_pdf("/tmp/f.docx", "job1")

    def test_convert_to_pdf_libreoffice_calledprocess_error(self):
        from app.pipeline.input_conversion.converter import InputConverter

        err = subprocess.CalledProcessError(1, "soffice", stderr=b"error")
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/tmp/f.docx"),
            patch("os.makedirs"),
            patch("shutil.which", return_value="/usr/bin/soffice"),
            patch("subprocess.run", side_effect=err),
            pytest.raises(Exception),
        ):
            InputConverter().convert_to_pdf("/tmp/f.docx", "job1")
