from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


def _make_bbox(cls, l, t, r, b, page=1):
    bbox = MagicMock()
    bbox.l = l
    bbox.t = t
    bbox.r = r
    bbox.b = b
    bbox.page = page
    return bbox


class TestDoclingClientInitEdgeCases:
    def test_init_docling_converter_none(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter", return_value=None):
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            assert c.is_available() is False
            assert c.converter is None

    def test_init_converter_exception(self):
        mock_conv_cls = MagicMock()
        mock_conv_cls.side_effect = Exception("Init error")
        with patch("app.pipeline.services.docling_client._load_docling_converter", return_value=mock_conv_cls):
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            assert c.is_available() is False


class TestDoclingClientAnalyzeLayoutDeep:
    def test_analyze_with_tables(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            mock_doc = MagicMock()
            mock_doc.texts = []
            mock_table = MagicMock()
            t_bbox = _make_bbox(None, 10, 100, 500, 300, 1)
            mock_table.prov = [MagicMock(bbox=t_bbox)]
            mock_table.data.grid = [["a", "b"], ["c", "d"]]
            mock_doc.tables = [mock_table]
            mock_doc.num_pages = 1
            mock_conv.convert.return_value.document = mock_doc
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            result = c.analyze_layout("test.pdf")
            assert len(result["elements"]) == 1
            assert result["elements"][0]["type"] == "table"
            assert result["elements"][0]["rows"] == 2

    def test_analyze_global_exception(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            mock_conv.convert.side_effect = Exception("Boom")
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            result = c.analyze_layout("test.pdf")
            assert result["elements"] == []
            assert result["pages"] == 0

    def test_analyze_num_pages_as_property(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            mock_doc = MagicMock()
            mock_doc.texts = []
            mock_doc.tables = []
            type(mock_doc).num_pages = PropertyMock(return_value=3)
            mock_conv.convert.return_value.document = mock_doc
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            result = c.analyze_layout("test.pdf")
            assert result["pages"] == 3

    def test_analyze_no_bbox_data(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            mock_doc = MagicMock()
            mock_item = MagicMock()
            mock_item.text = "No bbox"
            mock_item.label = "text"
            mock_item.level = 0
            mock_item.prov = None
            mock_doc.texts = [mock_item]
            mock_doc.tables = []
            mock_doc.num_pages = 1
            mock_conv.convert.return_value.document = mock_doc
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            result = c.analyze_layout("test.pdf")
            assert len(result["elements"]) == 1
            assert result["elements"][0]["bbox"] is None

    def test_analyze_empty_texts_and_tables(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_conv_cls = MagicMock()
            mock_conv = MagicMock()
            mock_conv_cls.return_value = mock_conv
            mock_load.return_value = mock_conv_cls
            mock_doc = MagicMock()
            mock_doc.texts = []
            mock_doc.tables = []
            mock_doc.num_pages = 0
            mock_conv.convert.return_value.document = mock_doc
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            result = c.analyze_layout("test.pdf")
            assert result["elements"] == []
            assert result["pages"] == 0

    def test_analyze_converter_none_during_call(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter") as mock_load:
            mock_load.return_value = MagicMock()
            from app.pipeline.services.docling_client import DoclingClient
            c = DoclingClient()
            c.converter = None
            result = c.analyze_layout("test.pdf")
            assert result["elements"] == []


class TestDoclingClientExtractElements:
    def test_extract_elements_basic(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.bbox.l = 0
        mock_item.bbox.t = 10
        mock_item.bbox.r = 100
        mock_item.bbox.b = 50
        mock_item.text = "Element text"
        mock_item.label = "paragraph"
        mock_item.prov = []
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert len(elements) == 1
        assert elements[0].text == "Element text"
        assert elements[0].element_type == "paragraph"

    def test_extract_elements_no_bbox_skips(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        del mock_item.bbox
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert elements == []

    def test_extract_elements_exception(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("Iteration error")
        elements = c._extract_elements(mock_doc)
        assert elements == []

    def test_extract_elements_with_prov_data(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 100
        mock_item.bbox.b = 50
        mock_item.text = "Styled"
        mock_item.label = "heading"
        mock_prov = MagicMock()
        mock_prov.font_size = 14.0
        mock_prov.font_weight = 700
        mock_prov.font_style = "italic"
        mock_item.prov = [mock_prov]
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert len(elements) == 1
        assert elements[0].font_size == 14.0
        assert elements[0].is_bold is True
        assert elements[0].is_italic is True

    def test_extract_elements_with_partial_prov(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 50
        mock_item.bbox.b = 20
        mock_item.text = "Minimal"
        mock_item.label = "text"
        mock_prov = MagicMock()
        del mock_prov.font_size
        del mock_prov.font_weight
        del mock_prov.font_style
        mock_item.prov = [mock_prov]
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert len(elements) == 1
        assert elements[0].font_size is None
        assert elements[0].is_bold is False
        assert elements[0].is_italic is False


class TestDoclingClientDetectHeadersFooters:
    def test_headers_and_footers(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        el1 = LayoutElement(text="Header", bbox=BoundingBox(0, 0, 100, 30), element_type="text")
        el2 = LayoutElement(text="Body", bbox=BoundingBox(0, 300, 100, 350), element_type="text")
        el3 = LayoutElement(text="Footer", bbox=BoundingBox(0, 950, 100, 1000), element_type="text")
        headers, footers = c._detect_headers_footers([el1, el2, el3])
        assert len(headers) == 1
        assert headers[0].text == "Header"
        assert len(footers) == 1
        assert footers[0].text == "Footer"

    def test_empty_elements(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        headers, footers = c._detect_headers_footers([])
        assert headers == []
        assert footers == []

    def test_multiple_pages(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        p1_header = LayoutElement(text="P1 Header", bbox=BoundingBox(0, 0, 100, 20, page=1), element_type="text")
        p1_body = LayoutElement(text="P1 Body", bbox=BoundingBox(0, 200, 100, 400, page=1), element_type="text")
        p2_header = LayoutElement(text="P2 Header", bbox=BoundingBox(0, 0, 100, 20, page=2), element_type="text")
        p2_body = LayoutElement(text="P2 Body", bbox=BoundingBox(0, 200, 100, 400, page=2), element_type="text")
        headers, footers = c._detect_headers_footers([p1_header, p1_body, p2_header, p2_body])
        assert len(headers) == 2
        assert footers == []


class TestDoclingClientExtractTables:
    def test_extracts_tables(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "table"
        mock_item.text = "Table data"
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 100
        mock_item.bbox.b = 50
        mock_item.num_rows = 3
        mock_item.num_cols = 2
        mock_doc.iterate_items.return_value = [mock_item]
        tables = c._extract_tables(mock_doc)
        assert len(tables) == 1
        assert tables[0]["rows"] == 3

    def test_no_tables(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "text"
        mock_doc.iterate_items.return_value = [mock_item]
        tables = c._extract_tables(mock_doc)
        assert tables == []

    def test_exception(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("Error")
        tables = c._extract_tables(mock_doc)
        assert tables == []


class TestDoclingClientExtractFigures:
    def test_extracts_figures(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "figure"
        mock_item.text = "Figure caption"
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 200
        mock_item.bbox.b = 150
        mock_item.caption = "Fig 1"
        mock_doc.iterate_items.return_value = [mock_item]
        figures = c._extract_figures(mock_doc)
        assert len(figures) == 1
        assert figures[0]["caption"] == "Fig 1"

    def test_no_figures(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "text"
        mock_doc.iterate_items.return_value = [mock_item]
        figures = c._extract_figures(mock_doc)
        assert figures == []

    def test_exception(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("Error")
        figures = c._extract_figures(mock_doc)
        assert figures == []

    def test_picture_label(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "picture"
        mock_item.text = "Picture"
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 100
        mock_item.bbox.b = 100
        mock_item.caption = ""
        mock_doc.iterate_items.return_value = [mock_item]
        figures = c._extract_figures(mock_doc)
        assert len(figures) == 1


class TestDoclingClientCalculateConfidence:
    def test_empty(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        assert c._calculate_confidence([]) == 0.0

    def test_single_element(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        elem = LayoutElement(text="A", bbox=BoundingBox(0, 0, 10, 10), element_type="text", confidence=0.8)
        assert c._calculate_confidence([elem]) == 0.8

    def test_multiple_elements(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        e1 = LayoutElement(text="A", bbox=BoundingBox(0, 0, 10, 10), element_type="text", confidence=0.9)
        e2 = LayoutElement(text="B", bbox=BoundingBox(0, 0, 10, 10), element_type="text", confidence=0.7)
        assert c._calculate_confidence([e1, e2]) == 0.8


class TestDoclingClientEmptyLayout:
    def test_empty_layout(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        result = c._empty_layout()
        assert result["elements"] == []
        assert result["headers"] == []
        assert result["tables"] == []
        assert result["figures"] == []
        assert result["confidence"] == 0.0
        assert result["pages"] == 0


class TestDoclingClientFindTitle:
    def test_no_candidates_returns_none(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        elem = LayoutElement(text="Logo", bbox=BoundingBox(0, 0, 100, 50), element_type="text")
        result = c.find_title_with_logo_tolerance([elem], logo_y_threshold=100)
        assert result is None

    def test_selects_largest_font(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        small = LayoutElement(text="Small", bbox=BoundingBox(0, 200, 100, 250), element_type="text", font_size=12)
        large = LayoutElement(text="Large", bbox=BoundingBox(0, 200, 100, 250), element_type="text", font_size=24)
        result = c.find_title_with_logo_tolerance([small, large], logo_y_threshold=100)
        assert result is not None
        assert result.text == "Large"

    def test_empty_elements(self):
        from app.pipeline.services.docling_client import DoclingClient
        c = DoclingClient()
        assert c.find_title_with_logo_tolerance([]) is None

    def test_font_size_none_handling(self):
        from app.pipeline.services.docling_client import BoundingBox, DoclingClient, LayoutElement
        c = DoclingClient()
        elem = LayoutElement(text="No font", bbox=BoundingBox(0, 200, 100, 250), element_type="text")
        result = c.find_title_with_logo_tolerance([elem], logo_y_threshold=50)
        assert result is not None
        assert result.text == "No font"


class TestDoclingClientModule:
    def test_docling_available_flag(self):
        from app.pipeline.services.docling_client import DOCLING_AVAILABLE
        assert DOCLING_AVAILABLE is not None

    def test_docling_enabled_settings(self):
        with patch("app.pipeline.services.docling_client.settings.USE_DOCLING_FALLBACK", True, create=True):
            with patch("app.pipeline.services.docling_client.settings.LOW_MEMORY_MODE", False):
                from app.pipeline.services.docling_client import _docling_enabled
                assert _docling_enabled() is True

    def test_docling_disabled_by_setting(self):
        with patch("app.pipeline.services.docling_client.settings.USE_DOCLING_FALLBACK", False, create=True):
            from app.pipeline.services.docling_client import _docling_enabled
            assert _docling_enabled() is False

    def test_docling_disabled_low_memory(self):
        with patch("app.pipeline.services.docling_client.settings.USE_DOCLING_FALLBACK", True, create=True):
            with patch("app.pipeline.services.docling_client.settings.LOW_MEMORY_MODE", True):
                from app.pipeline.services.docling_client import _docling_enabled
                assert _docling_enabled() is False


class TestBoundingBoxEdgeCases:
    def test_zero_dimensions(self):
        from app.pipeline.services.docling_client import BoundingBox
        b = BoundingBox(0, 0, 0, 0)
        assert b.width == 0
        assert b.height == 0

    def test_negative_coords(self):
        from app.pipeline.services.docling_client import BoundingBox
        b = BoundingBox(-10, -20, 100, 200)
        assert b.width == 110
        assert b.height == 220

    def test_center_y(self):
        from app.pipeline.services.docling_client import BoundingBox
        b = BoundingBox(0, 100, 100, 200)
        assert b.center_y == 150


class TestLayoutElementEdgeCases:
    def test_default_confidence(self):
        from app.pipeline.services.docling_client import BoundingBox, LayoutElement
        e = LayoutElement(text="Test", bbox=BoundingBox(0, 0, 10, 10), element_type="text")
        assert e.confidence == 1.0

    def test_is_bold_italic_defaults(self):
        from app.pipeline.services.docling_client import BoundingBox, LayoutElement
        e = LayoutElement(text="Test", bbox=BoundingBox(0, 0, 10, 10), element_type="text")
        assert e.is_bold is False
        assert e.is_italic is False
