# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import unittest
import sys
import os
from unittest.mock import patch

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Parsing imports with availability flags
MD_AVAILABLE = False
try:
    from app.pipeline.parsing.md_parser import MarkdownParser
    from app.models import BlockType
    MD_AVAILABLE = True
except ImportError:
    pass

PDF_AVAILABLE = False
try:
    from app.pipeline.parsing.pdf_parser import PdfParser
    PDF_AVAILABLE = True
except ImportError:
    pass

HTML_AVAILABLE = False
try:
    from app.pipeline.parsing.html_parser import HtmlParser
    from bs4 import BeautifulSoup
    HTML_AVAILABLE = True
except ImportError:
    pass

class TestRealWorldFeatures(unittest.TestCase):
    
    @unittest.skipUnless(MD_AVAILABLE, "MarkdownParser not available")
    def test_markdown_math_protection(self):
        """Test that Math $...$ is preserved during stripping."""
        parser = MarkdownParser()
        text = "Equation is $E=mc^2$."
        cleaned = parser._strip_markdown(text)
        print(f"DEBUG MATH: '{cleaned}'")
        self.assertEqual(cleaned, "Equation is $E=mc^2$.")
        
        text_block = "Block equation: $$x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}$$"
        cleaned_block = parser._strip_markdown(text_block)
        self.assertEqual(cleaned_block, text_block)

    @unittest.skipUnless(MD_AVAILABLE, "MarkdownParser not available")
    def test_markdown_strikethrough(self):
        """Test that Strikethrough ~~...~~ is stripped."""
        parser = MarkdownParser()
        text = "This is ~~struck~~ text."
        cleaned = parser._strip_markdown(text)
        self.assertEqual(cleaned, "This is struck text.")

    @unittest.skipUnless(MD_AVAILABLE, "MarkdownParser not available")
    def test_markdown_footnotes(self):
        """Test Footnote extraction."""
        parser = MarkdownParser()
        content = """
Introduction.
[^1]: This is a footnote.
        """
        blocks, _ = parser._extract_content(content)
        
        # Check for Footnote block
        footnote_blocks = [b for b in blocks if b.block_type == BlockType.FOOTNOTE]
        self.assertTrue(len(footnote_blocks) > 0, "No footnote blocks found")
        self.assertTrue("This is a footnote" in footnote_blocks[0].text)

    @unittest.skipUnless(PDF_AVAILABLE, "PdfParser not available")
    def test_pdf_header_footer_logic(self):
        """Test the _is_header_footer heuristic."""
        # Patch PYMUPDF_AVAILABLE
        with patch('app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE', True):
            parser = PdfParser()
            page_rect = [0, 0, 100, 1000] # 100x1000 page
            
            # Top 7% = 70px. Bottom 7% = 70px (from bottom). y > 930.
            
            # Header block (y1=50 <= 70) -> TRUE
            self.assertTrue(parser._is_header_footer([10, 10, 90, 50], page_rect))
            
            # Footer block (y0=950 >= 930) -> TRUE
            self.assertTrue(parser._is_header_footer([10, 950, 90, 990], page_rect))
            
            # Body block (y=[200, 300]) -> FALSE
            self.assertFalse(parser._is_header_footer([10, 200, 90, 300], page_rect))

    @unittest.skipUnless(HTML_AVAILABLE, "HtmlParser not available")
    def test_html_script_cleaning(self):
        """Test that <script> and <style> tags are removed."""
        with patch('app.pipeline.parsing.html_parser.BS4_AVAILABLE', True):
            parser = HtmlParser()
            html_content = """
            <html>
                <head>
                    <style>body { color: red; }</style>
                </head>
                <body>
                    <p>Clean text.</p>
                    <script>alert('XSS');</script>
                </body>
            </html>
            """
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Call internal method to process soup
            parser._extract_content(soup)
            
            # Check script/style removal
            self.assertEqual(len(soup.find_all('script')), 0)
            self.assertEqual(len(soup.find_all('style')), 0)
            
            # Check content extraction (indirectly, just ensure it didn't crash)
            # Currently _extract_content returns lists, but modifies soup in-place? 
            # Yes, decompose() modifies the soup tree in-place.

if __name__ == '__main__':
    unittest.main(verbosity=2)
