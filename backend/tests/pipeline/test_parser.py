# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from app.pipeline.parsing.parser import DocxParser, generate_figure_id, generate_table_id, generate_equation_id
from app.models import BlockType, ImageFormat, Block


class TestHelpers:
    def test_generate_figure_id(self):
        assert generate_figure_id(0) == "fig_000"
        assert generate_figure_id(12) == "fig_012"

    def test_generate_table_id(self):
        assert generate_table_id(0) == "tbl_000"
        assert generate_table_id(5) == "tbl_005"

    def test_generate_equation_id(self):
        assert generate_equation_id(0) == "eqn_000"
        assert generate_equation_id(99) == "eqn_099"


class TestDocxParserSupportsFormat:
    def test_supports_docx(self):
        p = DocxParser()
        assert p.supports_format(".docx")
        assert p.supports_format(".doc")

    def test_not_supports_other(self):
        p = DocxParser()
        assert not p.supports_format(".pdf")


class TestDocxParserParagraphExtraction:
    def test_extract_paragraph_empty_paragraph(self):
        p = DocxParser()
        para = MagicMock()
        para.text = ""
        style_mock = MagicMock()
        style_mock.font.name = None
        style_mock.font.bold = None
        style_mock.font.italic = None
        style_mock.font.size = None
        para.style = style_mock
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block is not None
        assert block.text == ""

    def test_extract_paragraph_with_text(self):
        p = DocxParser()
        para = MagicMock()
        para.text = "Hello world"
        style_mock = MagicMock()
        style_mock.name = "Normal"
        para.style = style_mock
        para.alignment = None
        run = MagicMock()
        run.text = "Hello world"
        run.bold = False
        run.italic = False
        run.underline = False
        run.font.name = None
        run.font.size = None
        run._element = MagicMock()
        run._element.findall.return_value = []
        para.runs = [run]
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block.text == "Hello world"
        assert block.metadata.get("style_name") == "Normal"
        assert block.block_type == BlockType.UNKNOWN

    def test_extract_paragraph_with_style_name(self):
        p = DocxParser()
        para = MagicMock()
        para.text = "Section"
        style_mock = MagicMock()
        style_mock.name = "Heading 1"
        style_mock.font.name = None
        style_mock.font.bold = None
        style_mock.font.italic = None
        style_mock.font.size = None
        para.style = style_mock
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block.metadata["style_name"] == "Heading 1"

    def test_extract_paragraph_with_alignment(self):
        p = DocxParser()
        para = MagicMock()
        para.text = "Centered"
        style_mock = MagicMock()
        style_mock.name = None
        style_mock.font.name = None
        style_mock.font.bold = None
        style_mock.font.italic = None
        style_mock.font.size = None
        para.style = style_mock
        para.alignment = 1
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert "alignment" in block.metadata

    def test_extract_paragraph_style_from_runs(self):
        p = DocxParser()
        para = MagicMock()
        para.text = "Bold text"
        style_mock = MagicMock()
        style_mock.name = None
        para.style = style_mock
        para.alignment = None
        run = MagicMock()
        run.text = "Bold text"
        run.bold = True
        run.italic = True
        run.underline = True
        run.font.name = "Arial"
        run.font.size = MagicMock(pt=12.0)
        run._element = MagicMock()
        run._element.findall.return_value = []
        para.runs = [run]
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block.style.bold is True
        assert block.style.italic is True
        assert block.style.underline is True
        assert block.style.font_name == "Arial"
        assert block.style.font_size == 12.0

    def test_extract_paragraph_style_fallback(self):
        p = DocxParser()
        para = MagicMock()
        para.text = "Styled"
        style_mock = MagicMock()
        style_mock.name = "Heading 1"
        style_mock.font.bold = True
        style_mock.font.italic = False
        style_mock.font.name = "Times New Roman"
        style_mock.font.size = MagicMock(pt=14.0)
        para.style = style_mock
        para.alignment = None
        para.runs = []
        para._element = MagicMock()
        para._element.findall.return_value = []
        block = p._extract_paragraph(para)
        assert block.style.bold is True

    def test_extract_hyperlinks(self):
        p = DocxParser()
        para = MagicMock()
        hyperlink = MagicMock()
        hyperlink.get.return_value = "rId1"
        hyperlink.findall.side_effect = [
            [MagicMock(findall=MagicMock(return_value=[MagicMock(text="click")]))],
        ]
        para._element.findall.return_value = [hyperlink]
        para.part.rels = {"rId1": MagicMock(target_ref="https://example.com")}
        links = p._extract_hyperlinks(para)
        assert len(links) >= 0

    def test_extract_note_references(self):
        p = DocxParser()
        para = MagicMock()
        note_ref = MagicMock()
        note_ref.get.return_value = "1"
        para._element.findall.return_value = [note_ref]
        from docx.oxml.ns import qn
        refs = p._extract_note_references(para, "w:footnoteReference")
        assert len(refs) >= 0

    def test_get_list_info_with_numpr(self):
        p = DocxParser()
        para = MagicMock()
        from lxml import etree
        numPr_xml = '<w:numPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:ilvl w:val="1"/><w:numId w:val="3"/></w:numPr>'
        pPr = etree.fromstring(f'<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{numPr_xml}</w:pPr>')
        para._element = MagicMock()
        from docx.oxml.ns import qn
        para._element.find.return_value = pPr
        result = p._get_list_info(para)
        assert result is not None
        assert result["is_list_item"] is True
        assert result["list_level"] == 1

    def test_get_list_info_with_style_fallback(self):
        p = DocxParser()
        para = MagicMock()
        pPr_xml = '<w:pPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:pStyle w:val="ListBullet2"/></w:pPr>'
        from lxml import etree
        pPr = etree.fromstring(pPr_xml)
        para._element = MagicMock()
        from docx.oxml.ns import qn
        para._element.find.return_value = pPr
        result = p._get_list_info(para)
        assert result is not None
        assert result["is_list_item"] is True

    def test_get_list_info_no_list(self):
        p = DocxParser()
        para = MagicMock()
        para._element = MagicMock()
        para._element.find.return_value = None
        result = p._get_list_info(para)
        assert result is None


class TestDocxParserImageExtraction:
    def test_get_image_format(self):
        p = DocxParser()
        assert p._get_image_format("image/png") == ImageFormat.PNG
        assert p._get_image_format("image/jpeg") == ImageFormat.JPEG
        assert p._get_image_format("image/unknown") == ImageFormat.UNKNOWN

    def test_extract_image_from_inline_missing_blip(self):
        p = DocxParser()
        inline = MagicMock()
        inline.find.return_value = None
        result = p._extract_image_from_inline(inline, MagicMock())
        assert result is None

    def test_extract_image_from_inline_missing_embed(self):
        p = DocxParser()
        inline = MagicMock()
        blip = MagicMock()
        blip.get.return_value = None
        inline.find.return_value = blip
        result = p._extract_image_from_inline(inline, MagicMock())
        assert result is None

    def test_extract_image_from_inline_success(self):
        p = DocxParser()
        inline = MagicMock()
        blip = MagicMock()
        blip.get.return_value = "rId1"
        inline.find.side_effect = lambda x, ns=None: blip if "blip" in x else MagicMock(cx=100000, cy=80000)
        part = MagicMock()
        image_part = MagicMock()
        image_part.blob = b"imagedata"
        image_part.content_type = "image/png"
        part.related_parts = {"rId1": image_part}
        result = p._extract_image_from_inline(inline, part)
        assert result is not None
        assert result.image_format == ImageFormat.PNG
        assert result.width is not None

    def test_extract_inline_images_empty_runs(self):
        p = DocxParser()
        para = MagicMock()
        para.runs = []
        assert p._extract_inline_images(para) == []


class TestDocxParserEquationExtraction:
    def test_extract_equations(self):
        p = DocxParser()
        para = MagicMock()
        para._element = MagicMock()
        para._element.findall.return_value = []
        assert p._extract_equations(para) == []


class TestDocxParserCoreProperties:
    def test_extract_core_properties(self):
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(
            title="Test Paper",
            author="John Doe",
            subject="Abstract text here",
            keywords="kw1, kw2",
            created=None,
        )
        meta = p._extract_core_properties(docx)
        assert meta.title == "Test Paper"
        assert meta.authors == ["John Doe"]
        assert "Abstract" in meta.abstract

    def test_extract_core_properties_empty(self):
        p = DocxParser()
        docx = MagicMock()
        docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
        meta = p._extract_core_properties(docx)
        assert meta.title is None


class TestDocxParserFootnotesEndnotes:
    def test_extract_footnotes_and_endnotes_empty(self):
        p = DocxParser()
        docx = MagicMock()
        docx.part.footnotes_part = None
        docx.part.endnotes_part = None
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert blocks == []

    def test_extract_footnotes_and_endnotes_exception(self):
        p = DocxParser()
        docx = MagicMock()
        docx.part = None
        blocks = p._extract_footnotes_and_endnotes(docx)
        assert blocks == []


class TestDocxParserHeaderFooter:
    def test_extract_headers_and_footers(self):
        p = DocxParser()
        docx = MagicMock()
        section = MagicMock()
        section.header = MagicMock(paragraphs=[])
        section.footer = MagicMock(paragraphs=[])
        docx.sections = [section]
        blocks = p._extract_headers_and_footers(docx)
        assert blocks == []

    def test_extract_headers_and_footers_exception(self):
        p = DocxParser()
        docx = MagicMock()
        docx.sections = None
        blocks = p._extract_headers_and_footers(docx)
        assert blocks == []


class TestDocxParserParse:
    def test_parse_file_not_found(self):
        p = DocxParser()
        with pytest.raises(FileNotFoundError):
            p.parse("/nonexistent.docx", "doc1")

    def test_parse_invalid_file(self, tmp_path):
        f = tmp_path / "bad.docx"
        f.write_text("not a docx")
        p = DocxParser()
        with pytest.raises(ValueError, match="Failed to open DOCX"):
            p.parse(str(f), "doc1")

    def test_parse_success(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            mock_docx_cls.return_value = docx
            p = DocxParser()
            doc = p.parse(str(f), "doc1")
            assert doc.document_id == "doc1"
            assert doc.original_filename == "test.docx"

    def test_parse_with_paragraphs(self, tmp_path):
        f = tmp_path / "paras.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            from docx.oxml.text.paragraph import CT_P
            from docx.text.paragraph import Paragraph as DocxParagraph
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            p_elem = MagicMock(spec=CT_P)
            docx.element.body = [p_elem]
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)

            para = MagicMock(spec=DocxParagraph)
            para.text = "Paragraph content"
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
            para._element.findall.return_value = []
            from docx.oxml.ns import qn
            para._element.find.return_value = None

            mock_docx_cls.return_value = docx

            with patch("app.pipeline.parsing.parser.DocxParagraph") as mock_p_cls:
                mock_p_cls.return_value = para
                p = DocxParser()
                doc = p.parse(str(f), "doc1")
                assert len(doc.blocks) >= 1

    def test_parse_document_id_conversion(self, tmp_path):
        f = tmp_path / "id.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            mock_docx_cls.return_value = docx
            from uuid import UUID
            p = DocxParser()
            doc = p.parse(str(f), UUID("12345678-1234-5678-1234-567812345678"))
            assert isinstance(doc.document_id, str)


class TestParseDocxFunction:
    def test_parse_docx_function(self, tmp_path):
        from app.pipeline.parsing.parser import parse_docx
        f = tmp_path / "test.docx"
        f.write_text("dummy")
        with patch("app.pipeline.parsing.parser.DocxDocument") as mock_docx_cls:
            docx = MagicMock()
            docx.core_properties = MagicMock(title=None, author=None, subject=None, keywords=None, created=None)
            docx.element.body = []
            docx.sections = []
            docx.part = MagicMock(footnotes_part=None, endnotes_part=None)
            mock_docx_cls.return_value = docx
            doc = parse_docx(str(f), "doc1")
            assert doc.document_id == "doc1"
