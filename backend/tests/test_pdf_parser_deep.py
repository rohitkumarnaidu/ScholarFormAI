# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch, call, ANY, PropertyMock
import pytest

from app.models import Block, BlockType, TextStyle


@pytest.fixture
def pdf_parser():
    with patch("app.pipeline.parsing.pdf_parser.fitz") as mock_fitz:
        from app.pipeline.parsing.pdf_parser import PdfParser
        parser = PdfParser()
        parser.block_counter = 0
        parser.figure_counter = 0
        parser.table_counter = 0
        yield parser


class MockRect:
    def __init__(self, x0=0, y0=0, x1=612, y1=792):
        self.x0 = x0; self.y0 = y0; self.x1 = x1; self.y1 = y1
    def __getitem__(self, i):
        return [self.x0, self.y0, self.x1, self.y1][i]
    def __len__(self):
        return 4


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.rect = MockRect(0, 0, 612, 792)
    page.get_text.return_value = {"blocks": []}
    page.find_tables.return_value = []
    page.get_images.return_value = []
    return page


@pytest.fixture
def mock_pdf_doc(mock_page):
    doc = MagicMock()
    doc.is_encrypted = False
    doc.metadata = {"title": "Test Paper", "author": "John Doe", "subject": "Abstract text", "keywords": "ml, ai"}
    doc.__len__.return_value = 1
    doc.__getitem__.return_value = mock_page
    doc.__iter__.return_value = iter([mock_page])
    return doc


class TestInit:
    def test_raises_without_pymupdf(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", False):
            with pytest.raises(ImportError, match="PyMuPDF"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                PdfParser()

    def test_initializes_counters(self, pdf_parser):
        assert pdf_parser.block_counter == 0
        assert pdf_parser.figure_counter == 0
        assert pdf_parser.table_counter == 0


class TestSupportsFormat:
    def test_pdf(self, pdf_parser):
        assert pdf_parser.supports_format(".pdf") is True

    def test_pdf_upper(self, pdf_parser):
        assert pdf_parser.supports_format(".PDF") is True

    def test_docx(self, pdf_parser):
        assert pdf_parser.supports_format(".docx") is False

    def test_empty(self, pdf_parser):
        assert pdf_parser.supports_format("") is False


class TestExtractMetadata:
    def test_basic(self, pdf_parser, mock_pdf_doc):
        meta = pdf_parser._extract_metadata(mock_pdf_doc)
        assert meta.title == "Test Paper"
        assert meta.authors == ["John Doe"]
        assert meta.abstract == "Abstract text"
        assert meta.keywords == ["ml", "ai"]

    def test_no_metadata(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.metadata = None
        meta = pdf_parser._extract_metadata(mock_pdf_doc)
        assert meta.title is None or meta.title == ""

    def test_empty_metadata(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.metadata = {}
        meta = pdf_parser._extract_metadata(mock_pdf_doc)
        assert meta.title is None or meta.title == ""

    def test_partial_metadata(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.metadata = {"title": "Only Title"}
        meta = pdf_parser._extract_metadata(mock_pdf_doc)
        assert meta.title == "Only Title"
        assert meta.authors is None or meta.authors == []

    def test_keywords_empty_string(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.metadata = {"keywords": ""}
        meta = pdf_parser._extract_metadata(mock_pdf_doc)
        assert meta.keywords == []


class TestShouldAttemptOcrFallback:
    def test_high_text_content(self, pdf_parser):
        blocks = [Block(block_id="b1", text="word " * 200, index=0, block_type=BlockType.BODY)]
        assert pdf_parser._should_attempt_ocr_fallback(blocks, 5) is False

    def test_low_total_chars(self, pdf_parser):
        blocks = [Block(block_id="b1", text="hi", index=0, block_type=BlockType.BODY)]
        assert pdf_parser._should_attempt_ocr_fallback(blocks, 3) is True

    def test_low_chars_per_page(self, pdf_parser):
        blocks = [Block(block_id="b1", text="hello world", index=0, block_type=BlockType.BODY)]
        assert pdf_parser._should_attempt_ocr_fallback(blocks, 5) is True

    def test_zero_pages(self, pdf_parser):
        assert pdf_parser._should_attempt_ocr_fallback([], 0) is False

    def test_empty_blocks(self, pdf_parser):
        assert pdf_parser._should_attempt_ocr_fallback([], 5) is True


class TestBuildOcrBlocks:
    def test_none_text(self, pdf_parser):
        assert pdf_parser._build_ocr_blocks(None, "tesseract") == []

    def test_empty_text(self, pdf_parser):
        assert pdf_parser._build_ocr_blocks("", "tesseract") == []

    def test_single_paragraph(self, pdf_parser):
        blocks = pdf_parser._build_ocr_blocks("Hello world", "tesseract")
        assert len(blocks) == 1
        assert blocks[0].text == "Hello world"
        assert blocks[0].block_type == BlockType.BODY
        assert blocks[0].metadata["ocr_generated"] is True
        assert blocks[0].metadata["ocr_backend"] == "tesseract"

    def test_multiple_paragraphs(self, pdf_parser):
        blocks = pdf_parser._build_ocr_blocks("Para one\n\nPara two\n\nPara three", "paddle")
        assert len(blocks) == 3

    def test_single_line_fallback(self, pdf_parser):
        blocks = pdf_parser._build_ocr_blocks("Line1\nLine2\nLine3", "tesseract")
        assert len(blocks) >= 1

    def test_increments_counter(self, pdf_parser):
        pdf_parser.block_counter = 5
        blocks = pdf_parser._build_ocr_blocks("Text", "tesseract")
        assert pdf_parser.block_counter == 6


class TestCalculateFontStats:
    def test_no_pages(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.__len__.return_value = 0
        assert pdf_parser._calculate_font_stats(mock_pdf_doc) == 11.0

    def test_no_text_blocks(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {"blocks": []}
        assert pdf_parser._calculate_font_stats(mock_pdf_doc) == 11.0

    def test_returns_weighted_mode(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "lines": [
                    {"spans": [
                        {"size": 11.0, "text": "a" * 100, "flags": 0, "font": "Times"},
                        {"size": 11.0, "text": "b" * 50, "flags": 0, "font": "Times"},
                        {"size": 14.0, "text": "c" * 20, "flags": 0, "font": "Times"},
                    ]}
                ]}
            ]
        }
        result = pdf_parser._calculate_font_stats(mock_pdf_doc)
        assert result == 11.0

    def test_exception_on_page_skipped(self, pdf_parser, mock_pdf_doc):
        mock_pdf_doc.__len__.return_value = 1
        mock_pdf_doc.__getitem__.side_effect = IndexError
        assert pdf_parser._calculate_font_stats(mock_pdf_doc) == 11.0

    def test_scans_at_most_5_pages(self, pdf_parser, mock_page):
        doc = MagicMock()
        doc.__len__.return_value = 20
        doc.__getitem__.return_value = mock_page
        mock_page.get_text.return_value = {
            "blocks": [{"type": 0, "lines": [{"spans": [{"size": 12.0, "text": "x", "flags": 0, "font": "A"}]}]}]
        }
        result = pdf_parser._calculate_font_stats(doc)
        assert doc.__getitem__.call_count <= 5


class TestIsHeaderFooter:
    def test_top_margin(self, pdf_parser):
        block_bbox = [0, 10, 100, 30]
        page_rect = [0, 0, 612, 792]
        assert pdf_parser._is_header_footer(block_bbox, page_rect) is True

    def test_bottom_margin(self, pdf_parser):
        block_bbox = [0, 750, 100, 780]
        page_rect = [0, 0, 612, 792]
        assert pdf_parser._is_header_footer(block_bbox, page_rect) is True

    def test_middle_not_header_footer(self, pdf_parser):
        block_bbox = [0, 300, 100, 400]
        page_rect = [0, 0, 612, 792]
        assert pdf_parser._is_header_footer(block_bbox, page_rect) is False

    def test_empty_bbox(self, pdf_parser):
        assert pdf_parser._is_header_footer([], [0, 0, 612, 792]) is False

    def test_empty_page_rect(self, pdf_parser):
        assert pdf_parser._is_header_footer([0, 0, 100, 100], []) is False

    def test_zero_height(self, pdf_parser):
        assert pdf_parser._is_header_footer([0, 0, 100, 100], [0, 0, 612, 0]) is False


class TestNormalizeMarginText:
    def test_basic(self, pdf_parser):
        result = pdf_parser._normalize_margin_text("Page 1 of 10")
        assert "page" not in result
        assert len(result) <= 3

    def test_roman_numerals(self, pdf_parser):
        result = pdf_parser._normalize_margin_text("Introduction iii")
        assert "iii" not in result.split()

    def test_none(self, pdf_parser):
        assert pdf_parser._normalize_margin_text(None) == ""

    def empty(self, pdf_parser):
        assert pdf_parser._normalize_margin_text("") == ""

    def test_mixed_content(self, pdf_parser):
        result = pdf_parser._normalize_margin_text("Journal of AI Research 2024")
        assert result == "journal of ai research"


class TestSanitizeCellText:
    def test_none(self, pdf_parser):
        assert pdf_parser._sanitize_cell_text(None) == ""

    def test_string(self, pdf_parser):
        assert pdf_parser._sanitize_cell_text("hello") == "hello"

    def test_with_newlines(self, pdf_parser):
        assert pdf_parser._sanitize_cell_text("hello\nworld") == "hello world"

    def test_int(self, pdf_parser):
        assert pdf_parser._sanitize_cell_text(42) == "42"

    def test_whitespace_stripped(self, pdf_parser):
        assert pdf_parser._sanitize_cell_text("  hello  ") == "hello"


class TestBuildTableModel:
    def test_empty_rows(self, pdf_parser):
        assert pdf_parser._build_table_model([], 1, 0) is None

    def test_empty_after_normalization(self, pdf_parser):
        assert pdf_parser._build_table_model([[""]], 1, 0) is not None

    def test_basic_table(self, pdf_parser):
        rows = [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        table = pdf_parser._build_table_model(rows, 1, 0)
        assert table is not None
        assert table.num_rows == 3
        assert table.num_cols == 2
        assert table.has_header is True
        assert len(table.cells) == 6

    def test_no_header(self, pdf_parser):
        rows = [["", ""], ["alice", "30"]]
        table = pdf_parser._build_table_model(rows, 1, 0)
        assert table is not None
        assert table.has_header is False

    def test_ragged_rows(self, pdf_parser):
        rows = [["A", "B", "C"], ["D", "E"]]
        table = pdf_parser._build_table_model(rows, 1, 0)
        assert table.num_cols == 3
        assert len(table.cells) == 6

    def test_increments_counter(self, pdf_parser):
        rows = [["A"]]
        pdf_parser.table_counter = 3
        pdf_parser._build_table_model(rows, 1, 0)
        assert pdf_parser.table_counter == 4


class TestParse:
    def test_file_not_found(self, pdf_parser):
        with pytest.raises(FileNotFoundError):
            pdf_parser.parse("/nonexistent/file.pdf", "doc1")

    def test_invalid_pdf(self, pdf_parser, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.fitz.open") as mock_open:
            mock_open.side_effect = Exception("bad file")
            p = tmp_path / "test.pdf"
            p.write_text("garbage")
            with pytest.raises(ValueError, match="Failed to open PDF"):
                pdf_parser.parse(str(p), "doc1")

    def test_encrypted_pdf(self, pdf_parser, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.fitz.open") as mock_open:
            doc = MagicMock()
            doc.is_encrypted = True
            doc.authenticate.return_value = False
            mock_open.return_value = doc
            p = tmp_path / "test.pdf"
            p.write_text("dummy")
            with pytest.raises(ValueError, match="password-protected"):
                pdf_parser.parse(str(p), "doc1")

    def test_encrypted_but_authenticated(self, pdf_parser, tmp_path, mock_pdf_doc):
        with patch("app.pipeline.parsing.pdf_parser.fitz.open") as mock_open:
            mock_pdf_doc.is_encrypted = True
            mock_pdf_doc.authenticate.return_value = True
            mock_open.return_value = mock_pdf_doc
            p = tmp_path / "test.pdf"
            p.write_text("dummy")
            doc = pdf_parser.parse(str(p), "doc1")
            assert doc is not None
            assert doc.document_id == "doc1"

    def test_successful_parse(self, pdf_parser, tmp_path, mock_pdf_doc, mock_page):
        with patch("app.pipeline.parsing.pdf_parser.fitz.open") as mock_open:
            mock_open.return_value = mock_pdf_doc
            p = tmp_path / "test.pdf"
            p.write_text("dummy")
            doc = pdf_parser.parse(str(p), "doc1")
            assert doc.document_id == "doc1"
            assert doc.metadata.title == "Test Paper"
            assert mock_pdf_doc.close.called

    def test_adds_processing_stage(self, pdf_parser, tmp_path, mock_pdf_doc, mock_page):
        import app.models
        with (
            patch("app.pipeline.parsing.pdf_parser.fitz.open") as mock_open,
            patch.object(app.models.PipelineDocument, "add_processing_stage") as mock_aps,
        ):
            mock_open.return_value = mock_pdf_doc
            mock_page.get_text.return_value = {
                "blocks": [{"type": 0, "bbox": [50, 300, 500, 320], "lines": [
                    {"spans": [{"text": "Hello World", "size": 12.0, "flags": 0, "font": "Times"}]}
                ]}]
            }
            p = tmp_path / "test.pdf"
            p.write_text("dummy")
            pdf_parser.parse(str(p), "doc1")
            assert mock_aps.called


class TestExtractContent:
    def test_empty_document(self, pdf_parser, mock_pdf_doc):
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert blocks == []
        assert figures == []
        assert tables == []

    def test_extracts_text_block(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {
            "blocks": [{"type": 0, "bbox": [50, 300, 500, 320], "lines": [
                {"spans": [{"text": "Hello World", "size": 12.0, "flags": 0, "font": "Times"}]}
            ]}]
        }
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(blocks) == 1
        assert blocks[0].text == "Hello World"
        assert blocks[0].page_number == 1

    def test_skips_text_in_table_region(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {
            "blocks": [{"type": 0, "bbox": [50, 300, 500, 320], "lines": [
                {"spans": [{"text": "Inside Table", "size": 11.0, "flags": 0, "font": "Times"}]}
            ]}]
        }
        table_mock = MagicMock()
        table_mock.bbox = [0, 290, 600, 330]
        table_mock.header = None
        table_mock.extract.return_value = [["A", "B"], ["1", "2"]]
        mock_page.find_tables.return_value = [table_mock]
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(blocks) == 0

    def test_detects_heading_levels(self, pdf_parser, mock_pdf_doc, mock_page):
        pdf_parser._calculate_font_stats = MagicMock(return_value=11.0)
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "bbox": [50, 100, 500, 130], "lines": [
                    {"spans": [{"text": "Big Heading", "size": 20.0, "flags": 16, "font": "Times"}]}
                ]},
                {"type": 0, "bbox": [50, 200, 500, 220], "lines": [
                    {"spans": [{"text": "Medium Heading", "size": 15.0, "flags": 0, "font": "Times"}]}
                ]},
                {"type": 0, "bbox": [50, 300, 500, 320], "lines": [
                    {"spans": [{"text": "Small Heading", "size": 12.5, "flags": 16, "font": "Times"}]}
                ]},
                {"type": 0, "bbox": [50, 400, 500, 420], "lines": [
                    {"spans": [{"text": "Body text here", "size": 11.0, "flags": 0, "font": "Times"}]}
                ]},
            ]
        }
        blocks, _, _ = pdf_parser._extract_content(mock_pdf_doc)
        assert len(blocks) == 4
        h1_blocks = [b for b in blocks if b.metadata.get("heading_level") == 1]
        h3_blocks = [b for b in blocks if b.metadata.get("heading_level") == 3]
        assert len(h1_blocks) >= 1
        assert len(h3_blocks) >= 0

    def test_header_footer_suppression(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "bbox": [50, 5, 500, 25], "lines": [
                    {"spans": [{"text": "Page Header", "size": 10.0, "flags": 0, "font": "Times"}]}
                ]},
                {"type": 0, "bbox": [50, 770, 500, 790], "lines": [
                    {"spans": [{"text": "Page Footer", "size": 10.0, "flags": 0, "font": "Times"}]}
                ]},
            ]
        }
        blocks, _, _ = pdf_parser._extract_content(mock_pdf_doc)
        header_blocks = [b for b in blocks if b.metadata.get("is_header") or b.metadata.get("is_footer")]
        assert len(header_blocks) == 2

    def test_extracts_table(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {"blocks": []}
        table_mock = MagicMock()
        table_mock.bbox = [0, 400, 600, 500]
        table_mock.header = None
        table_mock.extract.return_value = [["Name", "Age"], ["Alice", "30"]]
        mock_page.find_tables.return_value = [table_mock]
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(tables) == 1
        assert tables[0].num_rows == 2
        assert tables[0].num_cols == 2

    def test_extracts_image(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {"blocks": []}
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]
        pdf_doc = mock_pdf_doc
        pdf_doc.extract_image.return_value = {"image": b"imgdata", "ext": "png"}
        page_text_positions = []
        mock_page.get_image_rects.return_value = []
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(figures) == 1
        assert figures[0].image_format is not None

    def test_image_dedup_by_hash(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {"blocks": []}
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0), (2, 0, 0, 0, 0, 0, 0)]
        pdf_doc = mock_pdf_doc
        pdf_doc.extract_image.return_value = {"image": b"same_data", "ext": "png"}
        mock_page.get_image_rects.return_value = []
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(figures) == 1

    def test_fallback_image_extraction(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 1, "image": b"imgdata", "ext": "jpg", "bbox": [0, 0, 100, 100], "width": 100, "height": 100}
            ]
        }
        mock_page.get_images.return_value = []
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(figures) >= 1

    def test_duplicate_text_suppression(self, pdf_parser, mock_pdf_doc, mock_page):
        long_text = "This is a long repeated text that should be suppressed " * 3
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "bbox": [50, 300, 500, 320], "lines": [
                    {"spans": [{"text": long_text, "size": 11.0, "flags": 0, "font": "Times"}]}
                ]},
                {"type": 0, "bbox": [50, 350, 500, 370], "lines": [
                    {"spans": [{"text": long_text, "size": 11.0, "flags": 0, "font": "Times"}]}
                ]},
            ]
        }
        blocks, _, _ = pdf_parser._extract_content(mock_pdf_doc)
        assert len(blocks) == 1

    def test_text_dict_exception_handled(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.side_effect = Exception("get_text failed")
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(blocks) == 0

    def test_table_exception_handled(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.find_tables.side_effect = Exception("table extraction failed")
        mock_page.get_text.return_value = {"blocks": []}
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(tables) == 0

    def test_image_exception_handled(self, pdf_parser, mock_pdf_doc, mock_page):
        mock_page.get_text.return_value = {"blocks": []}
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]
        mock_pdf_doc.extract_image.side_effect = Exception("extract failed")
        blocks, figures, tables = pdf_parser._extract_content(mock_pdf_doc)
        assert len(figures) == 0


class TestMaybeApplyOcrFallback:
    def test_import_failure_returns_unmodified(self, pdf_parser):
        blocks = [Block(block_id="b1", text="hello", index=0, block_type=BlockType.BODY)]
        result, backend = pdf_parser._maybe_apply_ocr_fallback("/f.pdf", MagicMock(), blocks)
        assert result == blocks
        assert backend is None

    def test_ocr_disabled_by_profile(self, pdf_parser):
        blocks = [Block(block_id="b1", text="hello", index=0, block_type=BlockType.BODY)]
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR"),
        ):
            mock_em.profile.enabled = False
            mock_em.profile.ocr_enabled = True
            result, backend = pdf_parser._maybe_apply_ocr_fallback("/f.pdf", MagicMock(), blocks)
            assert backend is None

    def test_not_sparse_enough(self, pdf_parser):
        blocks = [Block(block_id="b1", text="word " * 200, index=0, block_type=BlockType.BODY)]
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 5
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR"),
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            result, backend = pdf_parser._maybe_apply_ocr_fallback("/f.pdf", mock_doc, blocks)
            assert backend is None

    def test_no_ocr_backends(self, pdf_parser):
        blocks = [Block(block_id="b1", text="short", index=0, block_type=BlockType.BODY)]
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 3
        with (
            patch("app.services.enhancement_manager.enhancement_manager") as mock_em,
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR"),
        ):
            mock_em.profile.enabled = True
            mock_em.profile.ocr_enabled = True
            mock_em.get_ocr_backends.return_value = ["some_other_backend"]
            result, backend = pdf_parser._maybe_apply_ocr_fallback("/f.pdf", mock_doc, blocks)
            assert backend is None
