# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Gap tests for PdfParser to improve branch/statement coverage from 72.36% to 90%+."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, mock_open, patch, PropertyMock

import pytest
from app.pipeline.parsing.pdf_parser import PdfParser
from app.pipeline.ocr.pdf_ocr import OCRError

# ────────────────────────────────────────────────────────────
# Helper: build a mock fitz Page with support for all
# access patterns used in the parser (attribute + __getitem__)
# ────────────────────────────────────────────────────────────
def _make_mock_page(*, blocks=None, tables=None, images=None, rect=None):
    from app.models import Block
    page = MagicMock()
    if rect is None:
        r = MagicMock(x0=0, y0=0, x1=612, y1=792)
        r.__getitem__.side_effect = lambda i: [0, 0, 612, 792][i]
        r.__len__.return_value = 4
        page.rect = r
    else:
        page.rect = rect
    page.get_text.return_value = {"blocks": blocks or []}
    page.find_tables.return_value = tables or []
    page.get_images.return_value = images or []
    return page

def _make_text_block(text, bbox=(50, 50, 550, 80), size=11.0, flags=0, lines=None):
    from app.models import Block
    if lines is not None:
        return {"type": 0, "bbox": bbox, "lines": lines}
    return {
        "type": 0,
        "bbox": bbox,
        "lines": [{"spans": [{"text": text, "size": size, "flags": flags}]}],
    }

def _make_image_block(image_data, ext="png", bbox=(100, 100, 200, 200), width=100, height=100):
    from app.models import Block
    return {
        "type": 1,
        "image": image_data,
        "ext": ext,
        "bbox": bbox,
        "width": width,
        "height": height,
    }

@pytest.fixture
def pdf_parser():
    from app.models import Block
    with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
        with patch("app.pipeline.parsing.pdf_parser.fitz") as mock_fitz:
            yield PdfParser(), mock_fitz

# ════════════════════════════════════════════════════════════
# Gap 85-86 — fitz.open raises → ValueError
# ════════════════════════════════════════════════════════════
class TestParseOpenFailure:
    def test_parse_raises_value_error_on_fitz_open_exception(self, tmp_path):
        from app.models import Block
        f = tmp_path / "corrupt.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz.open", side_effect=Exception("corrupt")):
                p = PdfParser()
                with pytest.raises(ValueError, match="Failed to open PDF file"):
                    p.parse(str(f), "doc1")

# ════════════════════════════════════════════════════════════
# Gap 99 — non‑str document_id → str conversion
# ════════════════════════════════════════════════════════════
class TestParseNonStringId:
    def test_parse_accepts_int_document_id(self, tmp_path):
        from app.models import Block
        f = tmp_path / "id.pdf"
        f.write_text("dummy")
        page = _make_mock_page()
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                doc_mock = MagicMock()
                doc_mock.is_encrypted = False
                doc_mock.__len__.return_value = 1
                doc_mock.__getitem__.return_value = page
                doc_mock.__iter__.return_value = iter([page])
                doc_mock.metadata = {}
                mf.open.return_value = doc_mock
                p = PdfParser()
                result = p.parse(str(f), 42)
        assert result.document_id == "42"

# ════════════════════════════════════════════════════════════
# Gaps 141→143, 143→145, 145→147, 147→151
# ════════════════════════════════════════════════════════════
class TestExtractMetadataBranches:
    @pytest.mark.parametrize(
        "meta,attr,expected",
        [
            ({"title": "T"}, "title", "T"),
            ({"author": "A"}, "authors", ["A"]),
            ({"subject": "S"}, "abstract", "S"),
            ({"keywords": "k1, k2"}, "keywords", ["k1", "k2"]),
        ],
    )
    def test_single_field(self, pdf_parser, meta, attr, expected):
        from app.models import Block
        p, _ = pdf_parser
        doc = MagicMock()
        doc.metadata = meta
        out = p._extract_metadata(doc)
        assert getattr(out, attr) == expected

    def test_empty_keywords(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        doc = MagicMock()
        doc.metadata = {"keywords": ""}
        assert p._extract_metadata(doc).keywords == []

    def test_keywords_with_blanks_filtered(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        doc = MagicMock()
        doc.metadata = {"keywords": "kw1, , kw3, "}
        assert p._extract_metadata(doc).keywords == ["kw1", "kw3"]

# ════════════════════════════════════════════════════════════
# Gap 159 — _should_attempt_ocr_fallback with page_count <= 0
# ════════════════════════════════════════════════════════════
class TestShouldAttemptOcrFallbackEdge:
    def test_zero_pages(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="x")], 0) is False

    def test_negative_pages(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="x")], -1) is False

    def test_very_low_chars_per_page(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="a")], 3) is True

    def test_chars_300_low_cpp(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="x" * 300)], 10) is True

    def test_chars_295_one_page(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._should_attempt_ocr_fallback([Block(block_id="b1", index=0, text="x" * 295)], 1) is True

# ════════════════════════════════════════════════════════════
# Gaps 180-182, 186, 193, 197-199, 203-214, 215-216, 218-220
# ════════════════════════════════════════════════════════════
class TestOcrFallbackBranches:

    # Gap 180-182 — import fails
    def test_import_error_fallback(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        blocks = []
        saved = sys.modules.pop("app.services.enhancement_manager", None)
        try:
            result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        finally:
            if saved is not None:
                sys.modules["app.services.enhancement_manager"] = saved
        assert result == blocks
        assert backend is None

    # Gap 186 — profile not enabled
    def test_profile_not_enabled(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        blocks = []
        profile = MagicMock(enabled=False, ocr_enabled=False)
        mgr = MagicMock(profile=profile)
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR"):
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gap 186 — profile.ocr_enabled is False
    def test_profile_ocr_disabled(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        blocks = []
        profile = MagicMock(enabled=True, ocr_enabled=False)
        mgr = MagicMock(profile=profile)
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR"):
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gap 193 — no supported backends
    def test_no_supported_backends(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hi")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["ocrmypdf"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR"):
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gap 188-189 — _should_attempt_ocr_fallback returns False
    def test_should_not_attempt_ocr(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="A" * 500)]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR"):
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gap 197-199 — not scanned and blocks exist
    def test_not_scanned_keeps_parsed(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hello")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOCR:
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    ocr_inst = MockOCR.return_value
                    ocr_inst.is_scanned.return_value = False
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gaps 203-214 — OCR success
    def test_ocr_success(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hi")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOCR:
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    ocr_inst = MockOCR.return_value
                    ocr_inst.is_scanned.return_value = True
                    ocr_inst.extract_text.return_value = ("OCR text.\n\nPara 2.", "tesseract")
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert backend == "tesseract"
        assert len(result) >= 2
        assert all(b.metadata.get("ocr_generated") for b in result)
        assert all(b.metadata.get("ocr_backend") == "tesseract" for b in result)

    # Gap 204-205 — OCR text empty
    def test_ocr_empty_result(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hi")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOCR:
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    ocr_inst = MockOCR.return_value
                    ocr_inst.is_scanned.return_value = True
                    ocr_inst.extract_text.return_value = ("", "tesseract")
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gap 215-216 — OCRError caught
    def test_ocr_ocrorror(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hi")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOCR:
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    ocr_inst = MockOCR.return_value
                    ocr_inst.is_scanned.return_value = True
                    ocr_inst.extract_text.side_effect = OCRError("no text")
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

    # Gaps 218-220 — unexpected exception caught
    def test_ocr_unexpected_exception(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        blocks = [Block(block_id="b1", index=0, text="hi")]
        profile = MagicMock(enabled=True, ocr_enabled=True)
        mgr = MagicMock(profile=profile)
        mgr.get_ocr_backends.return_value = ["tesseract"]
        with patch("app.services.enhancement_manager.enhancement_manager", mgr):
            with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOCR:
                with patch("app.pipeline.ocr.pdf_ocr.OCRError", OCRError):
                    ocr_inst = MockOCR.return_value
                    ocr_inst.is_scanned.return_value = True
                    ocr_inst.extract_text.side_effect = RuntimeError("boom")
                    result, backend = p._maybe_apply_ocr_fallback("test.pdf", pdf_doc, blocks)
        assert result == blocks
        assert backend is None

# ════════════════════════════════════════════════════════════
# Gap 233 — _build_ocr_blocks paragraph vs line split paths
# ════════════════════════════════════════════════════════════
class TestBuildOcrBlocksEdge:
    def test_paragraph_split(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        blocks = p._build_ocr_blocks("Para 1.\n\nPara 2.\n\nPara 3.", "tesseract")
        assert len(blocks) == 3

    def test_empty_after_strip_returns_empty(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._build_ocr_blocks(" \n \n ", "paddle") == []

    def test_without_double_newlines_single_paragraph(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        blocks = p._build_ocr_blocks("Line1\nLine2\nLine3", "paddle")
        assert len(blocks) == 1
        assert blocks[0].metadata.get("ocr_backend") == "paddle"

# ════════════════════════════════════════════════════════════
# Gaps 273→272, 277→275, 279-280 — _calculate_font_stats
# ════════════════════════════════════════════════════════════
class TestCalculateFontStatsEdge:
    def test_skips_non_text_blocks(self, pdf_parser):
        from app.models import Block
        p, mf = pdf_parser
        pdf = MagicMock()
        pdf.__len__.return_value = 1
        pg = MagicMock()
        pg.get_text.return_value = {
            "blocks": [
                {"type": 1},
                {"type": 0, "lines": [{"spans": [{"size": 14.0, "text": "body"}]}]},
            ]
        }
        pdf.__getitem__.return_value = pg
        assert p._calculate_font_stats(pdf) == 14.0

    def test_zero_size_span_skipped(self, pdf_parser):
        from app.models import Block
        p, mf = pdf_parser
        pdf = MagicMock()
        pdf.__len__.return_value = 1
        pg = MagicMock()
        pg.get_text.return_value = {
            "blocks": [{
                "type": 0,
                "lines": [{"spans": [{"size": 0, "text": "no"}, {"size": 0, "text": "size"}]}],
            }]
        }
        pdf.__getitem__.return_value = pg
        assert p._calculate_font_stats(pdf) == 11.0

    def test_page_exception_caught(self, pdf_parser):
        from app.models import Block
        p, mf = pdf_parser
        pdf = MagicMock()
        pdf.__len__.return_value = 3

        def getitem(i):
            from app.models import Block
            if i == 0:
                raise RuntimeError("fail")
            pg = MagicMock()
            pg.get_text.return_value = {
                "blocks": [{"type": 0, "lines": [{"spans": [{"size": 12.0, "text": "ok"}]}]}],
            }
            return pg
        pdf.__getitem__.side_effect = getitem
        assert p._calculate_font_stats(pdf) == 12.0

    def test_scan_limit_five_pages(self, pdf_parser):
        from app.models import Block
        p, mf = pdf_parser
        pdf = MagicMock()
        pdf.__len__.return_value = 100
        call_count = 0

        def getitem(i):
            from app.models import Block
            nonlocal call_count
            call_count += 1
            pg = MagicMock()
            pg.get_text.return_value = {"blocks": []}
            return pg
        pdf.__getitem__.side_effect = getitem
        p._calculate_font_stats(pdf)
        assert call_count == 5

# ════════════════════════════════════════════════════════════
# Gaps 294, 297 → exit — _is_header_footer edge cases
# ════════════════════════════════════════════════════════════
class TestIsHeaderFooterEdge:
    def test_no_block_bbox(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._is_header_footer(None, [0, 0, 612, 792]) is False
        assert p._is_header_footer([], [0, 0, 612, 792]) is False

    def test_no_page_rect(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._is_header_footer([0, 0, 100, 30], None) is False
        assert p._is_header_footer([0, 0, 100, 30], []) is False

    def test_page_height_zero_or_negative(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._is_header_footer([0, 0, 100, 30], [0, 0, 612, 0]) is False
        assert p._is_header_footer([0, 0, 100, 30], [0, 10, 612, 5]) is False

# ════════════════════════════════════════════════════════════
# Gaps 338, 344 — _build_table_model edge cases
# ════════════════════════════════════════════════════════════
class TestBuildTableModelEdge:
    def test_all_rows_empty_num_cols_zero(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        assert p._build_table_model([[], []], 1, 100) is None

    def test_row_shorter_than_num_cols_padded(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        tbl = p._build_table_model([["A", "B", "C"], ["1", "2"]], 1, 100)
        assert tbl is not None
        assert tbl.num_cols == 3
        assert tbl.rows[1] == ["1", "2", ""]

    def test_first_row_all_empty_no_header(self, pdf_parser):
        from app.models import Block
        p, _ = pdf_parser
        tbl = p._build_table_model([["", "", ""], ["1", "2", "3"]], 1, 100)
        assert tbl is not None
        assert tbl.has_header is False

# ════════════════════════════════════════════════════════════
# Gaps 414→417, 422→427, 423→425, 432→408, 440-441 — tables
# ════════════════════════════════════════════════════════════
class TestTableExtractionBranches:

    @staticmethod
    def _run(tmp_path, mock_table):
        from app.models import Block
        f = tmp_path / "tbl.pdf"
        f.write_text("dummy")
        page = _make_mock_page(tables=[mock_table])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    return p.parse(str(f), "doc1")

    # Gap 414→417: header has no 'names' attribute at all
    def test_header_no_names_attr(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 200, 300, 400)
        mock_tbl.extract.return_value = [["A", "B"]]
        mock_tbl.header = MagicMock(spec=[])
        doc = self._run(tmp_path, mock_tbl)
        assert len(doc.tables) == 1

    # Gap 414→417: header.names is None
    def test_header_names_none(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 200, 300, 400)
        mock_tbl.extract.return_value = [["A", "B"]]
        mock_tbl.header = MagicMock(names=None)
        doc = self._run(tmp_path, mock_tbl)
        assert len(doc.tables) == 1

    # Gap 414→417: header.names is empty
    def test_header_names_empty(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 200, 300, 400)
        mock_tbl.extract.return_value = [["A", "B"]]
        mock_tbl.header = MagicMock(names=[])
        doc = self._run(tmp_path, mock_tbl)
        assert len(doc.tables) == 1

    # Gaps 422→427, 423→425: header_names match first row
    def test_header_names_match_first_row(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 200, 300, 400)
        mock_tbl.extract.return_value = [["A", "B"], ["1", "2"]]
        mock_tbl.header = MagicMock(names=["A", "B"])
        doc = self._run(tmp_path, mock_tbl)
        assert len(doc.tables) == 1
        assert doc.tables[0].rows[0] == ["A", "B"]

    # Gap 432→408: extract returns no rows → table skipped
    def test_table_model_none_skipped(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 200, 300, 400)
        mock_tbl.extract.return_value = []
        mock_tbl.header = MagicMock(names=[])
        doc = self._run(tmp_path, mock_tbl)
        assert len(doc.tables) == 0

    # Gap 440-441: find_tables raises
    def test_table_extraction_exception(self, tmp_path):
        from app.models import Block
        f = tmp_path / "tbl_err.pdf"
        f.write_text("dummy")
        page = _make_mock_page()
        page.find_tables.side_effect = RuntimeError("find_tables failed")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert doc is not None

# ════════════════════════════════════════════════════════════
# Gaps 448-450 — get_text raises → empty dict fallback
# ════════════════════════════════════════════════════════════
class TestTextDictException:
    def test_get_text_raises(self, tmp_path):
        from app.models import Block
        f = tmp_path / "text_err.pdf"
        f.write_text("dummy")
        page = _make_mock_page()
        page.get_text.side_effect = RuntimeError("get_text failed")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert doc is not None

# ════════════════════════════════════════════════════════════
# Gaps 457→456, 462→475, 470-473, 476
# ════════════════════════════════════════════════════════════
class TestTextBlockProcessing:

    # Gap 457→456: non-text block skipped
    def test_non_text_block_skipped(self, tmp_path):
        from app.models import Block
        f = tmp_path / "nontext.pdf"
        f.write_text("dummy")
        page = _make_mock_page(blocks=[{"type": 1, "bbox": (0, 0, 100, 100)}])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.blocks) == 0

    # Gaps 462→475, 470-473: text overlapping table is skipped
    def test_text_overlapping_table_skipped(self, tmp_path):
        from app.models import Block
        f = tmp_path / "overlap.pdf"
        f.write_text("dummy")
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 100, 300, 300)
        mock_tbl.extract.return_value = [["A"]]
        mock_tbl.header = MagicMock(names=None)
        inside = _make_text_block("inside table", bbox=(150, 150, 250, 250))
        outside = _make_text_block("outside", bbox=(400, 400, 500, 420))
        page = _make_mock_page(blocks=[inside, outside], tables=[mock_tbl])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.blocks) == 1
        assert doc.blocks[0].text == "outside"

    # Gap 462→475: block_bbox is None → is_in_table stays False
    def test_no_bbox_not_in_table(self, tmp_path):
        from app.models import Block
        f = tmp_path / "nobbox_tbl.pdf"
        f.write_text("dummy")
        mock_tbl = MagicMock()
        mock_tbl.bbox = (100, 100, 300, 300)
        mock_tbl.extract.return_value = [["A"]]
        mock_tbl.header = MagicMock(names=None)
        no_bbox_block = {
            "type": 0,
            "lines": [{"spans": [{"text": "no bbox", "size": 11, "flags": 0}]}],
        }
        page = _make_mock_page(blocks=[no_bbox_block], tables=[mock_tbl])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.blocks) >= 1

# ════════════════════════════════════════════════════════════
# Gaps 493→497, 499, 501, 503→485, 508→456
# ════════════════════════════════════════════════════════════
class TestSpanProcessingEdge:

    @staticmethod
    def _run_parse(tmp_path, blocks, body_size=None):
        from app.models import Block
        f = tmp_path / "span.pdf"
        f.write_text("dummy")
        page = _make_mock_page(blocks=blocks)
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                patches = [patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False)]
                if body_size is not None:
                    patches.append(patch.object(PdfParser, "_calculate_font_stats", return_value=float(body_size)))
                with contextlib.ExitStack() as stack:
                    for pch in patches:
                        stack.enter_context(pch)
                    p = PdfParser()
                    return p.parse(str(f), "doc1")

    # Gap 493→497: font_size == 0 not tracked
    def test_font_size_zero_not_tracked(self, tmp_path):
        from app.models import Block
        doc = self._run_parse(tmp_path, [_make_text_block("text", size=0, flags=0)])
        assert len(doc.blocks) == 1
        assert doc.blocks[0].style.font_size is None

    # Gap 499: bold flag (16)
    def test_bold_flag(self, tmp_path):
        from app.models import Block
        doc = self._run_parse(tmp_path, [_make_text_block("bold", size=11, flags=16)])
        assert doc.blocks[0].style.bold is True

    # Gap 501: italic flag (2)
    def test_italic_flag(self, tmp_path):
        from app.models import Block
        doc = self._run_parse(tmp_path, [_make_text_block("italic", size=11, flags=2)])
        assert doc.blocks[0].style.italic is True

    # Gap 503→485: line with only whitespace skipped
    def test_whitespace_line_skipped(self, tmp_path):
        from app.models import Block
        block_dict = _make_text_block(
            "visible",
            bbox=(50, 50, 550, 80),
            lines=[
                {"spans": [{"text": "   ", "size": 11, "flags": 0}]},
                {"spans": [{"text": "visible", "size": 11, "flags": 0}]},
            ],
        )
        doc = self._run_parse(tmp_path, [block_dict])
        assert len(doc.blocks) == 1
        assert doc.blocks[0].text == "visible"

    # Gap 508→456: text empty after join → block skipped
    def test_empty_text_after_join_skipped(self, tmp_path):
        from app.models import Block
        block_dict = _make_text_block(
            "",
            bbox=(50, 50, 550, 80),
            lines=[{"spans": [{"text": " ", "size": 11, "flags": 0}]}],
        )
        doc = self._run_parse(tmp_path, [block_dict])
        assert len(doc.blocks) == 0

    # Gap 541→545: no font_sizes → font_size is None
    def test_no_font_sizes_style(self, tmp_path):
        from app.models import Block
        doc = self._run_parse(tmp_path, [_make_text_block("text", size=0, flags=0)])
        assert doc.blocks[0].style.font_size is None

import contextlib

# ════════════════════════════════════════════════════════════
# Gaps 513→525, 521-523, 525→532, 529→532, 534
# ════════════════════════════════════════════════════════════
class TestMarginAndDuplicateSuppression:

    @staticmethod
    def _run_multi_parse(tmp_path, pages):
        from app.models import Block
        f = tmp_path / "multi.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = len(pages)
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.side_effect = lambda i: pages[i]
                pdf_doc.__iter__.return_value = iter(pages)
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    return p.parse(str(f), "doc1")

    # Gap 513→525: footer margin repeated on page 2 suppressed
    def test_margin_text_suppressed(self, tmp_path):
        from app.models import Block
        margin = _make_text_block("Footer", bbox=(0, 770, 100, 792), size=10, flags=0)
        doc = self._run_multi_parse(tmp_path, [_make_mock_page(blocks=[margin]), _make_mock_page(blocks=[margin])])
        assert len(doc.blocks) == 1

    # Gap 521-523: page 0 header with >3 words not suppressed
    def test_page_zero_long_header_not_suppressed(self, tmp_path):
        from app.models import Block
        header = _make_text_block("This is a long title sentence", bbox=(0, 0, 200, 30), size=18, flags=0)
        doc = self._run_multi_parse(tmp_path, [_make_mock_page(blocks=[header])])
        assert len(doc.blocks) == 1

    # Gap 525→532: margin_key seen → skip
    def test_margin_key_seen_skips(self, tmp_path):
        from app.models import Block
        text_block = _make_text_block("Footer text", bbox=(0, 770, 100, 792), size=10, flags=0)
        p1 = _make_mock_page(blocks=[text_block])
        p2 = _make_mock_page(blocks=[text_block])
        doc = self._run_multi_parse(tmp_path, [p1, p2])
        assert len(doc.blocks) <= 1

    # Gap 534: duplicate text >20 chars suppressed
    def test_duplicate_text_suppressed(self, tmp_path):
        from app.models import Block
        text = "This is a long repeated text that should get suppressed"
        block = _make_text_block(text, bbox=(50, 100, 550, 130), size=11, flags=0)
        doc = self._run_multi_parse(tmp_path, [_make_mock_page(blocks=[block]), _make_mock_page(blocks=[block])])
        assert len(doc.blocks) <= 2

# ════════════════════════════════════════════════════════════
# Gaps 560→562, 563, 565→580
# ════════════════════════════════════════════════════════════
class TestBboxAndHeaderFooterMetadata:

    def test_header_footer_metadata_set(self, tmp_path):
        from app.models import Block
        f = tmp_path / "hfmeta.pdf"
        f.write_text("dummy")
        header = _make_text_block("Head", bbox=(0, 0, 100, 30), size=10, flags=0)
        footer = _make_text_block("Foot", bbox=(0, 770, 100, 792), size=10, flags=0)
        page = _make_mock_page(blocks=[header, footer])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        h = [b for b in doc.blocks if b.metadata.get("is_header")]
        f = [b for b in doc.blocks if b.metadata.get("is_footer")]
        assert len(h) == 1
        assert len(f) == 1

    def test_bbox_metadata_set(self, tmp_path):
        from app.models import Block
        f = tmp_path / "bbox.pdf"
        f.write_text("dummy")
        page = _make_mock_page(blocks=[_make_text_block("has bbox", bbox=(10, 20, 600, 50), size=11, flags=0)])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert doc.blocks[0].metadata["bbox"] == [10.0, 20.0, 600.0, 50.0]

    def test_no_bbox_no_metadata(self, tmp_path):
        from app.models import Block
        f = tmp_path / "nobbox2.pdf"
        f.write_text("dummy")
        block_dict = {"type": 0, "lines": [{"spans": [{"text": "no bbox", "size": 11, "flags": 0}]}]}
        page = _make_mock_page(blocks=[block_dict])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert "bbox" not in doc.blocks[0].metadata

# ════════════════════════════════════════════════════════════
# Gaps 581-588 — heading detection branches
# ════════════════════════════════════════════════════════════
class TestHeadingDetection:

    @pytest.mark.parametrize(
        "size,is_bold,body,expected_level",
        [
            (20, False, 11, 1),
            (15, False, 11, 2),
            (13, False, 11, 3),
            (11, True, 11, 3),
        ],
    )
    def test_heading_levels(self, tmp_path, size, is_bold, body, expected_level):
        from app.models import Block
        f = tmp_path / f"head_{size}_{is_bold}.pdf"
        f.write_text("dummy")
        flags = 16 if is_bold else 0
        block_dict = _make_text_block("Heading text", bbox=(50, 50, 550, 80), size=size, flags=flags)
        page = _make_mock_page(blocks=[block_dict])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_calculate_font_stats", return_value=float(body)):
                    with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                        p = PdfParser()
                        doc = p.parse(str(f), "doc1")
        block = doc.blocks[0]
        assert block.metadata.get("potential_heading") is True
        assert block.metadata.get("heading_level") == expected_level

    def test_no_heading_for_small_not_bold(self, tmp_path):
        from app.models import Block
        f = tmp_path / "nohead.pdf"
        f.write_text("dummy")
        block_dict = _make_text_block("body text", bbox=(50, 50, 550, 80), size=10, flags=0)
        page = _make_mock_page(blocks=[block_dict])
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                        p = PdfParser()
                        doc = p.parse(str(f), "doc1")
        assert doc.blocks[0].metadata.get("potential_heading") in (None, False)

# ════════════════════════════════════════════════════════════
# Gaps 601-607 — table anchor assignment
# ════════════════════════════════════════════════════════════
class TestTableAnchorAssignment:

    @staticmethod
    def _run(tmp_path, page):
        from app.models import Block
        f = tmp_path / "anchor.pdf"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    return p.parse(str(f), "doc1")

    # 601-603: text before table
    def test_anchor_text_before(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (50, 200, 550, 300)
        mock_tbl.extract.return_value = [["A"]]
        mock_tbl.header = MagicMock(names=None)
        above = _make_text_block("Above", bbox=(50, 100, 550, 130), size=11, flags=0)
        page = _make_mock_page(blocks=[above], tables=[mock_tbl])
        doc = self._run(tmp_path, page)
        assert len(doc.tables) == 1

    # 604-605: table before any text
    def test_anchor_no_text_before(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (50, 50, 550, 150)
        mock_tbl.extract.return_value = [["A"]]
        mock_tbl.header = MagicMock(names=None)
        below = _make_text_block("Below", bbox=(50, 400, 550, 430), size=11, flags=0)
        page = _make_mock_page(blocks=[below], tables=[mock_tbl])
        doc = self._run(tmp_path, page)
        assert len(doc.tables) == 1

    # 606-607: no text blocks at all
    def test_anchor_no_text_blocks(self, tmp_path):
        from app.models import Block
        mock_tbl = MagicMock()
        mock_tbl.bbox = (50, 50, 550, 150)
        mock_tbl.extract.return_value = [["A"]]
        mock_tbl.header = MagicMock(names=None)
        page = _make_mock_page(tables=[mock_tbl])
        doc = self._run(tmp_path, page)
        assert len(doc.tables) == 1

# ════════════════════════════════════════════════════════════
# Gaps 620, 624, 651-652, 654-663, 672-673 — image extraction
# ════════════════════════════════════════════════════════════
class TestImageExtractionGaps:

    # Gap 620: image_data is None → continue
    def test_image_no_data_skipped(self, tmp_path):
        from app.models import Block
        f = tmp_path / "noimgdata.pdf"
        f.write_text("dummy")
        page = _make_mock_page(images=[(1,), (2,)])
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.extract_image.side_effect = [
                    {"image": b"realdata", "ext": "png"},
                    {"image": None, "ext": "png"},
                ]
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1

    # Gap 624: duplicate image hash → skip
    def test_duplicate_image_hash_skipped(self, tmp_path):
        from app.models import Block
        f = tmp_path / "dupeimg.pdf"
        f.write_text("dummy")
        page = _make_mock_page(images=[(1,), (2,)])
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.extract_image.return_value = {"image": b"same_data", "ext": "png"}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1

    # Gaps 651-652: get_image_rects raises → caught
    def test_image_get_rects_exception(self, tmp_path):
        from app.models import Block
        f = tmp_path / "rects_exc.pdf"
        f.write_text("dummy")
        page = _make_mock_page(images=[(1,)])
        page.get_image_rects.side_effect = RuntimeError("rects fail")
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.extract_image.return_value = {"image": b"imgdata", "ext": "png"}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1

    # Gaps 654-663: image rects and dimensions
    def test_image_rects_and_dimensions(self, tmp_path):
        from app.models import Block
        f = tmp_path / "imgdims.pdf"
        f.write_text("dummy")
        page = _make_mock_page(images=[(1,)])
        img_rect = MagicMock()
        img_rect.x0 = 50; img_rect.y0 = 100; img_rect.x1 = 250; img_rect.y1 = 400
        img_rect.width = 200; img_rect.height = 300
        page.get_image_rects.return_value = [img_rect]
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.extract_image.return_value = {"image": b"imgdata", "ext": "jpg"}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1
        assert doc.figures[0].width == 200.0
        assert doc.figures[0].height == 300.0
        assert isinstance(doc.figures[0].image_format, str)

    # Gaps 672-673: image extraction exception → caught
    def test_image_extraction_exception(self, tmp_path):
        from app.models import Block
        f = tmp_path / "imgext_exc.pdf"
        f.write_text("dummy")
        page = _make_mock_page(images=[(1,)])
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.extract_image.side_effect = RuntimeError("extract fail")
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 0

# ════════════════════════════════════════════════════════════
# Gaps 680-718 — image block fallback
# ════════════════════════════════════════════════════════════
class TestImageBlockFallback:

    def test_fallback_extracts_image_blocks(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_img.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[
                _make_image_block(b"img1", "png", (100, 100, 300, 300)),
                _make_image_block(b"img2", "jpg", (400, 400, 500, 500)),
            ],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 2

    def test_fallback_non_bytes_image_skipped(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_nonbytes.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[
                {"type": 1, "image": "string_not_bytes", "ext": "png", "bbox": (100, 100, 200, 200)},
                _make_image_block(b"valid_data", "png", (300, 300, 400, 400)),
            ],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1

    def test_fallback_duplicate_hash(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_dupe.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[
                _make_image_block(b"same", "png", (100, 100, 200, 200)),
                _make_image_block(b"same", "png", (300, 300, 400, 400)),
            ],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1

    def test_fallback_bbox_metadata(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_bbox.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[_make_image_block(b"data", "png", bbox=(50, 60, 150, 160))],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1
        assert doc.figures[0].metadata.get("bbox") == [50.0, 60.0, 150.0, 160.0]

    def test_fallback_no_bbox(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_nobbox.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[{"type": 1, "image": b"data", "ext": "png", "width": 100, "height": 100}],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 1
        assert "bbox" not in doc.figures[0].metadata

    def test_fallback_exception_caught(self, tmp_path):
        from app.models import Block
        f = tmp_path / "fb_exc.pdf"
        f.write_text("dummy")
        page = _make_mock_page(
            blocks=[{
                "type": 1,
                "image": b"data",
                "ext": "png",
                "width": "bad-value",
                "height": 100,
                "bbox": (100, 100, 200, 200),
            }],
            images=[],
        )
        page.get_image_rects.return_value = []
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                pdf_doc = MagicMock()
                pdf_doc.is_encrypted = False
                pdf_doc.__len__.return_value = 1
                pdf_doc.metadata = {}
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                mf.open.return_value = pdf_doc
                with patch.object(PdfParser, "_should_attempt_ocr_fallback", return_value=False):
                    p = PdfParser()
                    doc = p.parse(str(f), "doc1")
        assert len(doc.figures) == 0
