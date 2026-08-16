# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def bs4_mocked():
    with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
        with patch("app.pipeline.parsing.html_parser.BeautifulSoup") as mock_bs:
            yield mock_bs


class TestHtmlParserInit:
    def test_import_error_when_bs4_missing(self):
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", False):
            from app.pipeline.parsing.html_parser import HtmlParser

            with pytest.raises(ImportError, match="BeautifulSoup4"):
                HtmlParser()

    def test_init_success(self):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        assert p.block_counter == 0
        assert p.figure_counter == 0


class TestHtmlParserSupportsFormat:
    def test_supports_html(self):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        assert p.supports_format(".html")
        assert p.supports_format(".htm")

    def test_not_supports_other(self):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        assert not p.supports_format(".pdf")


class TestHtmlParserExtractMetadata:
    def test_extract_title(self):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = MagicMock()
        title_tag = MagicMock()
        title_tag.get_text.return_value = "  My Title  "
        soup.find.return_value = title_tag
        meta = p._extract_metadata(soup)
        assert meta.title == "My Title"

    def test_extract_author(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup('<html><head><meta name="author" content="John Doe"></head></html>', "html.parser")
        meta = p._extract_metadata(soup)
        assert meta.authors == ["John Doe"]

    def test_extract_description(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup('<html><head><meta name="description" content="An abstract"></head></html>', "html.parser")
        meta = p._extract_metadata(soup)
        assert meta.abstract == "An abstract"

    def test_extract_keywords(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup('<html><head><meta name="keywords" content="kw1, kw2, kw3"></head></html>', "html.parser")
        meta = p._extract_metadata(soup)
        assert "kw1" in meta.keywords


class TestHtmlParserExtractContent:
    def test_extract_headings(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><h1>Title</h1><h2>Section</h2></body></html>", "html.parser")
        blocks, figures = p._extract_content(soup)
        assert len(blocks) == 2
        assert blocks[0].text == "Title"
        assert blocks[0].metadata["heading_level"] == 1
        assert blocks[1].metadata["heading_level"] == 2

    def test_extract_paragraphs(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        assert len(blocks) == 2
        assert "First" in blocks[0].text

    def test_extract_paragraph_with_bold(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><p><b>Bold text</b> normal</p></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        assert blocks[0].style.bold is True

    def test_extract_paragraph_with_italic(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><p><i>Italic</i> text</p></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        assert blocks[0].style.italic is True

    def test_extract_paragraph_links(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><p>Visit <a href='https://x.com'>X</a></p></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        assert "links" in blocks[0].metadata

    def test_extract_list_items(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><ul><li>Item A</li><li>Item B</li></ul></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        items = [b for b in blocks if b.metadata.get("is_list_item")]
        assert len(items) == 2

    def test_ordered_list(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><ol><li>First</li></ol></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        assert blocks[0].metadata["list_type"] == "ordered"

    def test_extract_code_block(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup(
            '<html><body><code class="language-python">print("hi")</code></body></html>', "html.parser"
        )
        blocks, _ = p._extract_content(soup)
        codes = [b for b in blocks if b.metadata.get("is_code_block")]
        assert len(codes) >= 1
        assert codes[0].metadata["code_language"] == "python"

    def test_extract_table(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><table><tr><td>A</td><td>B</td></tr></table></body></html>", "html.parser")
        blocks, _ = p._extract_content(soup)
        tables = [b for b in blocks if b.metadata.get("is_table")]
        assert len(tables) >= 1

    def test_extract_images(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup("<html><body><img src='img.png' alt='Photo'></body></html>", "html.parser")
        blocks, figures = p._extract_content(soup)
        assert len(figures) == 1
        assert figures[0].caption_text == "Photo"

    def test_script_style_removed(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = BeautifulSoup(
            "<html><body><script>alert('x')</script><p>Text</p><style>.c{}</style></body></html>", "html.parser"
        )
        blocks, _ = p._extract_content(soup)
        assert len(blocks) == 1

    def test_extraction_exception_handled(self, bs4_mocked):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        soup = MagicMock()
        body = MagicMock()
        body.find_all.return_value = [MagicMock(name="bad")]
        soup.find.return_value = body
        blocks, figures = p._extract_content(soup)
        assert len(blocks) == 0


class TestHtmlParserParse:
    def test_parse_full(self, tmp_path):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        f = tmp_path / "test.html"
        f.write_text("<html><body><h1>Title</h1><p>Body</p></body></html>")
        doc = p.parse(str(f), "doc1")
        assert doc.document_id == "doc1"
        assert len(doc.blocks) >= 1

    def test_parse_file_not_found(self):
        from app.pipeline.parsing.html_parser import HtmlParser

        p = HtmlParser()
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent.html", "doc1")
