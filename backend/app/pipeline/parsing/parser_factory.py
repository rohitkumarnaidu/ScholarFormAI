# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Parser Factory - Automatically select the correct parser for a given file format.

This factory pattern allows the pipeline to support multiple input formats
without hardcoding parser selection logic throughout the codebase.
"""

import logging
import os
from typing import Optional

from app.config.settings import settings
from app.pipeline.parsing.base_parser import BaseParser
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.parsing.pdf_parser import PdfParser
from app.pipeline.parsing.txt_parser import TxtParser
from app.pipeline.parsing.html_parser import HtmlParser
from app.pipeline.parsing.md_parser import MarkdownParser
from app.pipeline.parsing.tex_parser import TexParser
from app.pipeline.safety import safe_function

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory to create the appropriate parser for a given file format."""

    def __init__(self):
        """Initialize the factory with all available parsers."""
        # Try to initialize all parsers (some may fail if dependencies missing)
        self.parsers = []
        in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        enable_nougat = bool(settings.ENABLE_NOUGAT_PARSER)

        # Keep fast PDF extraction as default. Nougat stays opt-in and is used
        # as secondary OCR parser when explicitly enabled.
        if in_pytest and not enable_nougat:
            # Keep tests deterministic and fast unless explicitly enabled.
            enable_nougat = False

        # DOCX parser (always available - core functionality)
        try:
            self.parsers.append(DocxParser())
        except Exception as e:
            logger.warning("DocxParser initialization failed: %s", e)

        # PDF parser - PRIMARY (fast path via PyMuPDF)
        try:
            self.parsers.append(PdfParser())
        except ImportError:
            logger.info("PDF parsing not available (install PyMuPDF: pip install PyMuPDF)")
        except Exception as e:
            logger.warning("PdfParser initialization failed: %s", e)

        # Nougat parser is optional and used as OCR fallback when enabled.
        if enable_nougat:
            try:
                from app.pipeline.parsing.nougat_parser import NougatParser

                self.parsers.append(NougatParser())
                logger.info("NougatParser (Meta AI) enabled as optional PDF OCR fallback.")
            except ImportError:
                logger.info("Nougat not available (install with: pip install nougat-ocr).")
            except Exception as e:
                logger.warning("NougatParser initialization failed: %s.", e)

        # Plain text parser (always available)
        try:
            self.parsers.append(TxtParser())
        except Exception as e:
            logger.warning("TxtParser initialization failed: %s", e)

        # HTML parser (requires BeautifulSoup4)
        try:
            self.parsers.append(HtmlParser())
        except ImportError:
            logger.info(
                "HTML parsing not available (install beautifulsoup4: pip install beautifulsoup4)"
            )
        except Exception as e:
            logger.warning("HtmlParser initialization failed: %s", e)

        # Markdown parser (always available)
        try:
            self.parsers.append(MarkdownParser())
        except Exception as e:
            logger.warning("MarkdownParser initialization failed: %s", e)

        # TeX parser (always available)
        try:
            self.parsers.append(TexParser())
        except Exception as e:
            logger.warning("TexParser initialization failed: %s", e)

    @safe_function(fallback_value=None, error_message="ParserFactory.get_parser failed")
    def get_parser(self, file_path: str) -> Optional[BaseParser]:
        """
        Get the appropriate parser for the given file.

        Args:
            file_path: Path to the input file

        Returns:
            Parser instance that can handle the file format

        Raises:
            ValueError: If no parser supports the file format
        """
        # Extract file extension
        _, ext = os.path.splitext(file_path)
        file_ext = ext.lower()

        # Find matching parser
        for parser in self.parsers:
            if parser.supports_format(file_ext):
                return parser

        # No parser found - raise ValueError
        supported_formats = set()
        for parser in self.parsers:
            # Get supported formats from each parser
            for ext in [
                ".docx",
                ".pdf",
                ".txt",
                ".html",
                ".htm",
                ".md",
                ".markdown",
                ".tex",
                ".latex",
                ".doc",
            ]:
                if parser.supports_format(ext):
                    supported_formats.add(ext)

        raise ValueError(
            f"No parser available for file format '{file_ext}'. "
            f"Supported formats: {', '.join(sorted(supported_formats))}"
        )

    def get_supported_formats(self) -> list:
        """
        Get list of all supported file formats.

        Returns:
            List of file extensions (e.g., ['.docx', '.pdf', '.txt'])
        """
        supported = set()
        for parser in self.parsers:
            for ext in [
                ".docx",
                ".pdf",
                ".txt",
                ".html",
                ".htm",
                ".md",
                ".markdown",
                ".tex",
                ".latex",
                ".doc",
            ]:
                if parser.supports_format(ext):
                    supported.add(ext)
        return sorted(supported)
