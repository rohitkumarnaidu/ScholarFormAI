# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest

from app.pipeline.parsing.txt_parser import TxtParser


@pytest.fixture
def parser():
    return TxtParser()


class TestTxtParserSupportsFormat:
    def test_supports_txt(self, parser):
        assert parser.supports_format(".txt")

    def test_not_supports_other(self, parser):
        assert not parser.supports_format(".pdf")
        assert not parser.supports_format(".docx")


class TestTxtParserParse:
    def test_parse_basic_text(self, parser, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world\n\nSecond paragraph")
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) == 2
        assert doc.blocks[0].text == "Hello world"
        assert doc.blocks[1].text == "Second paragraph"
        assert doc.document_id == "doc1"

    def test_parse_file_not_found(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent.txt", "doc1")

    def test_parse_empty_file(self, parser, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) == 0

    def test_parse_latin1_fallback(self, parser, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes("café résumé".encode("latin-1"))
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) >= 1

    def test_parse_single_line(self, parser, tmp_path):
        f = tmp_path / "single.txt"
        f.write_text("Just one line")
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) == 1

    def test_parse_with_blank_lines(self, parser, tmp_path):
        f = tmp_path / "blank.txt"
        f.write_text("First\n\n\n\nSecond\n\nThird")
        doc = parser.parse(str(f), "doc1")
        assert len(doc.blocks) == 3


class TestTxtParserExtractBlocks:
    def test_detect_all_caps_heading(self, parser):
        blocks = parser._extract_blocks("INTRODUCTION\n\nSome text here")
        assert blocks[0].metadata.get("potential_heading") is True
        assert blocks[0].style.bold is True

    def test_detect_short_no_period_heading(self, parser):
        blocks = parser._extract_blocks("Abstract\n\nThis is the abstract")
        assert blocks[0].metadata.get("potential_heading") is True

    def test_long_sentence_not_heading(self, parser):
        text = "This is a very long sentence that should be considered body text because it ends with a period." * 3
        blocks = parser._extract_blocks(text)
        assert blocks[0].metadata.get("potential_heading") is not True

    def test_bullet_list_detection(self, parser):
        blocks = parser._extract_blocks("- Item one\n\n* Item two\n\n• Item three")
        for blk in blocks:
            assert blk.metadata.get("is_list_item") is True
            assert blk.metadata.get("list_type") == "unordered"

    def test_numbered_list_detection(self, parser):
        blocks = parser._extract_blocks("1. First item\n\n2. Second item")
        for blk in blocks:
            assert blk.metadata.get("is_list_item") is True
            assert blk.metadata.get("list_type") == "ordered"

    def test_numbered_list_years_not_detected(self, parser):
        blocks = parser._extract_blocks("1990. Not a list item")
        assert "is_list_item" not in blocks[0].metadata

    def test_numbered_list_above_99_not_detected(self, parser):
        blocks = parser._extract_blocks("100. Not a list item either")
        assert "is_list_item" not in blocks[0].metadata

    def test_letter_marker_list(self, parser):
        blocks = parser._extract_blocks("a) First letter item\n\nb) Second letter item")
        assert blocks[0].metadata.get("is_list_item") is True

    def test_email_detection(self, parser):
        blocks = parser._extract_blocks("Contact me at user@example.com for info")
        assert blocks[0].metadata.get("contains_email") is True

    def test_url_detection(self, parser):
        blocks = parser._extract_blocks("Visit https://example.com/path for details")
        assert blocks[0].metadata.get("contains_url") is True

    def test_both_email_and_url(self, parser):
        blocks = parser._extract_blocks("Email user@example.com at https://site.com")
        meta = blocks[0].metadata
        assert meta.get("contains_email") is True
        assert meta.get("contains_url") is True

    def test_empty_para_skipped(self, parser):
        blocks = parser._extract_blocks("\n\n  \n\n")
        assert len(blocks) == 0

    def test_block_index_increments(self, parser):
        blocks = parser._extract_blocks("A\n\nB\n\nC")
        indices = [b.index for b in blocks]
        assert indices == sorted(indices)
        assert len(set(indices)) == 3

    def test_paragraph_ending_period_not_heading(self, parser):
        blocks = parser._extract_blocks("This is a complete sentence with a period at the end.")
        assert blocks[0].metadata.get("potential_heading") is not True

    def test_heading_without_period_short(self, parser):
        blocks = parser._extract_blocks("Methods")
        assert blocks[0].metadata.get("potential_heading") is True

    def test_document_id_string_conversion(self, parser, tmp_path):
        f = tmp_path / "id.txt"
        f.write_text("Test")
        from uuid import UUID
        doc = parser.parse(str(f), UUID("12345678-1234-5678-1234-567812345678"))
        assert isinstance(doc.document_id, str)

    def test_supports_format_case_insensitive(self, parser):
        assert parser.supports_format(".TXT")
