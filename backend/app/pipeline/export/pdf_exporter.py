# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import html
import logging
import os
import platform
import subprocess

from app.config.settings import settings

logger = logging.getLogger(__name__)


class PDFExporter:
    """
    Adapter for converting DOCX to PDF using LibreOffice headless.
    """

    def __init__(self, libreoffice_path: str | None = None):
        self.libreoffice_path = libreoffice_path or settings.LIBREOFFICE_PATH or self._find_libreoffice()

    def _find_libreoffice(self) -> str | None:
        """Attempt to find LibreOffice executable based on OS (dynamic cross-platform)."""
        if platform.system() == "Windows":
            paths = [
                "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
                "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
            ]
            for p in paths:
                if os.path.exists(p):
                    return p
            return None  # Do NOT assume on PATH if not found in common dirs
        elif platform.system() == "Darwin":  # macOS
            return "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        else:  # Linux
            return "libreoffice"  # Usually on PATH

    def _weasyprint_fallback(self, docx_path: str, pdf_path: str) -> str | None:
        """
        Fallback PDF renderer using WeasyPrint with lightweight DOCX-to-HTML conversion.
        """
        try:
            from docx import Document as DocxDocument
            from weasyprint import HTML
        except Exception as exc:
            logger.warning("WeasyPrint fallback unavailable: %s", exc)
            return None

        try:
            doc = DocxDocument(docx_path)
            paragraphs = []
            for para in doc.paragraphs:
                raw_text = (para.text or "").strip()
                if raw_text:
                    paragraphs.append(f"<p>{html.escape(raw_text)}</p>")

            if not paragraphs:
                paragraphs.append("<p></p>")

            html_content = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<style>body{font-family:'Times New Roman', serif;font-size:12pt;line-height:1.5;}</style>"
                "</head><body>" + "".join(paragraphs) + "</body></html>"
            )

            HTML(string=html_content).write_pdf(pdf_path)
            if os.path.exists(pdf_path):
                return pdf_path
            return None
        except Exception as exc:
            logger.warning("WeasyPrint fallback failed: %s", exc)
            return None

    def convert_to_pdf(self, docx_path: str, output_dir: str) -> str | None:
        """
        Convert DOCX to PDF using LibreOffice, then WeasyPrint, then docx2pdf.
        Raises RuntimeError if all engines fail.
        """
        if not os.path.exists(docx_path):
            return None

        pdf_filename = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        # 1. Try LibreOffice
        if self.libreoffice_path:
            try:
                command = [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    output_dir,
                    docx_path,
                ]

                result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)

                if result.returncode == 0 and os.path.exists(pdf_path):
                    return pdf_path

                error_msg = result.stderr or result.stdout or "Unknown LibreOffice error"
                raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")

            except Exception as lo_err:
                logger.warning("LibreOffice conversion failed: %s. Trying WeasyPrint fallback...", lo_err)
        else:
            logger.warning("LibreOffice not found. Trying WeasyPrint fallback directly...")

        # 2. Try WeasyPrint fallback
        weasy_path = self._weasyprint_fallback(docx_path, pdf_path)
        if weasy_path:
            return weasy_path

        # 3. Try docx2pdf fallback
        try:
            from docx2pdf import convert

            # docx2pdf requires an absolute path on Windows, let's make sure
            convert(os.path.abspath(docx_path), os.path.abspath(pdf_path))
            if os.path.exists(pdf_path):
                return pdf_path
            raise RuntimeError(f"generated PDF not found at: {pdf_path}")
        except Exception as d2p_err:
            logger.error("docx2pdf also failed: %s", d2p_err)
            raise RuntimeError(f"Both PDF export engines failed. Final error: {d2p_err}")
