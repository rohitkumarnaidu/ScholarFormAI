# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.services.docling_client import (
    BoundingBox,
    DoclingClient,
    LayoutElement,
)


class TestBoundingBox:
    def test_basic_creation(self):
        b = BoundingBox(10, 20, 100, 200, page=1)
        assert b.x0 == 10
        assert b.y0 == 20
        assert b.x1 == 100
        assert b.y1 == 200
        assert b.page == 1

    def test_width(self):
        b = BoundingBox(10, 20, 100, 200)
        assert b.width == 90

    def test_height(self):
        b = BoundingBox(10, 20, 100, 200)
        assert b.height == 180

    def test_center_y(self):
        b = BoundingBox(0, 0, 100, 200)
        assert b.center_y == 100

    def test_to_dict(self):
        b = BoundingBox(0, 0, 100, 200)
        d = b.to_dict()
        assert d["x0"] == 0
        assert d["width"] == 100


class TestLayoutElement:
    def test_basic_creation(self):
        bbox = BoundingBox(0, 0, 100, 50)
        elem = LayoutElement(
            text="Hello",
            bbox=bbox,
            element_type="paragraph",
            font_size=12.0,
            is_bold=False,
        )
        assert elem.text == "Hello"
        assert elem.font_size == 12.0
        assert elem.element_type == "paragraph"

    def test_to_dict(self):
        bbox = BoundingBox(0, 0, 100, 50)
        elem = LayoutElement(text="Test", bbox=bbox, element_type="title")
        d = elem.to_dict()
        assert d["type"] == "title"
        assert d["text"] == "Test"


class TestDoclingClientInit:
    @patch("app.pipeline.services.docling_client._load_docling_converter", return_value=None)
    def test_init_not_available(self, mock_load):
        c = DoclingClient()
        assert c.is_available() is False
        assert c.converter is None

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_init_available(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_inst = MagicMock()
        mock_conv_cls.return_value = mock_inst
        mock_load.return_value = mock_conv_cls
        c = DoclingClient()
        assert c.is_available() is True
        assert c.converter is not None

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_init_fails_gracefully(self, mock_load):
        mock_conv_cls = MagicMock(side_effect=Exception("Init failed"))
        mock_load.return_value = mock_conv_cls
        c = DoclingClient()
        assert c.is_available() is False


class TestDoclingClientAnalyzeLayout:
    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_not_available(self, mock_load):
        mock_load.return_value = None
        c = DoclingClient()
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []
        assert result["pages"] == 0

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_with_text_elements(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_conv = MagicMock()
        mock_conv_cls.return_value = mock_conv
        mock_load.return_value = mock_conv_cls

        # Mock Docling document
        mock_doc = MagicMock()

        # Mock a text item
        mock_text_item = MagicMock()
        mock_text_item.text = "Test Heading"
        mock_text_item.label = "section_header"
        mock_text_item.level = 1
        mock_prov = MagicMock()
        mock_prov.bbox.l = 0
        mock_prov.bbox.t = 10
        mock_prov.bbox.r = 500
        mock_prov.bbox.b = 50
        mock_prov.page_no = 1
        mock_text_item.prov = [mock_prov]

        # Mock a paragraph
        mock_par = MagicMock()
        mock_par.text = "A paragraph of text."
        mock_par.label = "text"
        mock_par.level = 0
        mock_prov2 = MagicMock()
        mock_prov2.bbox.l = 10
        mock_prov2.bbox.t = 60
        mock_prov2.bbox.r = 500
        mock_prov2.bbox.b = 100
        mock_prov2.page_no = 1
        mock_par.prov = [mock_prov2]

        mock_doc.texts = [mock_text_item, mock_par]
        mock_doc.tables = []
        mock_doc.num_pages = 2

        mock_conv.convert.return_value.document = mock_doc

        c = DoclingClient()
        result = c.analyze_layout("test.pdf")
        assert len(result["elements"]) == 2
        assert result["elements"][0]["type"] == "section_header"
        assert result["elements"][1]["text"] == "A paragraph of text."
        assert result["pages"] == 2

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_converter_is_none(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_conv = MagicMock()
        mock_conv_cls.return_value = mock_conv
        mock_load.return_value = mock_conv_cls

        c = DoclingClient()
        c.converter = None
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_conversion_fails(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_conv = MagicMock()
        mock_conv.convert.side_effect = Exception("Conversion error")
        mock_conv_cls.return_value = mock_conv
        mock_load.return_value = mock_conv_cls

        c = DoclingClient()
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_num_pages_callable(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_conv = MagicMock()
        mock_conv_cls.return_value = mock_conv
        mock_load.return_value = mock_conv_cls

        mock_doc = MagicMock()
        mock_doc.texts = []
        mock_doc.tables = []
        mock_doc.num_pages = lambda: 5

        mock_conv.convert.return_value.document = mock_doc

        c = DoclingClient()
        result = c.analyze_layout("test.pdf")
        assert result["pages"] == 5

    @patch("app.pipeline.services.docling_client._load_docling_converter")
    def test_analyze_no_num_pages(self, mock_load):
        mock_conv_cls = MagicMock()
        mock_conv = MagicMock()
        mock_conv_cls.return_value = mock_conv
        mock_load.return_value = mock_conv_cls

        mock_doc = MagicMock()
        mock_doc.texts = []
        mock_doc.tables = []
        del mock_doc.num_pages

        mock_conv.convert.return_value.document = mock_doc

        c = DoclingClient()
        result = c.analyze_layout("test.pdf")
        assert result["pages"] == 1


class TestDoclingClientDetectHeadersFooters:
    def test_detect_headers_and_footers(self):
        c = DoclingClient()
        page_height = 1000
        page_height * 0.1  # y1 < 100
        page_height * 0.9  # y0 > 900

        header_elem = LayoutElement(
            text="Header", bbox=BoundingBox(0, 0, 500, 50), element_type="text"
        )
        body_elem = LayoutElement(
            text="Body", bbox=BoundingBox(0, 200, 500, 300), element_type="text"
        )
        footer_elem = LayoutElement(
            text="Footer", bbox=BoundingBox(0, 950, 500, 1000), element_type="text"
        )

        headers, footers = c._detect_headers_footers([header_elem, body_elem, footer_elem])
        assert len(headers) == 1
        assert headers[0].text == "Header"
        assert len(footers) == 1
        assert footers[0].text == "Footer"

    def test_detect_no_elements(self):
        c = DoclingClient()
        headers, footers = c._detect_headers_footers([])
        assert headers == []
        assert footers == []


class TestDoclingClientHelpers:
    def test_calculate_confidence_empty(self):
        c = DoclingClient()
        assert c._calculate_confidence([]) == 0.0

    def test_calculate_confidence_with_elements(self):
        c = DoclingClient()
        bbox = BoundingBox(0, 0, 100, 50)
        elems = [
            LayoutElement(text="A", bbox=bbox, element_type="text", confidence=0.8),
            LayoutElement(text="B", bbox=bbox, element_type="text", confidence=0.9),
        ]
        assert c._calculate_confidence(elems) == pytest.approx(0.85)

    def test_empty_layout(self):
        c = DoclingClient()
        result = c._empty_layout()
        assert result["elements"] == []
        assert result["pages"] == 0

    def test_find_title_no_elements(self):
        c = DoclingClient()
        assert c.find_title_with_logo_tolerance([]) is None

    def test_find_title_with_elements(self):
        c = DoclingClient()
        BoundingBox(0, 0, 100, 50)
        small = LayoutElement(text="small", bbox=BoundingBox(0, 200, 100, 250), element_type="text", font_size=10.0)
        large = LayoutElement(text="TITLE", bbox=BoundingBox(0, 200, 100, 250), element_type="text", font_size=24.0)
        result = c.find_title_with_logo_tolerance([small, large], logo_y_threshold=50)
        assert result is not None
        assert result.text == "TITLE"
