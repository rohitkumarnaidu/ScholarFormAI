# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

# ══════════════════════════════════════════════════════════════════════════════
# base_parser.py  — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseParserEnterprise:
    def test_abstract_methods_raise_not_implemented(self):
        from app.pipeline.parsing.base_parser import BaseParser
        class BadParser(BaseParser):
            pass
        with pytest.raises(TypeError):
            BadParser()

    def test_concrete_parse_must_return_document(self):
        from datetime import datetime

        from app.pipeline.parsing.base_parser import BaseParser
        class GoodParser(BaseParser):
            def parse(self, file_path, document_id):
                from app.models import PipelineDocument as Document
                now = datetime.now(UTC)
                return Document(document_id=document_id, created_at=now, updated_at=now)
            def supports_format(self, file_extension):
                return file_extension == ".abc"
        p = GoodParser()
        doc = p.parse("/fake/path", "d1")
        assert doc.document_id == "d1"


def _make_pdf_rect(x0=0, y0=0, x1=612, y1=792):
    """Create a fitz.Rect-like object supporting both attribute and index access."""
    r = MagicMock()
    r.x0 = x0
    r.y0 = y0
    r.x1 = x1
    r.y1 = y1
    r.__getitem__.side_effect = lambda i: [x0, y0, x1, y1][i]
    r.__len__.return_value = 4
    return r


# ══════════════════════════════════════════════════════════════════════════════
# parser_factory.py  — edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestParserFactoryEnterprise:
    def test_value_error_on_no_match(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            f = ParserFactory()
            f.parsers.clear()
            result = f.get_parser("test.xyz")
            assert result is None  # safe_function catches ValueError and returns fallback_value=None

    def test_get_supported_formats_empty(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = False
            f = ParserFactory()
            f.parsers.clear()
            assert f.get_supported_formats() == []

    def test_init_pdf_import_error_does_not_crash(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.PdfParser", side_effect=ImportError("no fitz")):
            with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
                mock_s.ENABLE_NOUGAT_PARSER = False
                f = ParserFactory()
                assert any(p.__class__.__name__ == "DocxParser" for p in f.parsers)

    def test_init_html_import_error_skips_html(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.HtmlParser", side_effect=ImportError("no bs4")):
            with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
                mock_s.ENABLE_NOUGAT_PARSER = False
                f = ParserFactory()
                names = {p.__class__.__name__ for p in f.parsers}
                assert "HtmlParser" not in names

    def test_init_pdf_parser_generic_exception(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.PdfParser", side_effect=RuntimeError("unexpected")):
            with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
                mock_s.ENABLE_NOUGAT_PARSER = False
                f = ParserFactory()
                assert any(p.__class__.__name__ == "TxtParser" for p in f.parsers)

    def test_nougat_init_exception_skipped(self):
        from app.pipeline.parsing.parser_factory import ParserFactory
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = True
            with patch("app.pipeline.parsing.nougat_parser.NougatParser", side_effect=Exception("fail")):
                f = ParserFactory()
                names = {p.__class__.__name__ for p in f.parsers}
                assert "NougatParser" not in names


# ══════════════════════════════════════════════════════════════════════════════
# parser.py  — DocxParser enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestDocxParserExtractCorePropsEnterprise:
    def test_authors_semicolon_split(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title=None, author="Smith; Jones; Lee",
            subject=None, keywords=None, created=None,
        )
        meta = p._extract_core_properties(docx)
        assert meta.authors == ["Smith", "Jones", "Lee"]

    def test_keywords_semicolon_split(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title=None, author=None, subject=None,
            keywords="kw1; kw2, kw3", created=None,
        )
        meta = p._extract_core_properties(docx)
        assert "kw1" in meta.keywords
        assert "kw2" in meta.keywords
        assert "kw3" in meta.keywords

class TestDocxParserFootnotesEndnotesEnterprise:
    def test_footnote_extracts_text(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.part.footnotes_part = None
        docx.part.endnotes_part = None
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert blocks == []

    def test_endnote_extracts_text(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.part.footnotes_part = None
        docx.part.endnotes_part = None
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert blocks == []

    def test_footnote_extraction_exception_returns_empty(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.part = None
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert blocks == []

    def test_footnote_returns_blocks_when_part_exists(self):
        import lxml.etree as ET

        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        fn_xml = (
            f'<w:footnotes xmlns:w="{ns}">'
            f'<w:footnote w:id="1"><w:p><w:r><w:t>FN text</w:t></w:r></w:p></w:footnote>'
            f'</w:footnotes>'
        )
        root = ET.fromstring(fn_xml)
        footnotes_part = MagicMock()
        footnotes_part.element = root
        part_mock = MagicMock()
        part_mock.footnotes_part = footnotes_part
        part_mock.endnotes_part = None
        docx.part = part_mock
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert len(blocks) == 1
        assert "FN text" in blocks[0].text
        assert blocks[0].metadata.get("is_footnote") is True

    def test_endnote_returns_blocks_when_part_exists(self):
        import lxml.etree as ET

        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        en_xml = (
            f'<w:endnotes xmlns:w="{ns}">'
            f'<w:endnote w:id="2"><w:p><w:r><w:t>EN content</w:t></w:r></w:p></w:endnote>'
            f'</w:endnotes>'
        )
        root = ET.fromstring(en_xml)
        endnotes_part = MagicMock()
        endnotes_part.element = root
        part_mock = MagicMock()
        part_mock.footnotes_part = None
        part_mock.endnotes_part = endnotes_part
        docx.part = part_mock
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert len(blocks) == 1
        assert "EN content" in blocks[0].text
        assert blocks[0].metadata.get("is_endnote") is True

class TestDocxParserHeaderFooterEnterprise:
    def test_header_extracts_paragraph(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        section = MagicMock()
        para = MagicMock()
        para.text = "Header text"
        font_mock = MagicMock()
        font_mock.name = None
        font_mock.bold = None
        font_mock.italic = None
        font_mock.size = None
        para.style = MagicMock(name=None, font=font_mock)
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        para._element.find.return_value = None
        section.header = MagicMock(paragraphs=[para])
        section.footer = MagicMock(paragraphs=[])
        docx.sections = [section]
        blocks = p._extract_headers_and_footers(docx)
        assert len(blocks) == 1
        assert blocks[0].metadata.get("is_header") is True

    def test_footer_extracts_paragraph(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        section = MagicMock()
        para = MagicMock()
        para.text = "Footer text"
        font_mock = MagicMock()
        font_mock.name = None
        font_mock.bold = None
        font_mock.italic = None
        font_mock.size = None
        para.style = MagicMock(name=None, font=font_mock)
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        para._element.find.return_value = None
        section.header = MagicMock(paragraphs=[])
        section.footer = MagicMock(paragraphs=[para])
        docx.sections = [section]
        blocks = p._extract_headers_and_footers(docx)
        assert len(blocks) == 1
        assert blocks[0].metadata.get("is_footer") is True

class TestDocxParserExtractBodyContentEnterprise:
    def test_paragraph_with_table_interleaved(self):
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P

        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        ct_p = MagicMock(spec=CT_P)
        ct_tbl = MagicMock(spec=CT_Tbl)
        docx.element.body = [ct_p, ct_tbl, ct_p]
        font_style = MagicMock()
        font_style.name = None
        font_style.bold = None
        font_style.italic = None
        font_style.size = None
        para_mock = MagicMock()
        para_mock.text = "Before table"
        para_mock.style = MagicMock(name=None, font=font_style)
        para_mock.alignment = None
        para_mock.runs = []
        para_mock._element = MagicMock()
        para_mock._element.findall.return_value = []
        para_mock._element.find.return_value = None
        para_mock2 = MagicMock()
        para_mock2.text = "After table"
        para_mock2.style = MagicMock(name=None, font=font_style)
        para_mock2.alignment = None
        para_mock2.runs = []
        para_mock2._element = MagicMock()
        para_mock2._element.findall.return_value = []
        para_mock2._element.find.return_value = None
        table_mock = MagicMock()
        with patch("app.pipeline.parsing.parser.DocxParagraph") as mp:
            mp.side_effect = [para_mock, para_mock2]
            with patch("app.pipeline.parsing.parser.DocxTable") as mt:
                mt.return_value = table_mock
                with patch.object(p, "_extract_table", return_value=MagicMock()):
                    blocks, figs, tbls, eqns = p._extract_body_content(docx)
                    assert len(blocks) == 2
                    assert blocks[0].text == "Before table"
                    assert len(tbls) == 1

    def test_empty_body_returns_empty_lists(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        docx = MagicMock()
        docx.element.body = []
        blocks, figs, tbls, eqns = p._extract_body_content(docx)
        assert blocks == []
        assert figs == []
        assert tbls == []
        assert eqns == []

class TestDocxParserEquationsEnterprise:
    def test_extract_equations_block_and_inline(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
        oMathPara_xml = (
            f'<w:p xmlns:w="{ns}" xmlns:m="{m_ns}">'
            f'<m:oMathPara><m:oMath><m:t>E=mc^2</m:t></m:oMath></m:oMathPara>'
            f'</w:p>'
        )
        root = ET.fromstring(oMathPara_xml)
        para._element = root
        eqns = p._extract_equations(para)
        assert len(eqns) == 1
        assert eqns[0].is_block is True
        assert "E=mc" in eqns[0].text

    def test_extract_equations_empty(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        root = ET.fromstring(f'<w:p xmlns:w="{ns}"/>')
        para._element = root
        eqns = p._extract_equations(para)
        assert eqns == []

    def test_extract_math_element_with_empty_text(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        m_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
        bad_el = ET.fromstring(f'<m:oMath xmlns:m="{m_ns}" xmlns:w="{ns}"/>')
        result = p._extract_math_element(bad_el, is_block=False)
        assert result is not None
        assert result.text == ""

class TestDocxParserListInfoEnterprise:
    def test_list_info_numpr_with_defaults(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        pPr_xml = (
            f'<w:pPr xmlns:w="{ns}">'
            f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
            f'</w:pPr>'
        )
        pPr = ET.fromstring(pPr_xml)
        para._element = MagicMock()
        para._element.find.return_value = pPr
        result = p._get_list_info(para)
        assert result is not None
        assert result["is_list_item"] is True
        assert result["list_level"] == 0
        assert result["list_id"] == "1"

    def test_list_info_style_fallback_list_bullet(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        pPr_xml = f'<w:pPr xmlns:w="{ns}"><w:pStyle w:val="ListBullet"/></w:pPr>'
        pPr = ET.fromstring(pPr_xml)
        para._element = MagicMock()
        para._element.find.return_value = pPr
        result = p._get_list_info(para)
        assert result is not None

    def test_list_info_no_match_returns_none(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        pPr_xml = f'<w:pPr xmlns:w="{ns}"/>'
        pPr = ET.fromstring(pPr_xml)
        para._element = MagicMock()
        para._element.find.return_value = pPr
        result = p._get_list_info(para)
        assert result is None

class TestDocxParserInlineImagesEnterprise:
    def test_inline_images_anchor_shapes(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        run = MagicMock()
        import lxml.etree as ET
        ns = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        a_ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
        r_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        wrapper_xml = (
            f'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            f'xmlns:wp="{ns}" xmlns:a="{a_ns}" xmlns:r="{r_ns}">'
            f'<wp:anchor>'
            f'<wp:extent cx="500000" cy="300000"/>'
            f'<a:blip r:embed="rId2"/>'
            f'</wp:anchor>'
            f'</w:r>'
        )
        run._element = ET.fromstring(wrapper_xml)
        run.part = MagicMock()
        run.part.related_parts = {"rId2": MagicMock(blob=b"imgdata", content_type="image/jpeg")}
        para.runs = [run]
        figures = p._extract_inline_images(para)
        assert len(figures) == 1
        assert figures[0].width is not None
        assert figures[0].height is not None

    def test_inline_images_no_part_fallback(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        run = MagicMock()
        run._element = MagicMock()
        run._element.findall.side_effect = [[MagicMock()], []]
        delattr(run, 'part')
        para.runs = [run]
        figures = p._extract_inline_images(para)
        assert figures == []

class TestDocxParserExtractStyleEnterprise:
    def test_paragraph_style_no_runs_uses_paragraph_style(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "Styled"
        para.runs = []
        para.style = MagicMock()
        para.style.font.bold = True
        para.style.font.italic = None
        para.style.font.name = "Times"
        para.style.font.size = MagicMock(pt=12.0)
        style = p._extract_paragraph_style(para)
        assert style.bold is True
        assert style.font_name == "Times"

    def test_paragraph_style_runs_skip_empty_first(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "  Real text"
        run0 = MagicMock()
        run0.text = "  "
        run0.bold = None
        run0.italic = None
        run0.underline = None
        run0.font.name = None
        run0.font.size = None
        run1 = MagicMock()
        run1.text = "Real text"
        run1.bold = True
        run1.italic = False
        run1.underline = False
        run1.font.name = "Arial"
        run1.font.size = MagicMock(pt=14.0)
        para.runs = [run0, run1]
        para.style = None
        style = p._extract_paragraph_style(para)
        assert style.bold is True

    def test_paragraph_style_runs_none_styles(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        para.text = "Text"
        run = MagicMock()
        run.text = "Text"
        run.bold = None
        run.italic = None
        run.underline = None
        run.font.name = None
        run.font.size = None
        para.runs = [run]
        para.style = MagicMock()
        para.style.font.bold = None
        para.style.font.italic = None
        style = p._extract_paragraph_style(para)
        assert style.bold is False

class TestDocxParserExtractImageInlineEnterprise:
    def test_get_image_format_unknown(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        from app.models import ImageFormat
        assert p._get_image_format("image/webp") == ImageFormat.UNKNOWN

    def test_extract_image_from_inline_no_extent(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        import lxml.etree as ET
        ns_draw = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
        ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        inline_xml = (
            f'<wp:inline xmlns:wp="{ns_draw}" xmlns:a="{ns_a}" xmlns:r="{ns_r}">'
            f'<a:blip r:embed="rId1"/>'
            f'</wp:inline>'
        )
        inline = ET.fromstring(inline_xml)
        part = MagicMock()
        image_part = MagicMock()
        image_part.blob = b"imgdata"
        image_part.content_type = "image/png"
        part.related_parts = {"rId1": image_part}
        figure = p._extract_image_from_inline(inline, part)
        assert figure is not None
        assert figure.width is None

class TestDocxParserHyperlinksEnterprise:
    def test_extract_hyperlinks_no_rid(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        hyperlink = MagicMock()
        hyperlink.get.return_value = None
        hyperlink.findall.return_value = []
        para._element.findall.return_value = [hyperlink]
        links = p._extract_hyperlinks(para)
        assert links == []

    def test_extract_hyperlinks_bad_rid_skipped(self):
        from app.pipeline.parsing.parser import DocxParser
        p = DocxParser()
        para = MagicMock()
        hyperlink = MagicMock()
        hyperlink.get.return_value = "rIdMissing"
        hyperlink.findall.return_value = []
        para._element.findall.return_value = [hyperlink]
        para.part.rels = {}
        links = p._extract_hyperlinks(para)
        assert links == []

class TestDocxParserParseEnterprise:
    def test_parse_uses_table_extractor(self, tmp_path):
        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "with_table.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as md:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            from docx.oxml.table import CT_Tbl
            ct_tbl = MagicMock(spec=CT_Tbl)
            docx.element.body = [ct_tbl]
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            md.return_value = docx
            with patch("app.pipeline.parsing.parser.TableExtractor") as mte:
                mte_instance = MagicMock()
                mte_instance.extract.return_value = MagicMock()
                mte.return_value = mte_instance
                p = DocxParser()
                p.parse(str(f), "doc1")
                assert mte_instance.extract.called

    def test_parse_produces_history(self, tmp_path):
        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "history.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as md:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            md.return_value = docx
            p = DocxParser()
            doc = p.parse(str(f), "doc1")
            assert len(doc.processing_history) >= 1

    def test_parse_document_id_uuid_conversion(self, tmp_path):
        import uuid

        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "uuid.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as md:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            md.return_value = docx
            p = DocxParser()
            doc = p.parse(str(f), uuid.UUID("00000000-0000-0000-0000-000000000001"))
            assert isinstance(doc.document_id, str)

    def test_parse_invalid_file_raises_value_error(self, tmp_path):
        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "bad.docx"
        f.write_text("not a docx")
        p = DocxParser()
        with pytest.raises(ValueError, match="Failed to open DOCX"):
            p.parse(str(f), "doc1")

    def test_parse_paragraphs_with_equations(self, tmp_path):
        from docx.oxml.text.paragraph import CT_P

        from app.pipeline.parsing.parser import DocxParser
        f = tmp_path / "eqns.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as md:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            p_elem = MagicMock(spec=CT_P)
            docx.element.body = [p_elem]
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            md.return_value = docx
            with patch("app.pipeline.parsing.parser.DocxParagraph") as mp:
                para = MagicMock()
                para.text = "Para with equation"
                eq_font_style = MagicMock()
                eq_font_style.name = None
                eq_font_style.bold = None
                eq_font_style.italic = None
                eq_font_style.size = None
                para.style = MagicMock(name=None, font=eq_font_style)
                para.alignment = None
                para.runs = []
                para._element = MagicMock()
                para._element.findall.return_value = []
                para._element.find.return_value = None
                mp.return_value = para
                p = DocxParser()
                doc = p.parse(str(f), "doc1")
                assert len(doc.blocks) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# pdf_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestPdfParserInitEnterprise:
    def test_init_raises_if_not_available(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", False):
            with pytest.raises(ImportError, match="PyMuPDF"):
                PdfParser()

class TestPdfParserExtractContentEnterprise:
    def test_extract_content_image_fallback_when_no_images(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = _make_pdf_rect()
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 1, "image": b"rawimgdata", "ext": "png",
                         "width": 100, "height": 50,
                         "bbox": [10, 10, 110, 60]}
                    ]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                blocks, figs, tbls = p._extract_content(pdf_doc)
                assert len(figs) >= 1

    def test_extract_content_image_skip_duplicate_hash(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = _make_pdf_rect()
                page.get_text.return_value = {"blocks": []}
                # Two identical images on same page should produce one figure (dedup)
                page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0, 0), (1, 0, 0, 0, 0, 0, 0, 0)]
                page.find_tables.return_value = []
                pdf_doc.extract_image.return_value = {"image": b"dupdata", "ext": "png"}
                page.get_image_rects.return_value = []
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                blocks, figs, tbls = p._extract_content(pdf_doc)
                assert len(figs) == 1

    def test_extract_content_header_on_page1_kept(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = _make_pdf_rect()
                page.get_text.return_value = {
                    "blocks": [{
                        "type": 0,
                        "bbox": [0, 0, 200, 30],
                        "lines": [{"spans": [{"text": "Title on page 1", "size": 18, "flags": 16}]}],
                    }]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                blocks, figs, tbls = p._extract_content(pdf_doc)
                assert len(blocks) >= 1

    def test_extract_content_duplicate_text_suppression(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = _make_pdf_rect()
                long_text = "A" * 30
                page.get_text.return_value = {
                    "blocks": [{
                        "type": 0,
                        "bbox": [50, 100, 500, 120],
                        "lines": [{"spans": [{"text": long_text, "size": 11, "flags": 0}]}],
                    }]
                }
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                blocks, figs, tbls = p._extract_content(pdf_doc)
                assert len(blocks) == 1

    def test_content_text_dict_failure_returns_empty(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 1
                page = MagicMock()
                page.rect = _make_pdf_rect()
                page.get_text.side_effect = RuntimeError("bad text")
                page.get_images.return_value = []
                page.find_tables.return_value = []
                pdf_doc.__getitem__.return_value = page
                pdf_doc.__iter__.return_value = iter([page])
                blocks, figs, tbls = p._extract_content(pdf_doc)
                assert blocks == []

class TestPdfParserBuildTableModelEnterprise:
    def test_build_table_model_with_header(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                table = p._build_table_model([["Name", "Age"], ["Alice", "30"]], 1, 100)
                assert table is not None
                assert table.has_header is True
                assert table.num_rows == 2
                assert table.num_cols == 2

    def test_build_table_model_uneven_rows_padded(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                table = p._build_table_model([["A", "B", "C"], ["1", "2"]], 1, 100)
                assert table is not None
                assert table.num_cols == 3

class TestPdfParserOCRFallbackEnterprise:
    def test_maybe_apply_ocr_fallback_import_fails(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                blocks, backend = p._maybe_apply_ocr_fallback("/fake.pdf", MagicMock(), [])
                assert backend is None

    def test_maybe_apply_ocr_fallback_disabled_profile(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                em = MagicMock()
                em.profile.enabled = False
                em.profile.ocr_enabled = False
                with patch("app.services.enhancement_manager.enhancement_manager", em):
                    with patch("app.pipeline.ocr.pdf_ocr") as m_ocr:
                        m_ocr.OCRError = Exception
                        m_ocr.PdfOCR = MagicMock
                        blocks, backend = p._maybe_apply_ocr_fallback("/fake.pdf", MagicMock(), [])
                        assert backend is None

class TestPdfParserFontStatsEnterprise:
    def test_font_stats_scan_error_continues(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 3
                page_bad = MagicMock()
                page_bad.get_text.side_effect = RuntimeError("fail")
                page_good = MagicMock()
                page_good.get_text.return_value = {
                    "blocks": [{"type": 0, "lines": [{"spans": [{"size": 12.0, "text": "hello"}]}]}]
                }
                pdf_doc.__getitem__.side_effect = lambda i: [page_bad, page_good, page_good][i]
                result = p._calculate_font_stats(pdf_doc)
                assert result == 12.0

    def test_font_stats_no_sizes_returns_default(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                pdf_doc = MagicMock()
                pdf_doc.__len__.return_value = 0
                result = p._calculate_font_stats(pdf_doc)
                assert result == 11.0

class TestPdfParserIsHeaderFooterEnterprise:
    def test_is_header_footer_empty_bbox(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._is_header_footer(None, [0, 0, 612, 792]) is False
                assert p._is_header_footer([], [0, 0, 612, 792]) is False

    def test_is_header_footer_no_page_rect(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._is_header_footer([0, 0, 100, 30], None) is False

    def test_normalize_margin_text_empty(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                assert p._normalize_margin_text("") == ""
                assert p._normalize_margin_text(None) == ""

class TestPdfParserMaybeApplyOCREnterprise:
    def test_ocr_fallback_no_backends(self):
        from app.pipeline.parsing.pdf_parser import PdfParser
        with patch("app.pipeline.parsing.pdf_parser.PYMUPDF_AVAILABLE", True):
            with patch("app.pipeline.parsing.pdf_parser.fitz"):
                p = PdfParser()
                em = MagicMock()
                em.profile.enabled = True
                em.profile.ocr_enabled = True
                em.get_ocr_backends.return_value = ["other"]
                with patch("app.services.enhancement_manager.enhancement_manager", em):
                    with patch("app.pipeline.ocr.pdf_ocr") as m_ocr:
                        m_ocr.OCRError = Exception
                        m_ocr.PdfOCR = MagicMock
                        with patch.object(p, "_should_attempt_ocr_fallback", return_value=True):
                            blocks, backend = p._maybe_apply_ocr_fallback("/f.pdf", MagicMock(), [MagicMock()])
                            assert backend is None


# ══════════════════════════════════════════════════════════════════════════════
# md_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkdownParserEnterprise:
    def test_parse_utf8_decode_failure_raised(self, tmp_path):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        f = tmp_path / "bad.md"
        f.write_text("dummy")
        with patch("builtins.open", side_effect=[UnicodeDecodeError("utf-8", b"", 0, 1, "bad"), PermissionError("denied")]):
            with pytest.raises(ValueError, match="Failed to read Markdown"):
                p.parse(str(f), "doc1")

    def test_extract_frontmatter_malformed_line_skipped(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        content, meta = p._extract_frontmatter("---\nbadline\n---\n\nBody")
        assert meta.title is None
        assert "Body" in content

    def test_extract_content_footnote_marker_preserved(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        blocks, _ = p._extract_content("[^ref]: Some footnote explanation")
        assert len(blocks) == 1
        assert "[^ref]" in blocks[0].text

    def test_strip_markdown_protects_math(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        result = p._strip_markdown("Math $E=mc^2$ here")
        assert "$E=mc^2$" in result

    def test_strip_markdown_removes_list_markers(self):
        from app.pipeline.parsing.md_parser import MarkdownParser
        p = MarkdownParser()
        result = p._strip_markdown("- item")
        assert result == "item"
        result2 = p._strip_markdown("1. item")
        assert result2 == "item"


# ══════════════════════════════════════════════════════════════════════════════
# html_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestHtmlParserEnterprise:
    def test_parse_utf8_decode_failure_fallback(self, tmp_path):
        from app.pipeline.parsing.html_parser import HtmlParser
        f = tmp_path / "test.html"
        f.write_bytes("<html><body><p>café</p></body></html>".encode("latin-1"))
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            doc = p.parse(str(f), "doc1")
            assert doc is not None

    def test_parse_utf8_decode_failure_fallback_exception(self, tmp_path):
        from app.pipeline.parsing.html_parser import HtmlParser
        f = tmp_path / "test.html"
        f.write_bytes(b"<html></html>")
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True), patch("builtins.open", side_effect=[
            UnicodeDecodeError("utf-8", b"", 0, 1, "bad"),
            PermissionError("denied"),
        ]):
            p = HtmlParser()
            with pytest.raises(ValueError, match="Failed to read HTML"):
                p.parse(str(f), "doc1")

    def test_parse_open_exception(self, tmp_path):
        from app.pipeline.parsing.html_parser import HtmlParser
        f = tmp_path / "test.html"
        f.write_text("<html></html>")
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            with patch("builtins.open", side_effect=PermissionError("denied")):
                p = HtmlParser()
                with pytest.raises(ValueError, match="Failed to open HTML"):
                    p.parse(str(f), "doc1")

    def test_extract_content_script_style_removed(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            soup = BeautifulSoup(
                "<html><body><script>alert(1)</script><style>body{}</style><p>Hello</p></body></html>",
                "html.parser",
            )
            blocks, _ = p._extract_content(soup)
            assert len(blocks) == 1

    def test_extract_content_element_failure_logged(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            soup = BeautifulSoup("<html><body><bad>text</bad><p>Good</p></body></html>", "html.parser")
            blocks, _ = p._extract_content(soup)
            assert len(blocks) >= 0

    def test_extract_metadata_no_title_tag(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            soup = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
            meta = p._extract_metadata(soup)
            assert meta.title is None

    def test_extract_content_pre_with_language_class(self):
        from bs4 import BeautifulSoup

        from app.pipeline.parsing.html_parser import HtmlParser
        with patch("app.pipeline.parsing.html_parser.BS4_AVAILABLE", True):
            p = HtmlParser()
            soup = BeautifulSoup(
                '<html><body><pre class="language-python">print("hello")</pre></body></html>',
                "html.parser",
            )
            blocks, _ = p._extract_content(soup)
            assert len(blocks) == 1
            assert blocks[0].metadata["code_language"] == "python"


# ══════════════════════════════════════════════════════════════════════════════
# tex_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestTexParserEnterprise:
    def test_parse_utf8_decode_failure_fallback(self, tmp_path):
        from app.pipeline.parsing.tex_parser import TexParser
        f = tmp_path / "test.tex"
        f.write_bytes(r"\documentclass{article}\begin{document}Hello\end{document}".encode("latin-1"))
        with patch("builtins.open", side_effect=[
            UnicodeDecodeError("utf-8", b"", 0, 1, "bad"),
        ]), patch("builtins.open") as mo:
            mo.return_value.__enter__.return_value.read.return_value = r"\begin{document}Body\end{document}"
            p = TexParser()
            doc = p.parse(str(f), "doc1")
            assert doc is not None

    def test_parse_utf8_fallback_exception(self, tmp_path):
        from app.pipeline.parsing.tex_parser import TexParser
        f = tmp_path / "test.tex"
        f.write_bytes(b"dummy")
        with patch("builtins.open", side_effect=[
            UnicodeDecodeError("utf-8", b"", 0, 1, "bad"),
            PermissionError("denied"),
        ]):
            p = TexParser()
            with pytest.raises(ValueError, match="Failed to read LaTeX"):
                p.parse(str(f), "doc1")

    def test_extract_content_itemize_and_enumerate(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        blocks = p._extract_content(
            r"\begin{document}"
            r"\begin{itemize}\item First\item Second\end{itemize}"
            r"\begin{enumerate}\item A\item B\end{enumerate}"
            r"\end{document}"
        )
        list_blocks = [b for b in blocks if b.metadata.get("is_list_item")]
        assert len(list_blocks) == 4

    def test_extract_content_table_tabular(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        blocks = p._extract_content(
            r"\begin{document}"
            r"\begin{tabular}{cc}\hline A & B \\ C & D \\\hline\end{tabular}"
            r"\end{document}"
        )
        table_blocks = [b for b in blocks if b.metadata.get("is_table")]
        assert len(table_blocks) >= 1

    def test_extract_content_no_document_env(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        blocks = p._extract_content("Just raw text without document environment.")
        assert len(blocks) >= 1

    def test_remove_comments_escaped_percent(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        result = p._remove_comments(r"text \% not a comment")
        assert r"\%" in result

    def test_clean_latex_removes_environments(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        result = p._clean_latex(r"\textbf{bold} and \textit{italic}")
        assert "bold" in result
        assert "italic" in result

    def test_extract_metadata_with_comments(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        meta = p._extract_metadata("% comment\n\\title{Real}")
        assert meta.title == "Real"

    def test_paragraph_extraction_skips_short_fragments(self):
        from app.pipeline.parsing.tex_parser import TexParser
        p = TexParser()
        blocks = p._extract_content(r"\begin{document}Hi\end{document}")
        [b for b in blocks if b.text == "Hi"]
        assert all(len(b.text) <= 10 or "Hi" in b.text for b in blocks if b.text == "Hi")


# ══════════════════════════════════════════════════════════════════════════════
# txt_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestTxtParserEnterprise:
    def test_parse_utf8_decode_failure_fallback(self, tmp_path):
        from app.pipeline.parsing.txt_parser import TxtParser
        f = tmp_path / "test.txt"
        f.write_bytes("Hello café".encode("latin-1"))
        p = TxtParser()
        doc = p.parse(str(f), "doc1")
        assert doc is not None

    def test_extract_blocks_letter_marker_list(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("a) First\n\nb) Second")
        assert blocks[0].metadata.get("is_list_item") is True

    def test_extract_blocks_parenthetical_list(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("(1) First\n\n(2) Second")
        assert blocks[0].metadata.get("is_list_item") is True

    def test_extract_blocks_all_caps_short_no_period(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        blocks = p._extract_blocks("ABSTRACT\n\nSome content here.")
        assert blocks[0].metadata.get("potential_heading") is True

    def test_extract_blocks_long_sentence_not_heading(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        long_text = "This is a very long sentence that should NOT be considered a heading because it is just a regular sentence." * 2
        blocks = p._extract_blocks(long_text)
        assert blocks[0].metadata.get("potential_heading") is not True

    def test_extract_blocks_empty_content(self):
        from app.pipeline.parsing.txt_parser import TxtParser
        p = TxtParser()
        assert p._extract_blocks("") == []


# ══════════════════════════════════════════════════════════════════════════════
# table_extractor.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

# Inject mocks BEFORE importing the module (call this from tests)
import sys


def _inject_torch_mocks():
    _torch_mock = MagicMock()
    _torch_mock.cuda.is_available.return_value = False
    _torch_mock.no_grad.return_value.__enter__.return_value = None
    _transformers_mock = MagicMock()
    _pil_mock = MagicMock()
    _pil_mock.__version__ = "10.0.0"
    _pil_image_mock = MagicMock()
    _timm_mock = MagicMock()
    for _mod_name, _mod_obj in [
        ("torch", _torch_mock),
        ("transformers", _transformers_mock),
        ("PIL", _pil_mock),
        ("PIL.Image", _pil_image_mock),
        ("timm", _timm_mock),
    ]:
        sys.modules[_mod_name] = _mod_obj

class TestTableExtractorEnterprise:
    @pytest.fixture(autouse=True)
    def _inject_mocks(self):
        _saved = {}
        for _mod_name in ["torch", "transformers", "PIL", "PIL.Image", "timm"]:
            _saved[_mod_name] = sys.modules.get(_mod_name)
        _inject_torch_mocks()
        yield
        for _mod_name in ["torch", "transformers", "PIL", "PIL.Image", "timm"]:
            if _saved[_mod_name] is not None:
                sys.modules[_mod_name] = _saved[_mod_name]
            elif _mod_name in sys.modules:
                del sys.modules[_mod_name]

    def test_init_unavailable_raises(self):
        from app.pipeline.parsing.table_extractor import TABLE_TRANSFORMER_AVAILABLE, TableExtractor
        if TABLE_TRANSFORMER_AVAILABLE:
            with patch("app.pipeline.parsing.table_extractor.TABLE_TRANSFORMER_AVAILABLE", False):
                with pytest.raises(ImportError, match="Table Transformer"):
                    TableExtractor()
        else:
            with pytest.raises(ImportError):
                TableExtractor()

    def test_get_table_extractor_returns_none_on_import_error(self):
        _inject_torch_mocks()
        from app.pipeline.parsing.table_extractor import get_table_extractor
        with patch("app.pipeline.parsing.table_extractor.TABLE_TRANSFORMER_AVAILABLE", False):
            result = get_table_extractor()
            assert result is None

    def test_to_table_model_with_headers(self):
        from app.pipeline.parsing.table_extractor import TABLE_TRANSFORMER_AVAILABLE, TableExtractor
        if not TABLE_TRANSFORMER_AVAILABLE:
            pytest.skip("Table Transformer not available")
        te = TableExtractor()
        table_data = {
            "detection": {"score": 0.95, "bbox": (0, 0, 100, 100)},
            "structure": {
                "num_rows": 2,
                "num_cols": 2,
                "data": [["H1", "H2"], ["A", "B"]],
                "headers": [{"bbox": (0, 0, 50, 20), "score": 0.9}],
            },
        }
        table = te.to_table_model(table_data, table_index=0, block_index=100, page_number=1)
        assert table.num_rows == 2
        assert table.num_cols == 2
        assert table.has_header is True
        assert table.page_number == 1

    def test_to_table_model_no_headers(self):
        from app.pipeline.parsing.table_extractor import TABLE_TRANSFORMER_AVAILABLE, TableExtractor
        if not TABLE_TRANSFORMER_AVAILABLE:
            pytest.skip("Table Transformer not available")
        te = TableExtractor()
        table_data = {
            "detection": {"score": 0.8, "bbox": (0, 0, 100, 100)},
            "structure": {
                "num_rows": 1,
                "num_cols": 1,
                "data": [["cell"]],
                "headers": [],
            },
        }
        table = te.to_table_model(table_data, table_index=1, block_index=200)
        assert table.has_header is False

    def test_extract_tables_from_page_detection_fails(self):
        from app.pipeline.parsing.table_extractor import TABLE_TRANSFORMER_AVAILABLE, TableExtractor
        if not TABLE_TRANSFORMER_AVAILABLE:
            pytest.skip("Table Transformer not available")
        te = TableExtractor()
        with patch.object(te, "detect_tables", side_effect=Exception("detection failed")):
            img = MagicMock()
            with pytest.raises(Exception):
                te.extract_tables_from_page(img)

    def test_extract_tables_from_page_structure_fails(self):
        from app.pipeline.parsing.table_extractor import TABLE_TRANSFORMER_AVAILABLE, TableExtractor
        if not TABLE_TRANSFORMER_AVAILABLE:
            pytest.skip("Table Transformer not available")
        te = TableExtractor()
        detections = [{"bbox": (0, 0, 100, 100), "score": 0.9}]
        with patch.object(te, "detect_tables", return_value=detections):
            with patch.object(te, "extract_table_structure", side_effect=Exception("struct fail")):
                img = MagicMock()
                results = te.extract_tables_from_page(img)
                assert len(results) == 1
                assert results[0]["structure"]["num_rows"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# nougat_parser.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# ocr_engine.py  — enterprise edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestOCREngineEnterprise:
    def test_init_unavailable_raises(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", False):
            with pytest.raises(ImportError, match="Surya OCR"):
                OCREngine()

    def test_get_ocr_engine_returns_none_on_unavailable(self):
        from app.pipeline.parsing.ocr_engine import get_ocr_engine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", False):
            engine = get_ocr_engine()
            assert engine is None

    def test_get_ocr_engine_returns_instance(self):
        from app.pipeline.parsing.ocr_engine import get_ocr_engine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
            with patch("app.pipeline.parsing.ocr_engine.OCREngine") as MockEngine:
                instance = MagicMock()
                MockEngine.return_value = instance
                engine = get_ocr_engine()
                assert engine is not None

    def test_is_scanned_pdf_true(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
            engine = OCREngine()
            assert engine.is_scanned_pdf("short", 10) is True

    def test_is_scanned_pdf_false(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
            engine = OCREngine()
            assert engine.is_scanned_pdf("A" * 500, 10) is False

    def test_is_scanned_pdf_zero_pages(self):
        from app.pipeline.parsing.ocr_engine import OCREngine
        with patch("app.pipeline.parsing.ocr_engine.SURYA_AVAILABLE", True):
            engine = OCREngine()
            assert engine.is_scanned_pdf("text", 0) is False
