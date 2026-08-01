# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, PropertyMock, patch

from app.pipeline.services.docling_client import (
    BoundingBox,
    DoclingClient,
    LayoutElement,
    _docling_enabled,
    _load_docling_converter,
    _suppress_docling_warnings,
)


class TestDoclingUtilities:
    def test_docling_enabled_fallback_false(self):
        with patch("app.pipeline.services.docling_client.settings") as ms:
            ms.USE_DOCLING_FALLBACK = False
            ms.LOW_MEMORY_MODE = False
            assert _docling_enabled() is False

    def test_docling_enabled_low_memory(self):
        with patch("app.pipeline.services.docling_client.settings") as ms:
            ms.USE_DOCLING_FALLBACK = True
            ms.LOW_MEMORY_MODE = True
            assert _docling_enabled() is False

    def test_docling_enabled_true(self):
        with patch("app.pipeline.services.docling_client.settings") as ms:
            ms.USE_DOCLING_FALLBACK = True
            ms.LOW_MEMORY_MODE = False
            assert _docling_enabled() is True

    def test_load_converter_not_available(self):
        with patch("app.pipeline.services.docling_client.DOCLING_AVAILABLE", False):
            assert _load_docling_converter() is None

    def test_load_converter_import_exception(self):
        orig_import = __import__
        def fake_import(name, *args, **kw):
            if "docling" in name:
                raise ImportError("docling not available")
            return orig_import(name, *args, **kw)
        with patch("app.pipeline.services.docling_client.DOCLING_AVAILABLE", True):
            with patch("builtins.__import__", side_effect=fake_import):
                assert _load_docling_converter() is None

    def test_suppress_warnings_context(self):
        with _suppress_docling_warnings(), warnings.catch_warnings(record=True) as w:
            warnings.warn("test deprecated", DeprecationWarning, stacklevel=2)
            assert len(w) == 1


class TestDoclingClientInit:
    def test_init_converter_none(self):
        with patch("app.pipeline.services.docling_client._load_docling_converter", return_value=None):
            c = DoclingClient()
            assert c._available is False
            assert c.converter is None

    def test_init_converter_raises(self):
        mock_cls = MagicMock(side_effect=Exception("init failed"))
        with patch("app.pipeline.services.docling_client._load_docling_converter", return_value=mock_cls):
            c = DoclingClient()
            assert c._available is False


class TestDoclingClientAnalyzeLayout:
    def test_analyze_not_available(self):
        c = DoclingClient()
        c._available = False
        with patch("app.pipeline.services.docling_client.DOCLING_AVAILABLE", True):
            result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    def test_analyze_converter_none(self):
        c = DoclingClient()
        c._available = True
        c.converter = None
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    def test_analyze_conversion_exception(self):
        c = DoclingClient()
        c._available = True
        c.converter = MagicMock()
        c.converter.convert.side_effect = Exception("convert failed")
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    def test_analyze_outer_exception(self):
        c = DoclingClient()
        c._available = True
        c.converter = MagicMock()
        mock_doc = MagicMock()
        c.converter.convert.return_value.document = mock_doc
        type(mock_doc).texts = PropertyMock(side_effect=Exception("outer crash"))
        result = c.analyze_layout("test.pdf")
        assert result["elements"] == []

    def test_analyze_text_item_no_prov(self):
        c = DoclingClient()
        c._available = True
        mock_converter = MagicMock()
        c.converter = mock_converter
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.text = "Some text"
        mock_item.label = "paragraph"
        mock_item.prov = []
        mock_doc.texts = [mock_item]
        mock_doc.tables = []
        mock_doc.num_pages = 5
        mock_converter.convert.return_value.document = mock_doc
        result = c.analyze_layout("test.pdf")
        assert len(result["elements"]) == 1
        assert result["elements"][0]["bbox"] is None

    def test_analyze_with_tables(self):
        c = DoclingClient()
        c._available = True
        mock_converter = MagicMock()
        c.converter = mock_converter
        mock_doc = MagicMock()
        mock_doc.texts = []
        mock_table = MagicMock()
        mock_table.prov = [MagicMock()]
        mock_table.prov[0].bbox.l = 10
        mock_table.prov[0].bbox.t = 20
        mock_table.prov[0].bbox.r = 100
        mock_table.prov[0].bbox.b = 200
        mock_table.prov[0].page_no = 1
        mock_table.data.grid = [["a", "b"], ["c", "d"]]
        mock_doc.tables = [mock_table]
        mock_doc.num_pages = 1
        mock_converter.convert.return_value.document = mock_doc
        result = c.analyze_layout("test.pdf")
        assert len(result["elements"]) == 1
        assert result["elements"][0]["type"] == "table"

    def test_analyze_num_pages_callable(self):
        c = DoclingClient()
        c._available = True
        mock_converter = MagicMock()
        c.converter = mock_converter
        mock_doc = MagicMock()
        mock_doc.texts = []
        mock_doc.tables = []
        mock_doc.num_pages = lambda: 3
        mock_converter.convert.return_value.document = mock_doc
        result = c.analyze_layout("test.pdf")
        assert result["pages"] == 3


class TestDoclingClientHelpers:
    def test_extract_elements_success(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.bbox.l = 0
        mock_item.bbox.t = 0
        mock_item.bbox.r = 100
        mock_item.bbox.b = 50
        mock_item.bbox.page = 1
        mock_item.text = "Hello"
        mock_item.label = "paragraph"
        mock_item.prov = [MagicMock()]
        mock_item.prov[0].font_size = 12.0
        mock_item.prov[0].font_weight = 700
        mock_item.prov[0].font_style = "italic"
        mock_item.prov[0].bbox.l = 0
        mock_item.prov[0].bbox.t = 0
        mock_item.prov[0].bbox.r = 100
        mock_item.prov[0].bbox.b = 50
        mock_doc.iterate_items.return_value = [mock_item]
        elements = c._extract_elements(mock_doc)
        assert len(elements) == 1
        assert elements[0].text == "Hello"

    def test_extract_elements_exception(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("iter failed")
        elements = c._extract_elements(mock_doc)
        assert elements == []

    def test_detect_headers_footers_empty(self):
        c = DoclingClient()
        h, f = c._detect_headers_footers([])
        assert h == []
        assert f == []

    def test_detect_headers_footers_basic(self):
        c = DoclingClient()
        header = LayoutElement("H", BoundingBox(0, 0, 100, 50, page=0), "heading")
        body = LayoutElement("B", BoundingBox(0, 200, 100, 300, page=0), "paragraph")
        footer = LayoutElement("F", BoundingBox(0, 950, 100, 1000, page=0), "footer")
        h, f = c._detect_headers_footers([header, body, footer])
        assert len(h) == 1
        assert len(f) == 1

    def test_extract_tables_success(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "table"
        mock_item.text = "table data"
        mock_item.bbox = MagicMock()
        mock_item.bbox.to_dict.return_value = {"x0": 0}
        mock_item.num_rows = 3
        mock_item.num_cols = 2
        mock_doc.iterate_items.return_value = [mock_item]
        tables = c._extract_tables(mock_doc)
        assert len(tables) == 1
        assert tables[0]["rows"] == 3

    def test_extract_tables_exception(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("bad")
        assert c._extract_tables(mock_doc) == []

    def test_extract_figures_success(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_item = MagicMock()
        mock_item.label = "figure"
        mock_item.text = "fig"
        mock_item.bbox = MagicMock()
        mock_item.bbox.to_dict.return_value = {}
        mock_item.caption = "A figure"
        mock_doc.iterate_items.return_value = [mock_item]
        figs = c._extract_figures(mock_doc)
        assert len(figs) == 1

    def test_extract_figures_exception(self):
        c = DoclingClient()
        mock_doc = MagicMock()
        mock_doc.iterate_items.side_effect = Exception("bad")
        assert c._extract_figures(mock_doc) == []

    def test_calculate_confidence_empty(self):
        c = DoclingClient()
        assert c._calculate_confidence([]) == 0.0

    def test_calculate_confidence_average(self):
        c = DoclingClient()
        e1 = LayoutElement("A", BoundingBox(0, 0, 10, 10), "p", confidence=0.8)
        e2 = LayoutElement("B", BoundingBox(0, 0, 10, 10), "p", confidence=0.6)
        assert c._calculate_confidence([e1, e2]) == 0.7

    def test_find_title_with_logo_no_candidates(self):
        c = DoclingClient()
        elem = LayoutElement("", BoundingBox(0, 0, 10, 10), "p")
        assert c.find_title_with_logo_tolerance([elem]) is None

    def test_find_title_with_logo_finds_max_font(self):
        c = DoclingClient()
        e1 = LayoutElement("Small", BoundingBox(0, 200, 100, 220), "p", font_size=10)
        e2 = LayoutElement("Large", BoundingBox(0, 200, 100, 220), "title", font_size=24)
        result = c.find_title_with_logo_tolerance([e1, e2], logo_y_threshold=100)
        assert result is not None
        assert result.text == "Large"
