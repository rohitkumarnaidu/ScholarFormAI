# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import MagicMock, patch
from app.pipeline.parsing.pdf_parser import PdfParser

@pytest.fixture
def pdf_parser():
    with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
        with patch("app.pipeline.parsing.pdf_parser.fitz") as mock_fitz:
            yield PdfParser(), mock_fitz

@pytest.fixture
def mock_page():
    page = MagicMock()
    page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
    page.get_text.return_value = {"blocks": []}
    page.get_images.return_value = []
    page.find_tables.return_value = []
    return page

class TestPdfParserInit:
    def test_init_available(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            p = PdfParser()
            assert p.block_counter == 0

    def test_init_unavailable_raises(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", False):
            with pytest.raises(ImportError, match="PyMuPDF"):
                PdfParser()

class TestPdfParserSupportsFormat:
    def test_supports_pdf(self, pdf_parser):
        p, _ = pdf_parser
        assert p.supports_format(".pdf")

    def test_not_supports_other(self, pdf_parser):
        p, _ = pdf_parser
        assert not p.supports_format(".docx")

class TestPdfParserMetadata:
    def test_extract_metadata_with_all_fields(self, pdf_parser):
        p, mf = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.metadata = {
            "title": "Paper Title",
            "author": "John Doe",
            "subject": "A good paper",
            "keywords": "kw1, kw2, kw3",
        }
        meta = p._extract_metadata(pdf_doc)
        assert meta.title == "Paper Title"
        assert meta.authors == ["John Doe"]
        assert "good paper" in meta.abstract
        assert "kw1" in meta.keywords

    def test_extract_metadata_empty(self, pdf_parser):
        p, mf = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.metadata = {}
        meta = p._extract_metadata(pdf_doc)
        assert meta.title is None

    def test_extract_metadata_none(self, pdf_parser):
        p, mf = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.metadata = None
        meta = p._extract_metadata(pdf_doc)
        assert meta.title is None

class TestPdfParserHelpers:
    def test_is_header_footer_top(self, pdf_parser):
        p, _ = pdf_parser
        page_rect = [0, 0, 612, 792]
        assert p._is_header_footer([0, 0, 100, 30], page_rect) is True

    def test_is_header_footer_bottom(self, pdf_parser):
        p, _ = pdf_parser
        page_rect = [0, 0, 612, 792]
        assert p._is_header_footer([0, 760, 100, 792], page_rect) is True

    def test_is_header_footer_middle(self, pdf_parser):
        p, _ = pdf_parser
        page_rect = [0, 0, 612, 792]
        assert p._is_header_footer([0, 200, 100, 300], page_rect) is False

    def test_normalize_margin_text(self, pdf_parser):
        p, _ = pdf_parser
        result = p._normalize_margin_text("Page 1 of 5")
        assert "page" not in result

    def test_sanitize_cell_text(self, pdf_parser):
        p, _ = pdf_parser
        assert p._sanitize_cell_text("hello\nworld") == "hello world"
        assert p._sanitize_cell_text(None) == ""
        assert p._sanitize_cell_text(42) == "42"

    def test_calculate_font_stats_empty(self, pdf_parser):
        p, mf = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        page = MagicMock()
        page.get_text.return_value = {"blocks": []}
        pdf_doc.__getitem__.return_value = page
        result = p._calculate_font_stats(pdf_doc)
        assert result == 11.0

    def test_calculate_font_stats_with_data(self, pdf_parser):
        p, mf = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        page = MagicMock()
        page.get_text.return_value = {
            "blocks": [{
                "type": 0,
                "lines": [{"spans": [{"size": 12.0, "text": "Hello world"}]}],
            }]
        }
        pdf_doc.__getitem__.return_value = page
        result = p._calculate_font_stats(pdf_doc)
        assert result == 12.0

    def test_should_attempt_ocr_fallback_true(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="hi")], 5) is True

    def test_should_attempt_ocr_fallback_false(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        text = "A" * 500
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text=text)], 5) is False

    def test_build_ocr_blocks(self, pdf_parser):
        p, _ = pdf_parser
        blocks = p._build_ocr_blocks("Hello world.\n\nSecond paragraph.", "tesseract")
        assert len(blocks) >= 1
        assert blocks[0].metadata.get("ocr_generated") is True
        assert blocks[0].metadata.get("ocr_backend") == "tesseract"

    def test_build_ocr_blocks_empty(self, pdf_parser):
        p, _ = pdf_parser
        assert p._build_ocr_blocks("", "tesseract") == []
        assert p._build_ocr_blocks("  ", "tesseract") == []

    def test_build_table_model(self, pdf_parser):
        p, _ = pdf_parser
        table = p._build_table_model([["A", "B"], ["1", "2"]], 1, 100)
        assert table is not None
        assert table.num_rows == 2
        assert table.num_cols == 2

    def test_build_table_model_empty(self, pdf_parser):
        p, _ = pdf_parser
        assert p._build_table_model([], 1, 100) is None

class TestPdfParserParse:
    def test_parse_file_not_found(self, pdf_parser):
        p, _ = pdf_parser
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent.pdf", "doc1")

    def test_parse_success(self, tmp_path, mock_page):
        f = tmp_path / "test.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.__getitem__.return_value = mock_page
                pdf_doc.__iter__.return_value = iter([mock_page])
                pdf_doc.metadata = {}
                mf.open.return_value = pdf_doc
                p = PdfParser()
                doc = p.parse(str(f), "doc1")
                assert doc.document_id == "doc1"

    def test_parse_encrypted(self, tmp_path):
        f = tmp_path / "enc.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = True
                pdf_doc.authenticate.return_value = False
                mf.open.return_value = pdf_doc
                p = PdfParser()
                with pytest.raises(ValueError, match="password-protected"):
                    p.parse(str(f), "doc1")

    def test_parse_encrypted_opens_with_password(self, tmp_path, mock_page):
        f = tmp_path / "enc2.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = True
                pdf_doc.authenticate.return_value = True
                pdf_doc.__len__.return_value = 1
                pdf_doc.__getitem__.return_value = mock_page
                pdf_doc.__iter__.return_value = iter([mock_page])
                pdf_doc.metadata = {}
                mf.open.return_value = pdf_doc
                p = PdfParser()
                doc = p.parse(str(f), "doc1")
                assert doc is not None

    def test_parse_extracts_content(self, tmp_path):
        from app.models import Block
        f = tmp_path / "content.pdf"
        f.write_text("dummy")
        test_blocks = [Block(block_id="b1", index=0, text="Hello PDF world")]
        test_figures = []
        test_tables = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_extract_content", return_value=(test_blocks, test_figures, test_tables)):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
                assert len(doc.blocks) >= 1
                assert "Hello" in doc.blocks[0].text

    def test_parse_with_header_footer_suppression(self, tmp_path):
        f = tmp_path / "hf.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 2
                pdf_doc.metadata = {}
                page1 = MagicMock()
                page1.rect = MagicMock()
                page1.rect.x0 = 0; page1.rect.y0 = 0; page1.rect.x1 = 612; page1.rect.y1 = 792
                page1.rect.__getitem__.side_effect = lambda i: [0, 0, 612, 792][i]
                page1.rect.__len__.return_value = 4
                page1.get_text.return_value = {
                    "blocks": [{"type": 0, "bbox": [0, 0, 100, 20], "lines": [{"spans": [{"text": "Header", "size": 10, "flags": 0}]}]}]
                }
                page1.get_images.return_value = []
                page1.find_tables.return_value = []
                page2 = MagicMock()
                page2.rect = MagicMock()
                page2.rect.x0 = 0; page2.rect.y0 = 0; page2.rect.x1 = 612; page2.rect.y1 = 792
                page2.rect.__getitem__.side_effect = lambda i: [0, 0, 612, 792][i]
                page2.rect.__len__.return_value = 4
                page2.get_text.return_value = {
                    "blocks": [{"type": 0, "bbox": [0, 0, 100, 20], "lines": [{"spans": [{"text": "Header", "size": 10, "flags": 0}]}]}]
                }
                page2.get_images.return_value = []
                page2.find_tables.return_value = []
                pdf_doc.__getitem__.side_effect = lambda i: [page1, page2][i]
                pdf_doc.__iter__.return_value = iter([page1, page2])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
                assert len(doc.blocks) >= 1

    def test_parse_with_images(self, tmp_path):
        f = tmp_path / "img.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0, 0)]
                page.find_tables.return_value = []
                pdf_doc.extract_image.return_value = {"image": b"imgdata", "ext": "png"}
                page.get_image_rects.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                mf.open.return_value = pdf_doc
                p = PdfParser()
                doc = p.parse(str(f), "doc1")
                assert len(doc.figures) >= 1

    def test_parse_with_table(self, tmp_path):
        f = tmp_path / "tbl.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = []
                mock_table = MagicMock()
                mock_table.bbox = (100, 200, 300, 400)
                mock_table.extract.return_value = [["A", "B"], ["1", "2"]]
                mock_table.header = MagicMock(names=["A", "B"])
                page.find_tables.return_value = [mock_table]
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                mf.open.return_value = pdf_doc
                p = PdfParser()
                doc = p.parse(str(f), "doc1")
                assert len(doc.tables) >= 1
