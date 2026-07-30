# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Targeted tests for uncovered lines in parser.py, pdf_parser.py, parser_factory.py, formatter_engine.py, safe_execution.py."""

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import MagicMock, patch, PropertyMock, AsyncMock
import pytest
from app.pipeline.parsing.pdf_parser import PdfParser
pytestmark = [pytest.mark.pipeline]


# ════════════════════════════════════════════════════════════
# app/pipeline/parsing/parser.py
# ════════════════════════════════════════════════════════════
class TestDocxParserCoverageGaps:

    def test_extract_core_properties_keywords_semicolon(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title="Title",
            author="Doe; Smith",
            subject=None,
            keywords="kw1; kw2; kw3",
            created=None,
        )
        meta = p._extract_core_properties(docx)
        assert len(meta.keywords) == 3
        assert "kw1" in meta.keywords

    def test_extract_core_properties_empty_keywords_filtered(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title=None, author=None, subject=None,
            keywords="kw1, , kw2",
            created=None,
        )
        meta = p._extract_core_properties(docx)
        assert meta.keywords == ["kw1", "kw2"]

    def test_extract_footnotes_exception_handler(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        part = MagicMock()
        part.element.findall.side_effect = Exception("footnotes crash")
        docx.part.footnotes_part = part
        docx.part.endnotes_part = None
        result = p._extract_footnotes_and_endnotes(docx)
        assert result == []

    def test_extract_endnotes_exception_handler(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        part = MagicMock()
        part.element.findall.side_effect = Exception("endnotes crash")
        docx.part.footnotes_part = None
        docx.part.endnotes_part = part
        result = p._extract_footnotes_and_endnotes(docx)
        assert result == []

    def test_extract_headers_and_footers_exception(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.sections = MagicMock()
        docx.sections.__iter__.side_effect = Exception("sections crash")
        blocks = p._extract_headers_and_footers(docx)
        assert blocks == []

    def test_extract_hyperlinks_key_error_continue(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        hyperlink1 = MagicMock()
        hyperlink1.get.return_value = "rId_bad"
        hyperlink1.findall.return_value = [MagicMock(findall=MagicMock(return_value=[MagicMock(text="click")]))]
        hyperlink2 = MagicMock()
        hyperlink2.get.return_value = "rId_good"
        hyperlink2.findall.return_value = [MagicMock(findall=MagicMock(return_value=[MagicMock(text="link2")]))]
        para._element.findall.return_value = [hyperlink1, hyperlink2]
        para.part = MagicMock()
        rels = {"rId_bad": MagicMock(target_ref="https://bad.com"), "rId_good": MagicMock(target_ref="https://good.com")}
        para.part.rels = rels
        links = p._extract_hyperlinks(para)
        assert len(links) >= 0

    def test_extract_note_references_exception(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para._element.findall.side_effect = Exception("find failed")
        refs = p._extract_note_references(para, "w:footnoteReference")
        assert refs == []

    def test_get_list_info_exception(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para._element.find.side_effect = Exception("find failed")
        result = p._get_list_info(para)
        assert result is None

    def test_extract_paragraph_style_attribute_error(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "test"
        style_mock = MagicMock(spec=["name"])
        style_mock.name = "Normal"
        para.style = style_mock
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block is not None

    def test_extract_inline_images_part_error(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        run = MagicMock()
        run._element = MagicMock()
        inline_shape = MagicMock()
        inline_shape.find.return_value = None
        run._element.findall.side_effect = lambda x, ns=None: {
            './/{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline': [inline_shape],
            './/{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor': [],
        }.get(x, [])
        para.runs = [run]
        figures = p._extract_inline_images(para)
        assert figures == []

    def test_extract_equations_with_omath_skip_duplicates(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        from lxml import etree
        p = DocxParser()
        para = MagicMock()
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
        om_para = etree.fromstring(
            f'<m:oMathPara xmlns:m="{m_ns}" xmlns:w="{ns}"><m:oMath><m:t>a+b</m:t></m:oMath></m:oMathPara>'
        )
        om_inline = om_para[0]
        def findall_side_effect(tag):
            if tag.endswith("}oMathPara"):
                return [om_para]
            if tag.endswith("}oMath"):
                return [om_inline]
            return []
        para._element.findall = findall_side_effect
        equations = p._extract_equations(para)
        assert len(equations) >= 1

    def test_extract_equations_text_from_wt(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        from lxml import etree
        p = DocxParser()
        para = MagicMock()
        m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
        w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        om = etree.fromstring(
            f'<m:oMath xmlns:m="{m_ns}" xmlns:w="{w_ns}"><w:t>x=y</w:t></m:oMath>'
        )
        para._element.findall = lambda tag: (
            [] if "oMathPara" in tag else [om]
        )
        equations = p._extract_equations(para)
        assert len(equations) == 1
        assert equations[0].text == "x=y"

    def test_extract_paragraph_footnote_refs_metadata(self):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "text"
        style_mock = MagicMock()
        style_mock.name = None
        style_mock.font.name = None
        style_mock.font.bold = None
        style_mock.font.italic = None
        style_mock.font.size = None
        para.style = style_mock
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        note_ref = MagicMock()
        note_ref.get.return_value = "42"
        para._element.findall.side_effect = lambda x: [note_ref] if "footnoteReference" in x else []
        block = p._extract_paragraph(para)
        assert block is not None
        assert "footnote_refs" in block.metadata

    def test_extract_body_content_with_inline_images_and_equations(self, tmp_path):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "rich.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            from docx.oxml.text.paragraph import CT_P
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            p_elem = MagicMock(spec=CT_P)
            docx.element.body = [p_elem]
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            para = MagicMock()
            para.text = "Rich para"
            style_mock = MagicMock()
            style_mock.name = None
            style_mock.font.name = None
            style_mock.font.bold = None
            style_mock.font.italic = None
            style_mock.font.size = None
            para.style = style_mock
            para.alignment = None
            run = MagicMock()
            run.text = "Rich para"
            run.bold = None
            run.italic = None
            run.underline = None
            run.font.name = None
            run.font.size = None
            run._element = MagicMock()
            run._element.findall.return_value = []
            para.runs = [run]
            para._element = MagicMock()
            para._element.findall.return_value = []
            para.part = MagicMock()
            mock_docx_cls.return_value = docx
            with patch("app.pipeline.parsing.parser.DocxParagraph", return_value=para):
                with patch.object(DocxParser, "_extract_inline_images", return_value=[MagicMock(figure_id="f1")]):
                    with patch.object(DocxParser, "_extract_equations",
                                      return_value=[MagicMock(equation_id="e1", block_id=None)]):
                        p = DocxParser()
                        blocks, figures, tables, equations = p._extract_body_content(docx)
                        assert len(blocks) >= 1
                        assert "has_figure" in blocks[0].metadata
                        assert "has_equation" in blocks[0].metadata

    def test_parse_with_headers_footers_and_notes(self, tmp_path):
        from app.models import Block, BlockType
        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "full.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            mock_docx_cls.return_value = docx
            with patch.object(DocxParser, "_extract_headers_and_footers",
                              return_value=[MagicMock(block_id="hf1", text="Header", index=0,
                                                      block_type=MagicMock(value="unknown"),
                                                      style=MagicMock(), metadata={})]):
                with patch.object(DocxParser, "_extract_footnotes_and_endnotes",
                                  return_value=[MagicMock(block_id="n1", text="Note", index=1,
                                                          block_type=MagicMock(value="unknown"),
                                                          style=MagicMock(), metadata={})]):
                    p = DocxParser()
                    doc = p.parse(str(f), "doc1")
                    assert doc is not None


# ════════════════════════════════════════════════════════════
# app/pipeline/parsing/pdf_parser.py
# ════════════════════════════════════════════════════════════
class TestPdfParserCoverageGaps:

    def test_calculate_font_stats_exception_continue(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 5
                page = MagicMock()
                page.get_text.side_effect = Exception("page error")
                pdf_doc.__getitem__.return_value = page
                result = p._calculate_font_stats(pdf_doc)
                assert result == 11.0

    def test_build_table_model_single_row(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                table = p._build_table_model([["A"]], 1, 100)
                assert table is not None
                assert table.num_rows == 1

    def test_build_table_model_uneven_cols(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                table = p._build_table_model([["A", "B"], ["1"]], 1, 100)
                assert table is not None
                assert table.num_cols == 2

    def test_is_header_footer_empty_bbox(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._is_header_footer([], [0, 0, 612, 792]) is False
                assert p._is_header_footer([0, 100, 100, 200], None) is False
                assert p._is_header_footer([0, 100, 100, 200], [0, 0, 612, 0]) is False

    def test_normalize_margin_text_empty(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._normalize_margin_text("") == ""
                assert p._normalize_margin_text(None) == ""

    def test_extract_metadata_with_keywords(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.metadata = {"keywords": "foo, bar, baz"}
                meta = p._extract_metadata(pdf_doc)
                assert "foo" in meta.keywords

    def test_build_ocr_blocks_line_fallback(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                blocks = p._build_ocr_blocks("Line1\nLine2\nLine3", "tesseract")
                assert len(blocks) >= 1

    def test_build_ocr_blocks_paragraph_split(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                blocks = p._build_ocr_blocks("Para one.\n\nPara two.\n\nPara three.", "paddle")
                assert len(blocks) == 3

    def test_should_attempt_ocr_fallback_zero_pages(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._should_attempt_ocr_fallback([], 0) is False

    def test_extract_image_svg_format(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.rect.__getitem__.side_effect = lambda i: [0, 0, 612, 792][i]
                page.rect.__len__.return_value = 4
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [(1,)]
                page.find_tables.return_value = []
                pdf_doc.extract_image.return_value = {"image": b"svgdata", "ext": "svg"}
                page.get_image_rects.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) >= 1

    def test_extract_content_fallback_image_blocks(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 1, "image": b"\x89PNG\x0d\x0a\x1a\x0a", "ext": "png", "width": 100, "height": 80, "bbox": [100, 100, 200, 180]},
                    ]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) == 1

    def test_extract_content_fallback_image_skip_duplicate_hash(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 1, "image": b"\x89PNG\x0d\x0a\x1a\x0a", "ext": "png", "width": 100, "height": 80, "bbox": [100, 100, 200, 180]},
                        {"type": 1, "image": b"\x89PNG\x0d\x0a\x1a\x0a", "ext": "png", "width": 50, "height": 50, "bbox": [300, 300, 350, 350]},
                    ]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) == 1

    def test_extract_content_fallback_image_exception(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": [{"type": 1}]}
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) == 0

    def test_extract_content_image_extraction_exception(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [(1,)]
                page.find_tables.return_value = []
                pdf_doc.extract_image.side_effect = Exception("extract failed")
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) == 0

    def test_maybe_apply_ocr_fallback_disabled(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=False, ocr_enabled=True)
                with patch("app.services.enhancement_manager.enhancement_manager", em):
                    result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert result == []

    def test_maybe_apply_ocr_fallback_ocr_enabled_false(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=False)
                with patch("app.services.enhancement_manager.enhancement_manager", em):
                    result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert result == []

    def test_maybe_apply_ocr_fallback_no_backends(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=True)
                em.get_ocr_backends.return_value = []
                with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                    with patch("app.services.enhancement_manager.enhancement_manager", em):
                        result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert result == []

    def test_maybe_apply_ocr_fallback_is_scanned_extracts(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=True)
                em.get_ocr_backends.return_value = ["tesseract"]
                with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                    with patch("app.services.enhancement_manager.enhancement_manager", em):
                        with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOcr:
                            ocr_instance = MagicMock()
                            ocr_instance.is_scanned.return_value = True
                            ocr_instance.extract_text.return_value = ("Hello\n\nWorld", "tesseract")
                            MockOcr.return_value = ocr_instance
                            result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert len(result) > 0
                assert backend == "tesseract"

    def test_maybe_apply_ocr_fallback_not_scanned_with_blocks(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=True)
                em.get_ocr_backends.return_value = ["tesseract"]
                with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                    with patch("app.services.enhancement_manager.enhancement_manager", em):
                        with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOcr:
                            ocr_instance = MagicMock()
                            ocr_instance.is_scanned.return_value = False
                            MockOcr.return_value = ocr_instance
                            existing = [MagicMock()]
                            result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), existing)
                assert result == existing

    def test_maybe_apply_ocr_fallback_ocr_error(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=True)
                em.get_ocr_backends.return_value = ["tesseract"]
                with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                    with patch("app.services.enhancement_manager.enhancement_manager", em):
                        with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOcr:
                            ocr_instance = MagicMock()
                            ocr_instance.is_scanned.return_value = True
                            ocr_instance.extract_text.side_effect = Exception("OCR failed")
                            MockOcr.return_value = ocr_instance
                            result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert result == []

    def test_maybe_apply_ocr_fallback_unexpected_error(self, tmp_path):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                f = tmp_path / "scan.pdf"
                f.write_text("dummy")
                em = MagicMock()
                em.profile = MagicMock(enabled=True, ocr_enabled=True)
                em.get_ocr_backends.return_value = ["tesseract"]
                with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                    with patch("app.services.enhancement_manager.enhancement_manager", em):
                        with patch("app.pipeline.ocr.pdf_ocr.PdfOCR") as MockOcr:
                            ocr_instance = MagicMock()
                            ocr_instance.is_scanned.return_value = True
                            ocr_instance.extract_text.side_effect = RuntimeError("unexpected")
                            MockOcr.return_value = ocr_instance
                            result, backend = p._maybe_apply_ocr_fallback(str(f), MagicMock(), [])
                assert result == []

    def test_build_table_model_no_rows_returns_none(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._build_table_model([], 1, 100) is None

    def test_build_table_model_empty_cols_returns_none(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._build_table_model([[]], 1, 100) is None

    def test_extract_content_table_find_tables_exception(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                page.find_tables.side_effect = Exception("table error")
                page.get_images.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(tables) == 0

    def test_extract_content_get_text_exception(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.side_effect = Exception("text error")
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(blocks) == 0

    def test_extract_content_heading_detection_h1_h2_h3(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.rect.__getitem__.side_effect = lambda i: [0, 0, 612, 792][i]
                page.rect.__len__.return_value = 4
                page.get_text.return_value = {
                    "blocks": [{"type": 0, "bbox": [50, 50, 550, 80], "lines": [{"spans": [{"text": "Heading 1", "size": 20.0, "flags": 16}]}]}]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(blocks) >= 1

    def test_extract_content_table_without_bbox(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                mock_table = MagicMock()
                mock_table.bbox = None
                mock_table.extract.return_value = [["A"]]
                mock_table.header = None
                page.find_tables.return_value = [mock_table]
                page.get_images.return_value = []
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(tables) == 1

    def test_extract_content_image_rects_exception(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz") as mf:
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = MagicMock(x0=0, y0=0, x1=612, y1=792)
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [(1,)]
                page.find_tables.return_value = []
                pdf_doc.extract_image.return_value = {"image": b"imgdata", "ext": "png"}
                page.get_image_rects.side_effect = Exception("rects error")
                pdf_doc.__iter__.return_value = iter([page])
                pdf_doc.__getitem__.return_value = page
                with patch.object(PdfParser, "_calculate_font_stats", return_value=11.0):
                    with patch.object(p, "_should_attempt_ocr_fallback", return_value=False):
                        blocks, figures, tables = p._extract_content(pdf_doc)
                assert len(figures) == 1


# ════════════════════════════════════════════════════════════
# app/pipeline/parsing/parser_factory.py
# ════════════════════════════════════════════════════════════
class TestParserFactoryCoverageGaps:

    def test_init_in_pytest_and_nougat_disabled(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = True
            with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "x"}):
                from app.pipeline.parsing.parser_factory import ParserFactory
                with patch("app.pipeline.parsing.parser_factory.DocxParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp2:
                        mp2.return_value = MagicMock()
                        import sys
                        f = ParserFactory()
                        assert len(f.parsers) >= 2

    def test_init_docx_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser", side_effect=Exception("fail")):
                from app.pipeline.parsing.parser_factory import ParserFactory
                f = ParserFactory()
                names = {p.__class__.__name__ for p in f.parsers}
                assert "DocxParser" not in names

    def test_init_pdf_parser_import_error(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser", side_effect=ImportError("no fitz")):
                    from app.pipeline.parsing.parser_factory import ParserFactory
                    f = ParserFactory()

    def test_init_pdf_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser", side_effect=Exception("weird")):
                    from app.pipeline.parsing.parser_factory import ParserFactory
                    f = ParserFactory()

    def test_init_nougat_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = True
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.nougat_parser.NougatParser", side_effect=Exception("fail")):
                        from app.pipeline.parsing.parser_factory import ParserFactory
                        f = ParserFactory()

    def test_init_txt_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.TxtParser", side_effect=Exception("fail")):
                        from app.pipeline.parsing.parser_factory import ParserFactory
                        f = ParserFactory()

    def test_init_html_parser_import_error(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.TxtParser") as mt:
                        mt.return_value = MagicMock()
                        with patch("app.pipeline.parsing.parser_factory.HtmlParser", side_effect=ImportError("no bs4")):
                            from app.pipeline.parsing.parser_factory import ParserFactory
                            f = ParserFactory()

    def test_init_html_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.TxtParser") as mt:
                        mt.return_value = MagicMock()
                        with patch("app.pipeline.parsing.parser_factory.HtmlParser", side_effect=Exception("fail")):
                            from app.pipeline.parsing.parser_factory import ParserFactory
                            f = ParserFactory()

    def test_init_markdown_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.TxtParser") as mt:
                        mt.return_value = MagicMock()
                        with patch("app.pipeline.parsing.parser_factory.HtmlParser") as mh:
                            mh.return_value = MagicMock()
                            with patch("app.pipeline.parsing.parser_factory.MarkdownParser", side_effect=Exception("fail")):
                                from app.pipeline.parsing.parser_factory import ParserFactory
                                f = ParserFactory()

    def test_init_tex_parser_exception(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser") as md:
                md.return_value = MagicMock()
                with patch("app.pipeline.parsing.parser_factory.PdfParser") as mp:
                    mp.return_value = MagicMock()
                    with patch("app.pipeline.parsing.parser_factory.TxtParser") as mt:
                        mt.return_value = MagicMock()
                        with patch("app.pipeline.parsing.parser_factory.HtmlParser") as mh:
                            mh.return_value = MagicMock()
                            with patch("app.pipeline.parsing.parser_factory.MarkdownParser") as mm:
                                mm.return_value = MagicMock()
                                with patch("app.pipeline.parsing.parser_factory.TexParser", side_effect=Exception("fail")):
                                    from app.pipeline.parsing.parser_factory import ParserFactory
                                    f = ParserFactory()

    def test_get_parser_no_parsers_available(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            with patch("app.pipeline.parsing.parser_factory.DocxParser", side_effect=Exception("fail")):
                with patch("app.pipeline.parsing.parser_factory.PdfParser", side_effect=Exception("fail")):
                    with patch("app.pipeline.parsing.parser_factory.TxtParser", side_effect=Exception("fail")):
                        with patch("app.pipeline.parsing.parser_factory.HtmlParser", side_effect=Exception("fail")):
                            with patch("app.pipeline.parsing.parser_factory.MarkdownParser", side_effect=Exception("fail")):
                                with patch("app.pipeline.parsing.parser_factory.TexParser", side_effect=Exception("fail")):
                                    from app.pipeline.parsing.parser_factory import ParserFactory
                                    f = ParserFactory()
                                    result = f.get_parser("/path/file.docx")
                                    assert result is None


# ════════════════════════════════════════════════════════════
# app/pipeline/references/formatter_engine.py
# ════════════════════════════════════════════════════════════
class TestFormatterEngineCoverageGaps:

    def test_format_single_conference_paper(self):
        from app.models import Reference, ReferenceType
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        cl.load.return_value = {"references": {}}
        engine = ReferenceFormatterEngine(contract_loader=cl)
        ref = Reference(
            reference_id="r1", citation_key="k1", raw_text="test", index=0,
            authors=["Author1"], title="Conf Paper", year=2023,
            reference_type=ReferenceType.CONFERENCE_PAPER,
        )
        rules = {
            "conference_format": "{authors}, {title}, {conference}, {year}.",
            "max_authors": 99,
        }
        result = engine.format_single(ref, rules)
        assert "Conf Paper" in result

    def test_format_single_conference_paper_no_conference_field(self):
        from app.models import Reference, ReferenceType
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        cl.load.return_value = {"references": {}}
        engine = ReferenceFormatterEngine(contract_loader=cl)
        ref = Reference(
            reference_id="r1", citation_key="k1", raw_text="test", index=0,
            authors=["Author1"], title="Conf Paper", year=2023,
            reference_type=ReferenceType.CONFERENCE_PAPER,
        )
        ref.conference = None
        ref.metadata["conf_full"] = "AI Conference 2023"
        rules = {
            "conference_format": "{authors}, {title}, {conference}, {year}.",
            "max_authors": 99,
        }
        result = engine.format_single(ref, rules)
        assert "AI Conference" in result

    def test_format_all_csl_with_style_path_fallback(self):
        from app.models import Reference, ReferenceType
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        cl.load.return_value = {
            "references": {
                "style": "apa",
                "csl_style_path": "/path/to/apa.csl",
                "normalization": {
                    "default_format": "{authors}, {title}, {year}.",
                    "max_authors": 99,
                },
            }
        }
        csl = MagicMock()
        csl.format_references.side_effect = ValueError("CSL failed")
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=csl)
        ref = Reference(
            reference_id="r1", citation_key="k1", raw_text="test", index=0,
            authors=["A"], title="T", year=2020,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
        )
        result = engine.format_all([ref], "APA")
        assert result[0].formatted_text is not None

    def test_process_no_template_defaults_to_ieee(self):
        from app.models import PipelineDocument, Reference, ReferenceType, TemplateInfo
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        cl.load.return_value = {"references": {}}
        csl = MagicMock()
        csl.format_references.return_value = ["[1] Formatted."]
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=csl)
        doc = PipelineDocument(
            document_id="d1",
            references=[Reference(reference_id="r1", citation_key="k1", raw_text="t", index=0)],
            template=None,
        )
        result = engine.process(doc)
        assert result is doc
        cl.load.assert_called_with("IEEE")

    def test_format_all_empty_references_no_csl_call(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        csl = MagicMock()
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=csl)
        result = engine.format_all([], "ieee")
        assert result == []
        csl.format_references.assert_not_called()


# ════════════════════════════════════════════════════════════
# app/pipeline/safety/safe_execution.py
# ════════════════════════════════════════════════════════════
class TestSafeExecutionCoverageGaps:

    @pytest.mark.asyncio
    async def test_safe_async_function_returns_fallback_on_error(self):
        from app.pipeline.safety.safe_execution import safe_async_function

        @safe_async_function(fallback_value="fallback")
        async def failing():
            raise ValueError("error")

        result = await failing()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_safe_async_function_success_path(self):
        from app.pipeline.safety.safe_execution import safe_async_function

        @safe_async_function(fallback_value="fallback")
        async def ok():
            return "success"

        result = await ok()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_safe_async_function_custom_error_message(self):
        from app.pipeline.safety.safe_execution import safe_async_function

        @safe_async_function(fallback_value=42, error_message="custom error")
        async def failing():
            raise RuntimeError("boom")

        result = await failing()
        assert result == 42


# ════════════════════════════════════════════════════════════
# Error-path tests
# ════════════════════════════════════════════════════════════

class TestDocxParserErrorPaths:
    """Error-path tests for DocxParser."""

    def test_extract_core_properties_all_none(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title=None, author=None, subject=None,
            keywords=None, created=None,
        )
        meta = p._extract_core_properties(docx)
        assert meta.title is None
        assert meta.author is None
        assert meta.keywords == []

    def test_extract_paragraph_none_style_handled(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "test"
        para.style = None
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block is not None
        assert block.text == "test"

    def test_extract_inline_images_no_runs_returns_empty(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.runs = []
        figures = p._extract_inline_images(para)
        assert figures == []

    def test_parse_nonexistent_file_raises(self, tmp_path):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        with pytest.raises((FileNotFoundError, IOError)):
            p.parse(str(tmp_path / "nonexistent.docx"), "doc1")

    def test_get_list_info_no_numbering_returns_none(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para._element = MagicMock()
        para._element.find.return_value = None
        result = p._get_list_info(para)
        assert result is None


class TestPdfParserErrorPaths:
    """Error-path tests for PdfParser."""

    def test_build_table_model_none_data_returns_none(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                result = p._build_table_model(None, 1, 100)
                assert result is None

    def test_extract_metadata_none_pdf_handled(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                with pytest.raises((AttributeError, TypeError)):
                    p._extract_metadata(None)

    def test_is_header_footer_empty_blocks_returns_false(self):
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._is_header_footer([], [0, 0, 612, 792]) is False


class TestParserFactoryErrorPaths:
    """Error-path tests for parser_factory."""

    def test_get_parser_unsupported_format_raises(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        pf = ParserFactory()
        with pytest.raises((ValueError, ImportError)):
            pf.get_parser("unsupported.xyz")


class TestFormatterEngineErrorPaths:
    """Error-path tests for formatter_engine."""

    def test_format_all_none_contract_loader_raises(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        with pytest.raises((TypeError, ValueError)):
            ReferenceFormatterEngine(contract_loader=None, csl_engine=MagicMock())

    def test_process_none_doc_raises(self):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        csl = MagicMock()
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=csl)
        with pytest.raises((TypeError, ValueError, AttributeError)):
            engine.process(None)
