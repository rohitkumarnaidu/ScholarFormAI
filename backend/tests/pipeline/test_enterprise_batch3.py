# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, ANY
from pathlib import Path
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# parsing/base_parser.py
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseParser:
    def test_cannot_instantiate_abstract(self):
        from app.pipeline.parsing.base_parser import BaseParser
        with pytest.raises(TypeError):
            BaseParser()

    def test_concrete_implementation(self):
        from app.pipeline.parsing.base_parser import BaseParser
        class ConcreteParser(BaseParser):
            def parse(self, file_path, document_id):
                from app.models import PipelineDocument as Document
                return Document(document_id=document_id, created_at=None, updated_at=None)
            def supports_format(self, file_extension):
                return file_extension == ".txt"
        parser = ConcreteParser()
        assert parser.supports_format(".txt") is True
        assert parser.supports_format(".pdf") is False


# ══════════════════════════════════════════════════════════════════════════════
# parsing/txt_parser.py
# ══════════════════════════════════════════════════════════════════════════════

class TestTxtParser:
    def test_supports_format(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        assert p.supports_format(".txt") is True
        assert p.supports_format(".md") is False
        assert p.supports_format("") is False

    def test_extract_blocks_paragraphs(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("First para.\n\nSecond para.\n\nThird para.")
        assert len(blocks) == 3
        assert blocks[0].text == "First para."
        assert blocks[1].text == "Second para."
        assert blocks[2].text == "Third para."

    def test_extract_blocks_empty(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        assert p._extract_blocks("") == []
        assert p._extract_blocks("   ") == []
        assert p._extract_blocks("\n\n\n") == []

    def test_extract_blocks_heading_allcaps(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("INTRODUCTION\n\nThis is the body.")
        assert len(blocks) == 2
        assert blocks[0].metadata.get("potential_heading") is True

    def test_extract_blocks_unordered_list(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("- Item one\n\n- Item two\n\n- Item three")
        assert len(blocks) == 3
        for b in blocks:
            assert b.metadata.get("is_list_item") is True
            assert b.metadata.get("list_type") == "unordered"

    def test_extract_blocks_ordered_list(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("1. First\n\n2. Second\n\n3. Third")
        assert len(blocks) == 3
        for b in blocks:
            assert b.metadata.get("is_list_item") is True
            assert b.metadata.get("list_type") == "ordered"

    def test_extract_blocks_email_detection(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("Contact author@example.com for info.")
        assert len(blocks) == 1
        assert blocks[0].metadata.get("contains_email") is True

    def test_extract_blocks_url_detection(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("Visit https://example.com/page for details.")
        assert len(blocks) == 1
        assert blocks[0].metadata.get("contains_url") is True

    def test_parse_file_not_found(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent/file.txt", "doc123")

    def test_parse_success(self, tmp_path):
        from app.pipeline.parsing.txt_parser import TxtParser
        f = tmp_path / "test.txt"
        f.write_text("Hello world.\n\nSecond para.", encoding="utf-8")
        p = TxtParser()
        doc = p.parse(str(f), "doc123")
        assert doc.document_id == "doc123"
        assert len(doc.blocks) == 2
        assert doc.blocks[0].text == "Hello world."


# ══════════════════════════════════════════════════════════════════════════════
# parsing/parser_factory.py
# ══════════════════════════════════════════════════════════════════════════════

class TestParserFactory:
    def test_get_parser_txt(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        parser = f.get_parser("doc.txt")
        assert parser is not None
        assert parser.supports_format(".txt")

    def test_get_parser_html(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        if f.get_parser("doc.html"):
            assert f.get_parser("doc.html").supports_format(".html")

    def test_get_parser_md(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        parser = f.get_parser("doc.md")
        assert parser is not None
        assert parser.supports_format(".md")

    def test_get_parser_tex(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        parser = f.get_parser("doc.tex")
        assert parser is not None
        assert parser.supports_format(".tex")

    def test_get_parser_unsupported(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        result = f.get_parser("doc.xyz")
        assert result is None

    def test_get_supported_formats(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        formats = f.get_supported_formats()
        assert ".txt" in formats
        assert isinstance(formats, list)

    def test_get_parser_docx(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        parser = f.get_parser("manuscript.docx")
        assert parser is not None

    def test_get_parser_pdf(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        f = ParserFactory()
        try:
            parser = f.get_parser("paper.pdf")
            assert parser is not None
        except ValueError:
            pass  # PDF parser may be unavailable without PyMuPDF


# ══════════════════════════════════════════════════════════════════════════════
# parsing/normalizer.py
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizer:
    def test_process_empty_document(self):
        from app.pipeline.normalization.normalizer import Normalizer
        doc = MagicMock()
        doc.blocks = []
        doc.tables = []
        doc.metadata = MagicMock()
        doc.metadata.title = None
        doc.metadata.authors = []
        doc.metadata.affiliations = []
        doc.metadata.abstract = None
        doc.metadata.keywords = []
        doc.metadata.journal = None
        doc.metadata.corresponding_author = None
        doc.metadata.email = None
        result = Normalizer().process(doc)
        assert result is doc

    def test_normalize_metadata_title(self):
        from app.pipeline.normalization.normalizer import Normalizer
        meta = MagicMock()
        meta.title = "  Hello World  "
        meta.authors = []
        meta.affiliations = []
        meta.abstract = None
        meta.keywords = []
        meta.journal = None
        meta.corresponding_author = None
        meta.email = None
        with patch("app.pipeline.normalization.normalizer.clean_metadata_field", return_value="Hello World"):
            result = Normalizer()._normalize_metadata(meta)
            assert result.title == "Hello World"

    def test_normalize_metadata_none_title(self):
        from app.pipeline.normalization.normalizer import Normalizer
        meta = MagicMock()
        meta.title = None
        meta.authors = []
        meta.affiliations = []
        meta.abstract = None
        meta.keywords = []
        meta.journal = None
        meta.corresponding_author = None
        meta.email = None
        result = Normalizer()._normalize_metadata(meta)
        assert result is meta

    def test_repair_common_corruptions(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("2ethodology") == "2 Methodology"
        assert n._repair_common_corruptions("3esults") == "3 Results"
        assert n._repair_common_corruptions("4iscussion") == "4 Discussion"
        assert n._repair_common_corruptions("5onclusion") == "5 Conclusion"
        assert n._repair_common_corruptions("6eferences") == "6 References"
        assert n._repair_common_corruptions("7ntroduction") == "7 Introduction"
        assert n._repair_common_corruptions("8bstract") == "8 Abstract"

    def test_repair_no_change(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("Normal text here") == "Normal text here"
        assert n._repair_common_corruptions("") == ""
        assert n._repair_common_corruptions(None) is None

    def test_sanitize_empty_orphan_blocks(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import BlockType
        n = Normalizer()
        b = MagicMock()
        type(b).text = PropertyMock(return_value="")
        b.block_type = BlockType.UNKNOWN
        b.metadata = {}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 0

    def test_sanitize_empty_orphan_with_anchor_kept(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import BlockType
        n = Normalizer()
        b = MagicMock()
        type(b).text = PropertyMock(return_value="")
        b.block_type = BlockType.BODY
        b.metadata = {"figure_anchor": True}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_calculate_median_font_size(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b1 = MagicMock()
        b1.style.font_size = 12
        b1.text.strip.return_value = "text"
        b2 = MagicMock()
        b2.style.font_size = 14
        b2.text.strip.return_value = "more"
        result = n._calculate_median_font_size([b1, b2])
        assert result == 13.0

    def test_calculate_median_font_size_empty(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._calculate_median_font_size([]) is None

    def test_normalize_blocks_abstract_split(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import BlockType
        n = Normalizer()
        b = MagicMock()
        type(b).text = PropertyMock(return_value="AbstractThis is the abstract content.")
        b.index = 100
        b.block_id = "block0"
        b.block_type = BlockType.UNKNOWN
        b.style.bold = False
        b.style.font_size = None
        b.metadata = {}
        b.model_copy = lambda **kw: MagicMock(text=kw.get("update", {}).get("text", b.text), index=b.index, block_id=kw.get("update", {}).get("block_id", b.block_id), style=b.style, metadata=b.metadata)
        with patch("app.pipeline.normalization.normalizer.normalize_block_text", side_effect=lambda x, **kw: x):
            result = n._normalize_blocks([b])
            assert len(result) >= 1

    def test_normalize_blocks_consecutive_duplicate(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import BlockType
        from unittest.mock import PropertyMock
        n = Normalizer()
        shared_style = MagicMock()
        shared_style.bold = False
        shared_style.font_size = None
        b1 = MagicMock()
        type(b1).text = PropertyMock(return_value="Hello")
        b1.index = 100
        b1.block_id = "b1"
        b1.block_type = BlockType.UNKNOWN
        b1.style = shared_style
        b1.metadata = {}
        b1.warnings = []
        b1.model_copy = lambda **kw: MagicMock(text=kw.get("update", {}).get("text", "Hello"), index=b1.index, style=shared_style, metadata={}, warnings=[])
        b2 = MagicMock()
        type(b2).text = PropertyMock(return_value="Hello")
        b2.index = 200
        b2.block_id = "b2"
        b2.block_type = BlockType.UNKNOWN
        b2.style = shared_style
        b2.metadata = {}
        b2.warnings = []
        b2.model_copy = lambda **kw: MagicMock(text=kw.get("update", {}).get("text", "Hello"), index=b2.index, style=shared_style, metadata={}, warnings=[])
        with patch("app.pipeline.normalization.normalizer.normalize_block_text", side_effect=lambda x, **kw: x):
            result = n._normalize_blocks([b1, b2])
            assert len(result) == 1


# ══════════════════════════════════════════════════════════════════════════════
# parsing/md_parser.py (markdown)
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkdownParser:
    def test_supports_format(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p.supports_format(".md") is True
        assert p.supports_format(".markdown") is True
        assert p.supports_format(".txt") is False

    def test_strip_markdown_bold(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p._strip_markdown("**bold** text") == "bold text"

    def test_strip_markdown_italic(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p._strip_markdown("*italic* text") == "italic text"

    def test_strip_markdown_code(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p._strip_markdown("`code` here") == "code here"

    def test_strip_markdown_links(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p._strip_markdown("[text](http://example.com)") == "text"

    def test_strip_markdown_empty(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        assert p._strip_markdown("") == ""

    def test_parse_file_not_found(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent/file.md", "doc123")


# ══════════════════════════════════════════════════════════════════════════════
# parsing/tex_parser.py (LaTeX)
# ══════════════════════════════════════════════════════════════════════════════

class TestTexParser:
    def test_supports_format(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        assert p.supports_format(".tex") is True
        assert p.supports_format(".latex") is True
        assert p.supports_format(".txt") is False

    def test_remove_comments(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        assert p._remove_comments("Text % comment\nmore") == "Text \nmore"

    def test_remove_comments_escaped(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        result = p._remove_comments(r"Text \% not comment\nmore")
        assert "not comment" in result

    def test_remove_comments_empty(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        assert p._remove_comments("") == ""

    def test_clean_latex_basic(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        result = p._clean_latex(r"\textbf{bold} text")
        assert "bold" in result
        assert "textbf" not in result

    def test_clean_latex_empty(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        assert p._clean_latex("") == ""

    def test_parse_file_not_found(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent/file.tex", "doc123")


# ══════════════════════════════════════════════════════════════════════════════
# parsing/html_parser.py
# ══════════════════════════════════════════════════════════════════════════════

class TestHtmlParser:
    def test_supports_format(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            assert p.supports_format(".html") is True
            assert p.supports_format(".htm") is True
            assert p.supports_format(".txt") is False

    def test_init_raises_without_bs4(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", False):
            with pytest.raises(ImportError):
                HtmlParser()

    def test_extract_metadata(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        from bs4 import BeautifulSoup
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            html = "<html><head><title>Test Title</title><meta name='author' content='Dr. Smith'></head></html>"
            soup = BeautifulSoup(html, "html.parser")
            meta = p._extract_metadata(soup)
            assert meta.title == "Test Title"
            assert "Dr. Smith" in meta.authors

    def test_extract_metadata_abstract(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        from bs4 import BeautifulSoup
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            html = "<html><head><meta name='description' content='Paper abstract'></head></html>"
            soup = BeautifulSoup(html, "html.parser")
            meta = p._extract_metadata(soup)
            assert meta.abstract == "Paper abstract"

    def test_extract_metadata_keywords(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        from bs4 import BeautifulSoup
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            html = "<html><head><meta name='keywords' content='ml, ai, nlp'></head></html>"
            soup = BeautifulSoup(html, "html.parser")
            meta = p._extract_metadata(soup)
            assert "ml" in meta.keywords

    def test_parse_file_not_found(self):
        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            with pytest.raises(FileNotFoundError):
                p.parse("/nonexistent/file.html", "doc123")


# ══════════════════════════════════════════════════════════════════════════════
# parsing/parser.py (DOCX) — standalone utility methods
# ══════════════════════════════════════════════════════════════════════════════

class TestDocxParser:
    def test_supports_format(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        assert p.supports_format(".docx") is True
        assert p.supports_format(".doc") is True
        assert p.supports_format(".pdf") is False

    def test_get_image_format_known(self):
        from app.pipeline.parsing.parser import DocxParser
        from app.models import ImageFormat
        p = DocxParser()
        assert p._get_image_format("image/png") == ImageFormat.PNG
        assert p._get_image_format("image/jpeg") == ImageFormat.JPEG
        assert p._get_image_format("image/gif") == ImageFormat.GIF

    def test_get_image_format_unknown(self):
        from app.pipeline.parsing.parser import DocxParser
        from app.models import ImageFormat
        p = DocxParser()
        assert p._get_image_format("image/webp") == ImageFormat.UNKNOWN
        assert p._get_image_format("") == ImageFormat.UNKNOWN

    def test_normalize_margin_text(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        p = PdfParser()
        assert p._normalize_margin_text("  hello  ") == "hello"
        assert p._normalize_margin_text("") == ""

    def test_sanitize_cell_text(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        p = PdfParser()
        assert p._sanitize_cell_text(" hello ") == "hello"
        assert p._sanitize_cell_text(123) == "123"
        assert p._sanitize_cell_text(None) == ""
