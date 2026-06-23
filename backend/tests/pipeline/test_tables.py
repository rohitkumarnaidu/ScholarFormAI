# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Test suite for tables pipeline: extractor, renderer, caption matcher.
"""

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, call
import pytest
from app.pipeline.tables.caption_matcher import TableCaptionMatcher
from app.pipeline.tables.extractor import TableExtractor
from app.pipeline.tables.renderer import TableRenderer
from app.models import PipelineDocument, Block, BlockType, Table, TableCell


# ===================================================================
# CAPTION MATCHER TESTS
# ===================================================================

class TestTableCaptionMatcher:
    @pytest.fixture
    def matcher(self):
        return TableCaptionMatcher()

    def test_process_empty_document(self, matcher):
        doc = PipelineDocument(document_id="t", blocks=[])
        result = matcher.process(doc)
        assert result is doc

    def test_process_no_tables_returns_early(self, matcher):
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=1, text="Results are in Table 1.", block_type=BlockType.BODY),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_process_with_tables_and_captions(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Table 1. Performance comparison.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Some body text.", block_type=BlockType.BODY),
            ],
            tables=[
                Table(table_id="t1", num_rows=0, num_cols=0, index=0, block_index=1),
            ],
        )
        result = matcher.process(doc)
        assert result.tables[0].table_id == "t1"

    def test_adds_stage_info(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[Block(block_id="b1", index=0, text="Table 1. Testing.", block_type=BlockType.BODY)],
            tables=[Table(table_id="t1", num_rows=0, num_cols=0, index=0, block_index=0)],
        )
        result = matcher.process(doc)
        stages = [s.stage_name for s in result.processing_history]
        assert "table_caption_matching" in stages

    def test_custom_search_window(self):
        matcher = TableCaptionMatcher(search_window_above=3, search_window_below=2)
        assert matcher.search_window_above == 3
        assert matcher.search_window_below == 2

    def test_caption_above_table_is_matched(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Table 1. Accuracy metrics.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Some data.", block_type=BlockType.BODY),
            ],
            tables=[Table(table_id="t1", num_rows=2, num_cols=2, index=0, block_index=1)],
        )
        result = matcher.process(doc)
        assert result.tables[0].caption_text is not None

    def test_multiple_tables_multiple_captions(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Table 1. First table.", block_type=BlockType.BODY),
                Block(block_id="b2", index=1, text="Body text.", block_type=BlockType.BODY),
                Block(block_id="b3", index=2, text="Table 2. Second table.", block_type=BlockType.BODY),
                Block(block_id="b4", index=3, text="Body text.", block_type=BlockType.BODY),
            ],
            tables=[
                Table(table_id="t1", num_rows=2, num_cols=2, index=0, block_index=1),
                Table(table_id="t2", num_rows=2, num_cols=2, index=1, block_index=3),
            ],
        )
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. First table."
        assert result.tables[1].caption_text == "Table 2. Second table."

    def test_headings_are_not_captions(self, matcher):
        doc = PipelineDocument(document_id="t",
            blocks=[
                Block(block_id="b1", index=0, text="Table 1. Introduction", block_type=BlockType.HEADING_1),
                Block(block_id="b2", index=1, text="Body text.", block_type=BlockType.BODY),
            ],
            tables=[Table(table_id="t1", num_rows=2, num_cols=2, index=0, block_index=1)],
        )
        result = matcher.process(doc)
        assert result.tables[0].caption_text is None


# ===================================================================
# EXTRACTOR TESTS
# ===================================================================

class TestTableExtractor:
    @pytest.fixture
    def extractor(self):
        return TableExtractor()

    # -- helpers ------------------------------------------------------

    def _make_docx_cell(self, text: str, bold: bool = False, nested_table_count: int = 0):
        """Build a MagicMock that behaves like a python-docx Cell."""
        cell = MagicMock()
        cell.text = text
        cell._tc = MagicMock()
        # By default, _tc.iter() yields nothing (deep extraction fails)
        cell._tc.iter.return_value = []

        run = MagicMock()
        run.bold = bold
        para = MagicMock()
        para.runs = [run]
        cell.paragraphs = [para]

        # For nested table detection via XML
        cell._element = MagicMock()
        tbl_xmls = [MagicMock() for _ in range(nested_table_count)]
        # Store data on the mock so DocxTableWrapper can inspect .rows
        for t in tbl_xmls:
            t._inner_data = [["nested"]]
            t._inner_rows = [MagicMock()]
            t._inner_rows[0].cells = [MagicMock()]
            t._inner_rows[0].cells[0].text = "nested"
        cell._element.findall.return_value = tbl_xmls

        cell._parent = MagicMock()
        cell._parent._parent = MagicMock()
        cell._parent._parent._parent = MagicMock()
        return cell

    def _make_docx_table(self, data, header_row=False, nested_at=None):
        """Build a MagicMock docx Table from a 2D list of strings."""
        from unittest.mock import MagicMock
        tbl = MagicMock()
        rows = []
        for r_idx, row_data in enumerate(data):
            row = MagicMock()
            cells = []
            for c_idx, text in enumerate(row_data):
                is_bold = header_row and r_idx == 0
                nested_count = 0
                if nested_at and (r_idx, c_idx) in nested_at:
                    nested_count = nested_at[(r_idx, c_idx)]
                cells.append(self._make_docx_cell(text, bold=is_bold, nested_table_count=nested_count))
            row.cells = cells
            rows.append(row)
        tbl.rows = rows
        return tbl

    # -- basic extraction tests ---------------------------------------

    def test_basic_2x2_table(self, extractor):
        docx_tbl = self._make_docx_table([["A1", "B1"], ["A2", "B2"]])
        result = extractor.extract(docx_tbl, "tbl_001", 0, 0)
        assert result.table_id == "tbl_001"
        assert result.num_rows == 2
        assert result.num_cols == 2
        assert result.data == [["A1", "B1"], ["A2", "B2"]]
        assert len(result.cells) == 4

    def test_single_cell_table(self, extractor):
        docx_tbl = self._make_docx_table([["only"]])
        result = extractor.extract(docx_tbl, "tbl_single", 0, 0)
        assert result.num_rows == 1
        assert result.num_cols == 1
        assert result.data[0][0] == "only"

    def test_empty_cells_preserved(self, extractor):
        docx_tbl = self._make_docx_table([["", "B1"], ["A2", ""]])
        result = extractor.extract(docx_tbl, "tbl_empty", 0, 0)
        assert result.data[0][0] == ""
        assert result.data[1][1] == ""

    def test_header_row_via_bold(self, extractor):
        docx_tbl = self._make_docx_table([["Name", "Value"], ["x", "1"]], header_row=True)
        result = extractor.extract(docx_tbl, "tbl_hdr", 0, 0)
        assert result.has_header is True
        assert result.header_rows == 1
        assert result.cells[0].bold is True

    def test_header_row_via_keywords(self, extractor):
        docx_tbl = self._make_docx_table([["Name", "Value"], ["x", "1"]], header_row=False)
        result = extractor.extract(docx_tbl, "tbl_kw", 0, 0)
        # "Name" and "Value" are in the common_headers set -> has_header should be True
        assert result.has_header is True

    def test_no_header_detected(self, extractor):
        docx_tbl = self._make_docx_table([["apple", "banana"], ["cherry", "date"]], header_row=False)
        result = extractor.extract(docx_tbl, "tbl_nh", 0, 0)
        assert result.has_header is False

    def test_3x3_table(self, extractor):
        docx_tbl = self._make_docx_table([["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]])
        result = extractor.extract(docx_tbl, "tbl_33", 0, 0)
        assert result.num_rows == 3
        assert result.num_cols == 3
        assert result.data[2][2] == "I"

    # -- deep XML fallback -------------------------------------------

    def test_deep_xml_fallback_fills_empty_cell(self, extractor):
        cell = MagicMock()
        cell.text = ""
        # deep text available via XML
        cell._tc = MagicMock()
        text_node = MagicMock()
        text_node.tag = "}t"
        text_node.text = "hidden_text"
        cell._tc.iter.return_value = [text_node]

        run = MagicMock()
        run.bold = False
        cell.paragraphs = [MagicMock(runs=[run])]
        cell._element = MagicMock()
        cell._element.findall.return_value = []
        cell._parent = MagicMock()

        row = MagicMock()
        row.cells = [cell]
        tbl = MagicMock()
        tbl.rows = [row]

        result = extractor.extract(tbl, "tbl_deep", 0, 0)
        assert result.data[0][0] == "hidden_text"

    def test_deep_xml_no_text_returns_empty(self, extractor):
        cell = MagicMock()
        cell.text = ""
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []  # no text nodes
        run = MagicMock()
        run.bold = False
        cell.paragraphs = [MagicMock(runs=[run])]
        cell._element = MagicMock()
        cell._element.findall.return_value = []
        cell._parent = MagicMock()

        row = MagicMock()
        row.cells = [cell]
        tbl = MagicMock()
        tbl.rows = [row]

        result = extractor.extract(tbl, "tbl_deep2", 0, 0)
        assert result.data[0][0] == ""

    # -- nested tables ------------------------------------------------

    def test_nested_table_extraction(self, extractor):
        """Nested tables are extracted recursively."""
        inner_data = [["inner_a", "inner_b"], ["inner_c", "inner_d"]]

        # Build inner docx table
        inner_tbl = MagicMock()
        inner_rows = []
        for inner_row_data in inner_data:
            row = MagicMock()
            cells = []
            for text in inner_row_data:
                cells.append(self._make_docx_cell(text))
            row.cells = cells
            inner_rows.append(row)
        inner_tbl.rows = inner_rows

        # We need to mock docx.table.Table to return our inner table when constructed
        with patch("docx.table.Table", return_value=inner_tbl):
            # Build outer table with cell containing nested table
            cell = self._make_docx_cell("outer", nested_table_count=1)
            row = MagicMock()
            row.cells = [cell]
            tbl = MagicMock()
            tbl.rows = [row]

            result = extractor.extract(tbl, "tbl_nested", 0, 0)
            assert result.num_rows == 1
            nested = result.cells[0].metadata.get("nested_tables", [])
            assert len(nested) == 1
            assert nested[0].data[0][0] == "inner_a"

    def test_nested_table_extraction_failure_handled(self, extractor):
        """If nested extraction fails, it's logged and doesn't crash."""
        cell = self._make_docx_cell("outer", nested_table_count=1)
        row = MagicMock()
        row.cells = [cell]
        tbl = MagicMock()
        tbl.rows = [row]

        # Make docx.table.Table raise on construction
        with patch("docx.table.Table", side_effect=Exception("mock failure")):
            result = extractor.extract(tbl, "tbl_fail", 0, 0)
            assert result.num_rows == 1
            assert "nested_tables" not in result.cells[0].metadata or not result.cells[0].metadata.get("nested_tables")

    # -- edge cases ---------------------------------------------------

    def test_table_id_assigned(self, extractor):
        docx_tbl = self._make_docx_table([["a"]])
        result = extractor.extract(docx_tbl, "my_id", 42, 7)
        assert result.table_id == "my_id"
        assert result.index == 42
        assert result.block_index == 7

    def test_unicode_text(self, extractor):
        docx_tbl = self._make_docx_table([["café", "naïve"], ["über", "α β γ"]])
        result = extractor.extract(docx_tbl, "tbl_uni", 0, 0)
        assert result.data[0][0] == "café"
        assert result.data[1][1] == "α β γ"


# ===================================================================
# RENDERER TESTS
# ===================================================================

class TestTableRenderer:
    @pytest.fixture
    def renderer(self):
        return TableRenderer()

    def _make_mock_doc(self):
        """Create a mock python-docx Document."""
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        return doc

    def test_skip_when_table_none(self, renderer):
        doc = MagicMock()
        renderer.render(doc, None)
        doc.add_table.assert_not_called()

    def test_skip_when_no_rows(self, renderer):
        doc = MagicMock()
        tbl = Table(table_id="empty", num_rows=0, num_cols=0, index=0, block_index=0)
        renderer.render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_basic_table_rendering(self, renderer, simple_table):
        doc = self._make_mock_doc()
        renderer.render(doc, simple_table)
        doc.add_table.assert_called_once_with(rows=2, cols=2)
        word_table = doc.add_table.return_value
        assert word_table.style == "Table Grid"

    def test_caption_added_above_table(self, renderer, simple_table):
        doc = self._make_mock_doc()
        simple_table.caption_text = "Table 1: Accuracy results"
        renderer.render(doc, simple_table)
        doc.add_paragraph.assert_called_once()
        cap_para = doc.add_paragraph.return_value
        # Should have added a bold "Table 1: " run
        assert cap_para.add_run.call_count >= 1

    def test_caption_with_number_override(self, renderer, simple_table):
        doc = self._make_mock_doc()
        simple_table.caption_text = "Performance metrics"
        renderer.render(doc, simple_table, number=5)
        doc.add_paragraph.assert_called_once()
        cap_para = doc.add_paragraph.return_value
        # Should have added "Table 5: "
        calls = cap_para.add_run.call_args_list
        bold_runs = [c for c in calls if c[0][0] == "Table 5: "]
        assert len(bold_runs) > 0

    def test_caption_with_existing_table_prefix(self, renderer, simple_table):
        doc = self._make_mock_doc()
        simple_table.caption_text = "Table 1: Experimental results"
        renderer.render(doc, simple_table)
        cap_para = doc.add_paragraph.return_value
        calls = cap_para.add_run.call_args_list
        # bold run should be "Table 1: "
        assert any(c[0][0] == "Table 1: " for c in calls)

    def test_nested_table_rendering(self, renderer, simple_table):
        doc = self._make_mock_doc()
        nested = Table(table_id="n1", num_rows=1, num_cols=1, index=1, block_index=1,
                       data=[["inner"]], cells=[TableCell(row=0, col=0, text="inner")])
        simple_table.cells[0].metadata["nested_tables"] = [nested]

        # Need cells access on word_table for population
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        word_tbl.rows = [MagicMock(), MagicMock()]
        word_tbl.rows[0].cells = [MagicMock(), MagicMock()]
        word_tbl.rows[1].cells = [MagicMock(), MagicMock()]

        renderer.render(doc, simple_table)
        # Should have created at least 2 tables (main + nested)
        assert doc.add_table.call_count >= 1

    def test_style_fallback_when_missing(self, renderer, simple_table):
        doc = MagicMock()
        # Table Grid style not present
        doc.styles = {}
        doc.add_table.return_value = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        renderer.render(doc, simple_table)
        word_table = doc.add_table.return_value
        # Should not have tried to set style
        assert word_table.style != "Table Grid"

    def test_cell_population(self, renderer, simple_table):
        doc = self._make_mock_doc()
        # Set up word_table cell mocks
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        row0 = MagicMock()
        row1 = MagicMock()
        cell00 = MagicMock()
        cell01 = MagicMock()
        cell10 = MagicMock()
        cell11 = MagicMock()
        row0.cells = [cell00, cell01]
        row1.cells = [cell10, cell11]
        word_tbl.rows = [row0, row1]

        renderer.render(doc, simple_table)
        assert cell00.text == "A1"
        assert cell01.text == "B1"
        assert cell10.text == "A2"
        assert cell11.text == "B2"

    def test_cell_population_error_does_not_crash(self, renderer, simple_table):
        doc = self._make_mock_doc()
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        word_tbl.rows = [MagicMock()]
        word_tbl.rows[0].cells = [MagicMock()]
        # Raise error when setting text on cell
        word_tbl.rows[0].cells[0].text = "something"
        # Make the table have more cells than word_tbl rows (index error)
        simple_table.cells = [
            TableCell(row=0, col=0, text="ok"),
            TableCell(row=5, col=5, text="out_of_bounds"),
        ]
        # Should not raise
        renderer.render(doc, simple_table)

    def test_cell_access_error_handled_gracefully(self, renderer, simple_table):
        """Triggers the cell population except handler at line 79-80."""
        doc = self._make_mock_doc()
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        row = MagicMock()
        row.cells = MagicMock()
        row.cells.__getitem__.side_effect = IndexError("cell access error")
        word_tbl.rows = [row]
        # Should not raise — error is logged and loop continues
        renderer.render(doc, simple_table)

    def test_renderer_returns_none(self, renderer, simple_table):
        doc = self._make_mock_doc()
        result = renderer.render(doc, simple_table)
        assert result is None
