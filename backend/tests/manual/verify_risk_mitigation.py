# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import logging

# Add backend to path
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.pipeline.parsing.pdf_parser import PdfParser
from app.pipeline.parsing.tex_parser import TexParser
from app.pipeline.parsing.txt_parser import TxtParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RiskVerification")


class TestRiskMitigation(unittest.TestCase):
    @patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True)
    def test_pdf_font_analysis_logic(self):
        """Test the logic of font analysis without needing a real PDF."""
        # Ensure we can init even if fitz is missing in test env
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            parser = PdfParser()

        # Test 1: Weighted Mode Calculation
        # Mock a PDF doc with pages -> blocks -> lines -> spans
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        # Create a text dict structure
        # Block 1: 100 chars of size 12.0
        # Block 2: 20 chars of size 24.0 (Heading)
        text_dict = {
            "blocks": [
                {"type": 0, "lines": [{"spans": [{"size": 12.0, "text": "a" * 100}]}]},
                {"type": 0, "lines": [{"spans": [{"size": 24.0, "text": "b" * 20}]}]},
            ]
        }
        mock_page.get_text.return_value = text_dict

        # Run calculation with a LIST of pages (simulating fitz document)
        try:
            body_size = parser._calculate_font_stats([mock_page])
            print(f"Calculated Body Size: {body_size}")

            # Expect 12.0 to be the body size (most frequent by char count)
            assert body_size == 12.0

            # Verify Thresholds Logic (Manual Check)
            h1 = body_size * 1.6
            assert h1 < 24.0, "Heading (24) should be detected as H1 (> 19.2)"
        except Exception as e:
            print(f"TEST ERROR: {e}")
            import traceback

            traceback.print_exc()
            raise e

    def test_latex_comment_stripping(self):
        """Test that % comments are removed but \\% is kept."""
        parser = TexParser()

        latex_input = r"""
        \section{Introduction} % This is a comment
        This is visible text.
        We have a 50\% increase. % Another comment
        % A full line comment
        \textbf{End}
        """

        cleaned = parser._remove_comments(latex_input)
        cleaned_stripped = cleaned.strip()

        logger.info(f"Cleaned LaTeX:\n{cleaned_stripped}")

        assert "This is a comment" not in cleaned
        assert "Another comment" not in cleaned
        assert "50\\% increase" in cleaned
        assert "This is visible text" in cleaned

    def test_txt_strict_list_logic(self):
        """Test strict numbered list detection."""
        parser = TxtParser()

        # Input with tricky cases
        content = """
1. First item
2. Second item
1999. The year (should NOT be a list item)
10. Tenth item
a) Letter item
        """

        blocks = parser._extract_blocks(content)

        for b in blocks:
            logger.info(f"Block: '{b.text[:20]}...' | List? {b.metadata.get('is_list_item')}")

            if "1. First" in b.text:
                assert b.metadata.get("is_list_item")
            if "1999." in b.text:
                assert not b.metadata.get("is_list_item"), "Year should not be list item"
            if "10. Tenth" in b.text:
                assert b.metadata.get("is_list_item")
            if "a) Letter" in b.text:
                assert b.metadata.get("is_list_item")


if __name__ == "__main__":
    import traceback

    try:
        # Manually run tests to control output
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRiskMitigation)
        # Use a stream that writes to sys.stdout
        runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
        result = runner.run(suite)
        if not result.wasSuccessful():
            sys.exit(1)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
