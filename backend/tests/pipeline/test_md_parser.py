# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import re
import pytest
from unittest.mock import MagicMock, patch
from app.pipeline.parsing.md_parser import MarkdownParser
from app.models import DocumentMetadata


@pytest.fixture
def parser():
    return MarkdownParser()


class TestMarkdownParserSupportsFormat:
    def test_supports_md(self, parser):
        assert parser.supports_format(".md")
        assert parser.supports_format(".markdown")

    def test_not_supports_other(self, parser):
        assert not parser.supports_format(".pdf")


class TestMarkdownParserParse:
    def test_parse_simple(self, parser, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nSome paragraph text.")
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) >= 1
        assert doc.document_id == "doc1"

    def test_parse_file_not_found(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent.md", "doc1")

    def test_parse_utf8_fallback(self, parser, tmp_path):
        f = tmp_path / "test.md"
        f.write_bytes("café".encode("latin-1"))
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) >= 1

    def test_parse_read_failure(self, parser, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("dummy")
        with patch("builtins.open", side_effect=PermissionError("denied")):
            with pytest.raises(ValueError, match="Failed to open Markdown"):
                parser.parse(str(f), "doc1")

    def test_parse_with_frontmatter(self, parser, tmp_path):
        f = tmp_path / "front.md"
        f.write_text("---\ntitle: My Paper\nauthor: John Doe\n---\n\n# Hello\nContent.")
        doc = parser.parse(str(f), "doc1")
        assert doc.metadata.title == "My Paper"
        assert doc.metadata.authors == ["John Doe"]

    def test_frontmatter_yields_metadata(self, parser):
        content, meta = parser._extract_frontmatter("---\ntitle: Test\nkeywords: a, b, c\n---\n\nBody")
        assert meta.title == "Test"
        assert meta.keywords == ["a", "b", "c"]
        assert "Body" in content


class TestMarkdownParserExtractContent:
    def test_heading_h1(self, parser):
        blocks, _ = parser._extract_content("# Title")
        assert len(blocks) == 1
        assert blocks[0].metadata["heading_level"] == 1
        assert blocks[0].text == "Title"

    def test_heading_h2(self, parser):
        blocks, _ = parser._extract_content("## Section")
        assert blocks[0].metadata["heading_level"] == 2

    def test_heading_h3(self, parser):
        blocks, _ = parser._extract_content("### Subsection")
        assert blocks[0].metadata["heading_level"] == 3

    def test_paragraph(self, parser):
        blocks, _ = parser._extract_content("A simple paragraph text.")
        assert len(blocks) == 1
        assert blocks[0].text == "A simple paragraph text."

    def test_multiple_paragraphs(self, parser):
        blocks, _ = parser._extract_content("First para.\n\nSecond para.\n\nThird para.")
        assert len(blocks) == 3

    def test_code_block(self, parser):
        blocks, _ = parser._extract_content("```python\nprint('hello')\n```")
        assert len(blocks) == 1
        assert blocks[0].metadata["is_code_block"] is True
        assert blocks[0].metadata["code_language"] == "python"
        assert "print" in blocks[0].text

    def test_code_block_no_language(self, parser):
        blocks, _ = parser._extract_content("```\nplain code\n```")
        assert blocks[0].metadata["code_language"] == "plaintext"

    def test_table(self, parser):
        blocks, _ = parser._extract_content("| A | B |\n| --- | --- |\n| 1 | 2 |")
        assert len(blocks) >= 1
        assert blocks[0].metadata.get("is_table")

    def test_blockquote(self, parser):
        blocks, _ = parser._extract_content("> A wise quote\n> More wisdom")
        assert len(blocks) == 1
        assert blocks[0].metadata.get("is_blockquote") is True
        assert blocks[0].style.italic is True

    def test_horizontal_rule_skipped(self, parser):
        blocks, _ = parser._extract_content("Before\n\n---\n\nAfter")
        assert len(blocks) == 2

    def test_unordered_list_item(self, parser):
        blocks, _ = parser._extract_content("- Item one\n- Item two")
        assert len(blocks) >= 1

    def test_image_extraction(self, parser):
        blocks, figures = parser._extract_content("![Alt text](image.png)")
        assert len(figures) == 1
        assert figures[0].caption_text == "Alt text"
        assert figures[0].metadata["src"] == "image.png"

    def test_image_in_paragraph(self, parser):
        blocks, figures = parser._extract_content("Text with ![img](photo.jpg) inline")
        assert len(figures) == 1

    def test_footnote_definition(self, parser):
        blocks, _ = parser._extract_content("[^1]: Footnote text here")
        assert len(blocks) == 1
        assert "[^1]" in blocks[0].text

    def test_strip_markdown_bold(self, parser):
        result = parser._strip_markdown("**bold** text")
        assert "bold" in result
        assert "**" not in result

    def test_strip_markdown_italic(self, parser):
        result = parser._strip_markdown("*italic* text")
        assert "italic" in result
        assert "*" not in result.strip("*")

    def test_strip_markdown_link(self, parser):
        result = parser._strip_markdown("[link text](https://example.com)")
        assert "link text" in result

    def test_strip_markdown_inline_code(self, parser):
        result = parser._strip_markdown("Use `code` here")
        assert "code" in result
        assert "`" not in result

    def test_strip_markdown_strikethrough(self, parser):
        result = parser._strip_markdown("~~struck~~ text")
        assert "struck" in result

    def test_create_paragraph_block_hyperlinks(self, parser):
        block = parser._create_paragraph_block("Click [here](https://example.com) now")
        assert "here" in block.text
        assert block.metadata.get("hyperlinks") is not None

    def test_create_paragraph_block_footnote_refs(self, parser):
        block = parser._create_paragraph_block("Text[^ref1] and[^ref2]")
        assert block.metadata.get("footnote_refs") == ["ref1", "ref2"]

    def test_block_counter_increments(self, parser):
        parser._extract_content("A\n\nB\n\nC")
        assert parser.block_counter > 0

    def test_frontmatter_with_keywords(self, parser):
        content, meta = parser._extract_frontmatter("---\nkeywords: a, b\n---\n\nBody")
        assert meta.keywords == ["a", "b"]

    def test_frontmatter_malformed_line(self, parser):
        content, meta = parser._extract_frontmatter("---\nbadline\n---\n\nBody")
        assert meta.title is None
