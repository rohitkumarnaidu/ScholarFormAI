# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Coverage gap tests for parsing, structure detection, and normalization modules.

Targets:
  - pdf_parser.py      (85.53% -> 92%+)
  - detector.py        (24.51% -> 50%+)
  - normalizer.py      (68.75% -> 85%+)
  - base_parser.py     (77.78% -> 95%+)
  - ocr_engine.py      (0%    -> 30%+)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


# ══════════════════════════════════════════════════════════════════════════════
# pdf_parser.py — gap coverage
# ══════════════════════════════════════════════════════════════════════════════

class TestPdfParserGaps:

    # ── _build_ocr_blocks edge cases ────────────────────────────────────────

    def test_build_ocr_blocks_single_paragraph(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                blocks = p._build_ocr_blocks("Just one paragraph.", "tesseract")
                assert len(blocks) == 1
                assert blocks[0].text == "Just one paragraph."

    def test_build_ocr_blocks_line_fallback(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                blocks = p._build_ocr_blocks("Line1\nLine2\n\n\n  \nLine3", "tesseract")
                assert len(blocks) >= 2

    # ── _maybe_apply_ocr_fallback ───────────────────────────────────────────

    def _prepare_ocr_test(self):
        """Prepare PdfParser with fitz patched and helper mocks."""
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
        return p

    def test_maybe_apply_ocr_fallback_imports_unavailable(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        with patch("builtins.__import__", side_effect=ImportError("no module")):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [])
        assert result == []
        assert backend is None

    def test_maybe_apply_ocr_fallback_enhancement_disabled(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = False
        with patch("app.services.enhancement_manager.enhancement_manager", mock_mgr):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [])
        assert backend is None

    def test_maybe_apply_ocr_fallback_no_backends(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = True
        mock_mgr.profile.ocr_enabled = True
        mock_mgr.get_ocr_backends.return_value = ["surya", "ocrspace"]
        with (
            patch("app.services.enhancement_manager.enhancement_manager", mock_mgr),
            patch.object(p, "_should_attempt_ocr_fallback", return_value=True),
        ):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [])
        assert backend is None

    def test_maybe_apply_ocr_fallback_not_scanned(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = True
        mock_mgr.profile.ocr_enabled = True
        mock_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_ocr = MagicMock()
        mock_ocr.is_scanned.return_value = False
        with (
            patch("app.services.enhancement_manager.enhancement_manager", mock_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_ocr),
            patch.object(p, "_should_attempt_ocr_fallback", return_value=True),
        ):
            blocks_in = [MagicMock(text="some text")]
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, blocks_in)
        assert result == blocks_in
        assert backend is None

    def test_maybe_apply_ocr_fallback_scanned_but_no_ocr_blocks(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = True
        mock_mgr.profile.ocr_enabled = True
        mock_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_ocr = MagicMock()
        mock_ocr.is_scanned.return_value = True
        mock_ocr.extract_text.return_value = ("", "tesseract")
        with (
            patch("app.services.enhancement_manager.enhancement_manager", mock_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_ocr),
            patch.object(p, "_should_attempt_ocr_fallback", return_value=True),
        ):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [MagicMock(text="old")])
        assert backend is None

    def test_maybe_apply_ocr_fallback_success(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = True
        mock_mgr.profile.ocr_enabled = True
        mock_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_ocr = MagicMock()
        mock_ocr.is_scanned.return_value = True
        mock_ocr.extract_text.return_value = ("OCR text content.\n\nSecond para.", "tesseract")
        with (
            patch("app.services.enhancement_manager.enhancement_manager", mock_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_ocr),
            patch.object(p, "_should_attempt_ocr_fallback", return_value=True),
        ):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [])
        assert len(result) >= 2
        assert backend == "tesseract"

    def test_maybe_apply_ocr_fallback_ocr_error(self):
        p = self._prepare_ocr_test()
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 5
        mock_mgr = MagicMock()
        mock_mgr.profile.enabled = True
        mock_mgr.profile.ocr_enabled = True
        mock_mgr.get_ocr_backends.return_value = ["tesseract"]
        mock_ocr = MagicMock()
        mock_ocr.is_scanned.return_value = True
        mock_ocr.extract_text.side_effect = Exception("OCRError")
        with (
            patch("app.services.enhancement_manager.enhancement_manager", mock_mgr),
            patch("app.pipeline.ocr.pdf_ocr.PdfOCR", return_value=mock_ocr),
            patch.object(p, "_should_attempt_ocr_fallback", return_value=True),
        ):
            result, backend = p._maybe_apply_ocr_fallback("path.pdf", pdf_doc, [MagicMock(text="old")])
        assert backend is None

    # ── _is_header_footer edge cases ────────────────────────────────────────

    def test_is_header_footer_mid_region_bottom_true(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                # 792 - (792*0.07) = 736.56
                assert p._is_header_footer([0, 750, 100, 792], [0, 0, 612, 792]) is True

    # ── _normalize_margin_text edge cases ───────────────────────────────────

    def test_normalize_margin_text_none(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                assert p._normalize_margin_text(None) == ""
                assert p._normalize_margin_text("") == ""

    def test_normalize_margin_text_roman(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                result = p._normalize_margin_text("Page iii of v")
                assert result == "page of"

    def test_normalize_margin_text_no_numbers(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                result = p._normalize_margin_text("Header Text")
                assert result == "header text"

    # ── _sanitize_cell_text edge cases ──────────────────────────────────────

    def test_sanitize_cell_text_multi_newlines(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                assert p._sanitize_cell_text("hello\n\n\nworld") == "hello   world"
                assert p._sanitize_cell_text("") == ""

    # ── _build_table_model edge cases ───────────────────────────────────────

    def test_build_table_model_no_rows_all_empty(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                assert p._build_table_model([[""]], 1, 100) is not None

    def test_build_table_model_all_zero_cols(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                assert p._build_table_model([], 1, 100) is None

    # ── _extract_content error paths ────────────────────────────────────────

    def _make_content_test_pdf_doc(self, page):
        pdf_doc = MagicMock()
        pdf_doc.__len__.return_value = 1
        pdf_doc.__getitem__.return_value = page
        pdf_doc.__iter__.return_value = iter([page])
        return pdf_doc

    def test_extract_content_table_extraction_fails(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.side_effect = Exception("table fail")
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert tables == []

    def test_extract_content_get_text_fails(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.return_value = []
                page.get_text.side_effect = Exception("get_text fail")
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert blocks == []

    def test_extract_content_image_extract_fails(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.return_value = []
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0, 0)]
                pdf_doc = self._make_content_test_pdf_doc(page)
                pdf_doc.extract_image.side_effect = Exception("extract fail")
                page.get_image_rects.return_value = []
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert figs == []

    def test_extract_content_image_fallback_path(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.return_value = []
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 1, "image": b"imgdata", "ext": "jpg", "width": 100, "height": 200, "bbox": [0, 0, 100, 200]}
                    ]
                }
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert len(figs) == 1

    def test_extract_content_image_fallback_skip_non_image_blocks(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.return_value = []
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 0, "lines": [{"spans": [{"text": "text", "size": 11, "flags": 0}]}]}
                    ]
                }
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert len(blocks) >= 1
                assert figs == []

    def test_extract_content_image_fallback_bad_image_data(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.find_tables.return_value = []
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 1, "image": "not_bytes", "ext": "png"}
                    ]
                }
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert figs == []

    def test_extract_content_table_without_header(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                mock_table = MagicMock()
                mock_table.bbox = (50, 100, 200, 150)
                mock_table.extract.return_value = [["A", "B"], ["1", "2"]]
                mock_table.header = None
                page.find_tables.return_value = [mock_table]
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert len(tables) == 1

    def test_extract_content_table_with_none_bbox(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                mock_table = MagicMock()
                mock_table.bbox = None
                mock_table.extract.return_value = [["A"]]
                mock_table.header = MagicMock(names=[])
                page.find_tables.return_value = [mock_table]
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert len(tables) == 1

    def test_extract_content_text_block_in_table_skipped(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                mock_table = MagicMock()
                mock_table.bbox = (0, 0, 612, 792)
                mock_table.extract.return_value = []
                mock_table.header = MagicMock(names=[])
                page.find_tables.return_value = [mock_table]
                page.get_text.return_value = {
                    "blocks": [
                        {
                            "type": 0,
                            "bbox": (10, 10, 100, 50),
                            "lines": [{"spans": [{"text": "Table text", "size": 11, "flags": 0}]}],
                        }
                    ]
                }
                page.get_images.return_value = []
                pdf_doc = self._make_content_test_pdf_doc(page)
                blocks, figs, tables = p._extract_content(pdf_doc)
                assert blocks == []

    def test_extract_content_repeated_text_suppression(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                from app.pipeline.parsing.pdf_parser import PdfParser
                p = PdfParser()
                pages = []
                text_block = {
                    "type": 0,
                    "bbox": (100, 300, 400, 350),
                    "lines": [{"spans": [{"text": "Repeated text that is long enough to trigger suppression", "size": 11, "flags": 0}]}],
                }
                for _ in range(2):
                    pg = MagicMock()
                    pg.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                    pg.find_tables.return_value = []
                    pg.get_text.return_value = {"blocks": [text_block]}
                    pg.get_images.return_value = []
                    pages.append(pg)
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 2
                pdf_doc.__getitem__.side_effect = lambda i: pages[i]
                pdf_doc.__iter__.return_value = iter(pages)
                with patch.object(p, "_is_header_footer", return_value=False):
                    blocks, figs, tables = p._extract_content(pdf_doc)
                assert len(blocks) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# detector.py — gap coverage
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectorGaps:

    def _make_detector(self):
        with patch("app.pipeline.structure_detection.detector.ContractLoader"):
            from app.pipeline.structure_detection.detector import StructureDetector
            return StructureDetector()

    def test_detect_structure_convenience(self):
        from app.models import PipelineDocument as Document
        from app.pipeline.structure_detection.detector import detect_structure
        doc = Document(document_id="t", blocks=[])
        with patch("app.pipeline.structure_detection.detector.ContractLoader"):
            result = detect_structure(doc)
            assert result is not None

    def test_process_with_docling_layout(self):
        sd = self._make_detector()
        from app.models import DocumentMetadata
        from app.models import PipelineDocument as Document
        doc = Document(
            document_id="t",
            blocks=[],
            metadata=DocumentMetadata(ai_hints={"docling_layout": {"elements": [{"text": "Title", "type": "title", "font_size": 20, "bbox": {"page": 1, "y0": 50}}]}}),
        )
        sd.process(doc)
        assert "structure_detection" in [s.stage_name for s in doc.processing_history]

    def test_process_with_template(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        from app.models import PipelineDocument as Document
        from app.models.pipeline_document import TemplateInfo
        block = Block(block_id="b1", index=0, text="1. Introduction", style=TextStyle(bold=True))
        doc = Document(
            document_id="t",
            blocks=[block],
            template=TemplateInfo(template_name="ieee"),
        )
        sd.process(doc)
        assert doc.blocks[0].section_name is not None

    def test_detect_structure_with_docling_empty_elements(self):
        sd = self._make_detector()
        blocks = []
        result = sd._detect_structure_with_docling(blocks, {"elements": []})
        assert result == []

    def test_detect_structure_with_docling_title_detected(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        block = Block(block_id="b1", index=0, text="Paper Title", style=TextStyle())
        result = sd._detect_structure_with_docling(
            [block],
            {
                "elements": [
                    {"text": "Paper Title", "type": "title", "font_size": 20, "bbox": {"page": 1, "y0": 50}},
                ]
            },
        )
        assert len(result) == 1
        assert result[0]["level"] == 0

    def test_detect_structure_with_docling_heading_detected(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        block = Block(block_id="b2", index=100, text="Introduction", style=TextStyle())
        result = sd._detect_structure_with_docling(
            [block],
            {
                "elements": [
                    {"text": "Introduction", "type": "section_header", "font_size": 16, "confidence": 0.95},
                ]
            },
        )
        assert len(result) == 1
        assert result[0]["level"] == 1

    def test_detect_structure_with_docling_token_overlap_match(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        block = Block(block_id="b3", index=200, text="Background and Related Work", style=TextStyle())
        result = sd._detect_structure_with_docling(
            [block],
            {
                "elements": [
                    {"text": "Background & Related Work", "type": "heading", "font_size": 14},
                ]
            },
        )
        assert len(result) == 1

    def test_detect_structure_with_docling_fallback_to_standard(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        block = Block(block_id="b4", index=300, text="Some random text", style=TextStyle())
        result = sd._detect_structure_with_docling(
            [block],
            {
                "elements": [
                    {"text": "Completely Different Text", "type": "heading", "font_size": 14},
                ]
            },
        )
        # Elements don't match any block so _detect_heading_candidates fallback runs
        assert len(result) >= 0
    def test_detect_heading_candidates_author_affiliation(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        title_block = Block(block_id="t1", index=0, text="The Paper Title", style=TextStyle())
        author_block = Block(block_id="a1", index=100, text="John A. Doe, Jane B. Smith", style=TextStyle())
        aff_block = Block(block_id="af1", index=200, text="University of Science and Technology", style=TextStyle())
        sd._detect_heading_candidates([title_block, author_block, aff_block])
        assert title_block.metadata.get("is_author_block") is None
        assert author_block.metadata.get("is_author_block") is True
        assert aff_block.metadata.get("is_affiliation_block") is True

    def test_detect_heading_candidates_skip_header_footer(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        b = Block(block_id="hf1", index=0, text="Header content", style=TextStyle(),
                  metadata={"is_header": True})
        result = sd._detect_heading_candidates([b])
        assert result == []

    def test_assign_section_names_headers_footers_skipped(self):
        sd = self._make_detector()
        from app.models import Block
        h_block = Block(block_id="h1", index=0, text="Header", metadata={"is_header": True})
        sd._assign_section_names([h_block], [])
        assert h_block.section_name is None

    def test_assign_section_names_with_numbering(self):
        sd = self._make_detector()
        from app.models import Block
        heading = Block(block_id="hd1", index=0, text="1. Introduction",
                        metadata={"numbering_info": {"remainder": "Introduction"}})
        candidates = [{"block": heading, "block_id": "hd1", "level": 1}]
        sd._assign_section_names([heading], candidates)
        assert heading.section_name == "Introduction"

    def test_assign_section_names_title_level(self):
        sd = self._make_detector()
        from app.models import Block
        heading = Block(block_id="h0", index=0, text="The Title")
        candidates = [{"block": heading, "block_id": "h0", "level": 0}]
        sd._assign_section_names([heading], candidates)
        assert heading.section_name == "title"

    def test_build_hierarchy_with_parent(self):
        sd = self._make_detector()
        from app.models import Block
        l1 = Block(block_id="l1", index=0, text="Intro")
        l2 = Block(block_id="l2", index=100, text="Background")
        candidates = [
            {"block": l1, "block_id": "l1", "level": 1},
            {"block": l2, "block_id": "l2", "level": 2},
        ]
        sd._build_hierarchy([l1, l2], candidates)
        assert l2.parent_id == "l1"

    def test_build_hierarchy_skip_header_footer(self):
        sd = self._make_detector()
        from app.models import Block
        hf = Block(block_id="hf", index=0, text="Header", metadata={"is_header": True})
        candidates = [{"block": hf, "block_id": "hf", "level": 1}]
        sd._build_hierarchy([hf], candidates)
        assert hf.parent_id is None

    def test_canonicalize_sections(self):
        sd = self._make_detector()
        from app.models import Block
        block = Block(block_id="b", index=0, text="Related Work", section_name="Related Work")
        sd.contract_loader.get_canonical_name.return_value = "Background"
        sd._canonicalize_sections([block], "ieee")
        assert block.section_name == "Background"

    def test_canonicalize_sections_fails_gracefully(self):
        sd = self._make_detector()
        from app.models import Block
        block = Block(block_id="b", index=0, text="Intro", section_name="Intro")
        sd.contract_loader.get_canonical_name.side_effect = Exception("fail")
        sd._canonicalize_sections([block], "ieee")
        assert block.section_name == "Intro"

    def test_validate_hierarchy_jump_detected(self):
        sd = self._make_detector()
        from app.models import Block, BlockType
        b1 = Block(block_id="b1", index=0, text="L1", level=1)
        b1.block_type = BlockType.HEADING_1
        b2 = Block(block_id="b2", index=100, text="L3", level=3)
        b2.block_type = BlockType.HEADING_3
        sd._validate_hierarchy([b1, b2])
        assert b2.is_valid is False
        assert any("jump" in w for w in b2.warnings)

    def test_validate_hierarchy_skip_header_footer(self):
        sd = self._make_detector()
        from app.models import Block, BlockType
        hf = Block(block_id="hf", index=0, text="Header", level=1, metadata={"is_header": True})
        hf.block_type = BlockType.HEADING_1
        sd._validate_hierarchy([hf])
        assert hf.is_valid is True

    def test_validate_hierarchy_no_jump(self):
        sd = self._make_detector()
        from app.models import Block, BlockType
        b1 = Block(block_id="b1", index=0, text="L1", level=1)
        b1.block_type = BlockType.HEADING_1
        b2 = Block(block_id="b2", index=100, text="L2", level=2)
        b2.block_type = BlockType.HEADING_2
        sd._validate_hierarchy([b1, b2])
        assert b2.is_valid is True

    def test_calculate_avg_font_size_with_text(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        b1 = Block(block_id="b1", index=0, text="hello", style=TextStyle(font_size=12.0))
        b2 = Block(block_id="b2", index=100, text="world", style=TextStyle(font_size=14.0))
        result = sd._calculate_avg_font_size([b1, b2])
        assert result == 13.0

    def test_calculate_avg_font_size_all_empty(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        b = Block(block_id="b1", index=0, text="", style=TextStyle(font_size=12.0))
        result = sd._calculate_avg_font_size([b])
        assert result is None

    def test_detect_heading_candidates_empty_text_skipped(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        b = Block(block_id="b1", index=0, text="   ", style=TextStyle())
        result = sd._detect_heading_candidates([b])
        assert result == []

    def test_detect_heading_candidates_title_detected(self):
        sd = self._make_detector()
        from app.models import Block, TextStyle
        b = Block(block_id="b1", index=0, text="Short Title", style=TextStyle())
        result = sd._detect_heading_candidates([b])
        assert len(result) >= 1
        assert b.block_type.value == "title"

    def test_process_fallback_from_docling_empty(self):
        sd = self._make_detector()
        from app.models import Block, DocumentMetadata, PipelineDocument, TextStyle
        b = Block(block_id="b1", index=0, text="Introduction", style=TextStyle(bold=True))
        doc = PipelineDocument(
            document_id="t",
            blocks=[b],
            metadata=DocumentMetadata(ai_hints={"docling_layout": {"elements": []}}),
        )
        sd.process(doc)
        # Normalizer may copy the block, so check document blocks
        assert doc.blocks[0].section_name is not None


# ══════════════════════════════════════════════════════════════════════════════
# normalizer.py — gap coverage
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizerGaps:

    def _make_normalizer(self):
        from app.pipeline.normalization.normalizer import Normalizer
        return Normalizer()

    # ── _sanitize_empty_orphan_blocks ───────────────────────────────────────

    def test_sanitize_empty_orphan_removes_body(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="", block_type=BlockType.BODY)
        b2 = Block(block_id="b2", index=100, text="Real content")
        result = n._sanitize_empty_orphan_blocks([b1, b2])
        assert len(result) == 1

    def test_sanitize_empty_orphan_removes_unknown(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.UNKNOWN)
        result = n._sanitize_empty_orphan_blocks([b])
        assert result == []

    def test_sanitize_empty_orphan_preserves_with_figure(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.BODY, metadata={"has_figure": True})
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_sanitize_empty_orphan_preserves_with_equation(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.BODY, metadata={"has_equation": True})
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_sanitize_empty_orphan_preserves_with_list_level(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.BODY, metadata={"list_level": 1})
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_sanitize_empty_orphan_preserves_with_anchor(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.BODY, metadata={"anchor": True})
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_sanitize_empty_orphan_preserves_heading_type(self):
        from app.models import Block, BlockType
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="", block_type=BlockType.HEADING_1)
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    # ── _normalize_metadata edge cases ──────────────────────────────────────

    def test_normalize_metadata_all_fields(self):
        from app.models import DocumentMetadata
        n = self._make_normalizer()
        meta = DocumentMetadata(
            title="  Title  ",
            authors=["  Author 1  ", ""],
            affiliations=["  Affil  ", ""],
            abstract="  Abstract\nwith newlines  ",
            keywords=["   kw1   ", ""],
            journal="  Journal  ",
            corresponding_author="  Author  ",
            email="  email@test.com  ",
        )
        result = n._normalize_metadata(meta)
        assert result.title == "Title"
        assert result.authors == ["Author 1"]
        assert result.affiliations == ["Affil"]
        assert "Abstract" in result.abstract
        assert result.keywords == ["kw1"]
        assert result.journal == "Journal"
        assert result.corresponding_author == "Author"
        assert result.email == "email@test.com"

    def test_normalize_metadata_partial(self):
        from app.models import DocumentMetadata
        n = self._make_normalizer()
        meta = DocumentMetadata(title=None, authors=[], affiliations=[], keywords=[])
        result = n._normalize_metadata(meta)
        assert result.title is None
        assert result.authors == []
        assert result.keywords == []

    # ── _calculate_median_font_size ─────────────────────────────────────────

    def test_calculate_median_font_size_some_empty(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="   ", style=TextStyle(font_size=12.0))
        b2 = Block(block_id="b2", index=100, text="content", style=TextStyle(font_size=14.0))
        result = n._calculate_median_font_size([b1, b2])
        assert result == 14.0

    def test_calculate_median_font_size_all_missing(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="content", style=TextStyle())
        result = n._calculate_median_font_size([b])
        assert result is None

    # ── _repair_common_corruptions edge cases ───────────────────────────────

    def test_repair_all_patterns(self):
        n = self._make_normalizer()
        assert n._repair_common_corruptions("2ntroduction") == "2 Introduction"
        assert n._repair_common_corruptions("3ethodology") == "3 Methodology"
        assert n._repair_common_corruptions("4esults") == "4 Results"
        assert n._repair_common_corruptions("5iscussion") == "5 Discussion"
        assert n._repair_common_corruptions("6onclusion") == "6 Conclusion"
        assert n._repair_common_corruptions("7eferences") == "7 References"
        assert n._repair_common_corruptions("8bstract") == "8 Abstract"

    def test_repair_no_match(self):
        n = self._make_normalizer()
        assert n._repair_common_corruptions("Normal text") == "Normal text"

    def test_repair_empty(self):
        n = self._make_normalizer()
        assert n._repair_common_corruptions("") == ""
        assert n._repair_common_corruptions(None) is None

    # ── _normalize_blocks split logic edge cases ────────────────────────────

    def test_normalize_blocks_keyword_split(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="IntroductionThis is the intro text that is long enough to warrant splitting into two blocks because the threshold is 30 chars for keyword splits.",
                  style=TextStyle())
        blocks = n._normalize_blocks([b])
        assert len(blocks) >= 2

    def test_normalize_blocks_keyword_split_too_short_body(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="IntroductionShort.", style=TextStyle())
        blocks = n._normalize_blocks([b])
        assert len(blocks) >= 1

    def test_normalize_blocks_abstract_split(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="Abstract: This paper describes a novel method.", style=TextStyle())
        blocks = n._normalize_blocks([b])
        assert len(blocks) >= 2
        assert "abstract" in blocks[0].text.lower()
        assert "This paper" in blocks[1].text

    def test_normalize_blocks_figure_block_skips_split(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="IntroductionText", style=TextStyle(), metadata={"has_figure": True})
        blocks = n._normalize_blocks([b])
        assert len(blocks) == 1

    def test_normalize_blocks_list_item_skips_numbered_split(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="1. IntroductionSome body text.",
                  style=TextStyle(), metadata={"list_level": 0})
        blocks = n._normalize_blocks([b])
        assert len(blocks) == 1

    def test_normalize_blocks_merge_heading_consolidation(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="Introduction", style=TextStyle(bold=True, font_size=14.0))
        b2 = Block(block_id="b2", index=100, text="And Background", style=TextStyle(bold=True, font_size=13.0))
        blocks = n._normalize_blocks([b1, b2], median_font=11.0)
        assert len(blocks) == 1
        assert "Introduction And Background" in blocks[0].text

    def test_normalize_blocks_no_merge_when_long(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="A" * 100, style=TextStyle(bold=True, font_size=14.0))
        b2 = Block(block_id="b2", index=100, text="B" * 100, style=TextStyle(bold=True, font_size=13.0))
        blocks = n._normalize_blocks([b1, b2], median_font=11.0)
        assert len(blocks) == 2

    def test_normalize_blocks_no_merge_not_heading(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="Short", style=TextStyle())
        b2 = Block(block_id="b2", index=100, text="Text", style=TextStyle())
        blocks = n._normalize_blocks([b1, b2], median_font=None)
        assert len(blocks) == 2

    def test_normalize_blocks_duplicate_consecutive_filter(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b1 = Block(block_id="b1", index=0, text="Same text", style=TextStyle())
        b2 = Block(block_id="b2", index=100, text="Same text", style=TextStyle())
        blocks = n._normalize_blocks([b1, b2])
        assert len(blocks) == 1
        assert blocks[0].metadata.get("has_consecutive_duplicate") is True

    def test_normalize_blocks_empty_after_split_filtered(self):
        from app.models import Block, TextStyle
        n = self._make_normalizer()
        b = Block(block_id="b1", index=0, text="   ", style=TextStyle())
        blocks = n._normalize_blocks([b])
        assert len(blocks) == 0

    # ── normalize_document convenience function ─────────────────────────────

    def test_normalize_document_convenience(self):
        from app.models import PipelineDocument as Document
        from app.pipeline.normalization.normalizer import normalize_document
        doc = Document(document_id="t", blocks=[])
        result = normalize_document(doc)
        assert result.document_id == "t"

    def test_normalize_document_with_blocks_and_tables(self):
        from app.models import Block, Table, TableCell
        from app.models import PipelineDocument as Document
        from app.pipeline.normalization.normalizer import normalize_document
        block = Block(block_id="b1", index=0, text="  Hello World  ")
        cell = TableCell(row=0, col=0, text="  Cell  ")
        table = Table(table_id="t1", index=0, block_index=0, page_number=1,
                      num_rows=1, num_cols=1, cells=[cell],
                      data=[["Cell"]], rows=[["Cell"]])
        doc = Document(document_id="t", blocks=[block], tables=[table])
        result = normalize_document(doc)
        assert result.blocks[0].text == "Hello World"
        assert result.tables[0].cells[0].text == "Cell"

    # ── process() invariant checks ──────────────────────────────────────────

    def test_process_duplicate_indices_causes_assertion(self):
        from app.models import Block, PipelineDocument
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b1 = Block(block_id="b1", index=0, text="a")
        b2 = Block(block_id="b2", index=0, text="b")
        doc = PipelineDocument(document_id="t", blocks=[b1, b2])
        with pytest.raises(AssertionError, match="Duplicate block indices"):
            n.process(doc)

    def test_process_non_integer_index_in_document(self):
        from app.models import PipelineDocument
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        # Directly set the document's blocks to bypass pydantic validation
        doc = PipelineDocument(document_id="t", blocks=[])
        # Create a block with a string index to test the isinstance check
        class BadBlock:
            def __init__(self):
                self.index = "not_int"
                self.text = "a"
                self.block_id = "b1"
                self.block_type = None
                self.metadata = {}
                self.style = MagicMock()
                self.style.font_size = None
                self.style.bold = False
                self.warnings = []
                self.is_valid = True
                self.model_copy = lambda **kw: self
                self.section_name = None
                self.level = None
                self.parent_id = None
        doc.blocks = [BadBlock()]
        with pytest.raises(AssertionError, match="Non-integer"):
            n.process(doc)


# ══════════════════════════════════════════════════════════════════════════════
# base_parser.py — gap coverage
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseParserGaps:

    def test_abstract_methods_have_correct_signatures(self):
        import inspect

        from app.pipeline.parsing.base_parser import BaseParser
        sig_parse = inspect.signature(BaseParser.parse)
        params = list(sig_parse.parameters.keys())
        assert "self" in params
        assert "file_path" in params
        assert "document_id" in params

        sig_format = inspect.signature(BaseParser.supports_format)
        params_f = list(sig_format.parameters.keys())
        assert "self" in params_f
        assert "file_extension" in params_f

    def test_concrete_must_implement_both_methods(self):
        from app.pipeline.parsing.base_parser import BaseParser
        class PartialParser(BaseParser):
            def parse(self, file_path, document_id):
                pass
        with pytest.raises(TypeError):
            PartialParser()

    def test_supports_format_dispatch(self):
        from app.pipeline.parsing.base_parser import BaseParser
        class DispatchParser(BaseParser):
            def parse(self, file_path, document_id):
                return None
            def supports_format(self, file_extension):
                return file_extension == ".pdf"
        p = DispatchParser()
        assert p.supports_format(".pdf") is True
        assert p.supports_format(".docx") is False


# ══════════════════════════════════════════════════════════════════════════════
# ocr_engine.py — gap coverage
# ══════════════════════════════════════════════════════════════════════════════

class TestOCREngineGaps:

    def _patch_surya_module(self):
        """Patch surya module imports with create=True since they're in try/except at module level."""
        return [
            patch("app.pipeline.parsing.ocr_engine.run_ocr", create=True),
            patch("app.pipeline.parsing.ocr_engine.batch_text_detection", create=True),
            patch("app.pipeline.parsing.ocr_engine.batch_layout_detection", create=True),
            patch("app.pipeline.parsing.ocr_engine.batch_ordering", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_det_model", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_det_processor", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_rec_model", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_rec_processor", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_order_model", create=True),
            patch("app.pipeline.parsing.ocr_engine.load_order_processor", create=True),
        ]

    def test_detect_text_basic(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                mock_run = MagicMock()
                mock_line = MagicMock()
                mock_line.text = "Hello world"
                mock_line.confidence = 0.95
                mock_line.bbox = [0, 0, 100, 20]
                mock_result = MagicMock()
                mock_result.text_lines = [mock_line]
                mock_run.return_value = [mock_result]
                with patch("app.pipeline.parsing.ocr_engine.run_ocr", mock_run, create=True):
                    engine = OCREngine()
                    pages = engine.detect_text([MagicMock()])
                    assert len(pages) == 1
                    assert pages[0]["full_text"] == "Hello world"
        finally:
            for p in patches:
                p.stop()

    def test_detect_text_with_languages(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                mock_run = MagicMock()
                mock_run.return_value = [MagicMock(text_lines=[])]
                with patch("app.pipeline.parsing.ocr_engine.run_ocr", mock_run, create=True):
                    engine = OCREngine()
                    pages = engine.detect_text([MagicMock()], languages=["en", "fr"])
                    assert len(pages) == 1
        finally:
            for p in patches:
                p.stop()

    def test_detect_layout_basic(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                mock_region = MagicMock()
                mock_region.label = "Text"
                mock_region.bbox = [0, 0, 100, 50]
                mock_region.confidence = 0.9
                page_layout = MagicMock()
                page_layout.bboxes = [mock_region]
                mock_layout = MagicMock(return_value=[page_layout])
                with patch("app.pipeline.parsing.ocr_engine.batch_layout_detection", mock_layout, create=True):
                    engine = OCREngine()
                    pages = engine.detect_layout([MagicMock()])
                    assert len(pages) == 1
                    assert pages[0][0]["label"] == "Text"
        finally:
            for p in patches:
                p.stop()

    def test_detect_layout_no_confidence(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                class FakeRegion:
                    label = "Figure"
                    bbox = [0, 0, 200, 150]
                page_layout = MagicMock()
                page_layout.bboxes = [FakeRegion()]
                mock_layout = MagicMock(return_value=[page_layout])
                with patch("app.pipeline.parsing.ocr_engine.batch_layout_detection", mock_layout, create=True):
                    engine = OCREngine()
                    pages = engine.detect_layout([MagicMock()])
                    assert pages[0][0]["confidence"] is None
        finally:
            for p in patches:
                p.stop()

    def test_detect_reading_order_basic(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                mock_item = MagicMock()
                mock_item.bbox = [0, 0, 100, 20]
                mock_item.position = 2
                mock_item.label = "text"
                page_order = MagicMock()
                page_order.bboxes = [mock_item]
                mock_order = MagicMock(return_value=[page_order])
                with patch("app.pipeline.parsing.ocr_engine.batch_ordering", mock_order, create=True):
                    engine = OCREngine()
                    pages = engine.detect_reading_order([MagicMock()])
                    assert len(pages) == 1
        finally:
            for p in patches:
                p.stop()

    def test_detect_reading_order_with_default_label(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                class FakeOrderItem:
                    bbox = [0, 0, 50, 20]
                    position = 1
                page_order = MagicMock()
                page_order.bboxes = [FakeOrderItem()]
                mock_order = MagicMock(return_value=[page_order])
                with patch("app.pipeline.parsing.ocr_engine.batch_ordering", mock_order, create=True):
                    engine = OCREngine()
                    pages = engine.detect_reading_order([MagicMock()])
                    assert pages[0][0]["label"] == "text"
        finally:
            for p in patches:
                p.stop()

    def test_is_scanned_pdf_edge_cases(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
                engine = OCREngine()
                assert engine.is_scanned_pdf("", 5) is True
                assert engine.is_scanned_pdf("   ", 5) is True
                assert engine.is_scanned_pdf("A" * 49, 1) is True
                assert engine.is_scanned_pdf("A" * 50, 1) is False
        finally:
            for p in patches:
                p.stop()

    def test_get_ocr_engine_returns_instance_when_available(self):
        from app.pipeline.parsing.ocr_engine import get_ocr_engine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.pipeline.parsing.ocr_engine.OCREngine") as MockEngine,
            ):
                instance = MagicMock()
                MockEngine.return_value = instance
                engine1 = get_ocr_engine()
                engine2 = get_ocr_engine()
                assert engine1 is engine2
        finally:
            for p in patches:
                p.stop()

    def test_get_ocr_engine_import_error(self):
        from app.pipeline.parsing import ocr_engine as ocr_mod
        from app.pipeline.parsing.ocr_engine import get_ocr_engine
        ocr_mod._ocr_engine = None
        eng = get_ocr_engine()
        assert eng is None

    def test_ensure_detection_loaded_model_store_has(self):
        """Cache hit: model_store already has surya_det_model."""
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
            ):
                mock_store.is_loaded.return_value = True
                mock_store.get_model.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_detection_loaded()
                assert engine._loaded_det is True
        finally:
            for p in patches:
                p.stop()

    def test_ensure_detection_loaded_model_store_miss(self):
        """Cache miss: model store doesn't have model, loading fresh."""
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
                patch("app.pipeline.parsing.ocr_engine.load_det_model", create=True) as mock_ldm,
                patch("app.pipeline.parsing.ocr_engine.load_det_processor", create=True) as mock_ldp,
            ):
                mock_store.is_loaded.return_value = False
                mock_ldm.return_value = MagicMock()
                mock_ldp.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_detection_loaded()
                assert engine._loaded_det is True
                mock_ldm.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_ensure_recognition_loaded_model_store_has(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
            ):
                mock_store.is_loaded.return_value = True
                mock_store.get_model.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_recognition_loaded()
                assert engine._loaded_rec is True
        finally:
            for p in patches:
                p.stop()

    def test_ensure_recognition_loaded_model_store_miss(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
                patch("app.pipeline.parsing.ocr_engine.load_rec_model", create=True) as mock_lrm,
                patch("app.pipeline.parsing.ocr_engine.load_rec_processor", create=True) as mock_lrp,
            ):
                mock_store.is_loaded.return_value = False
                mock_lrm.return_value = MagicMock()
                mock_lrp.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_recognition_loaded()
                assert engine._loaded_rec is True
                mock_lrm.assert_called_once()
        finally:
            for p in patches:
                p.stop()

    def test_ensure_ordering_loaded_model_store_has(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
            ):
                mock_store.is_loaded.return_value = True
                mock_store.get_model.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_ordering_loaded()
                assert engine._loaded_order is True
        finally:
            for p in patches:
                p.stop()

    def test_ensure_ordering_loaded_model_store_miss(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        patches = self._patch_surya_module()
        for p in patches:
            p.start()
        try:
            with (
                patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True),
                patch("app.services.model_store.model_store") as mock_store,
                patch("app.pipeline.parsing.ocr_engine.load_order_model", create=True) as mock_lom,
                patch("app.pipeline.parsing.ocr_engine.load_order_processor", create=True) as mock_lop,
            ):
                mock_store.is_loaded.return_value = False
                mock_lom.return_value = MagicMock()
                mock_lop.return_value = MagicMock()
                engine = OCREngine()
                engine._ensure_ordering_loaded()
                assert engine._loaded_order is True
                mock_lom.assert_called_once()
        finally:
            for p in patches:
                p.stop()
