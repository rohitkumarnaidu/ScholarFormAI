# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Gap-filling tests for tables pipeline: extractor, caption_matcher, renderer.
Targets 100% line coverage for each module.
"""

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock, call
import pytest
from app.pipeline.tables.caption_matcher import TableCaptionMatcher, match_table_captions
from app.pipeline.tables.extractor import TableExtractor
from app.pipeline.tables.renderer import TableRenderer

# ===================================================================
# TABLE EXTRACTOR — Lines 31-138, 142-144, 151-159, 163-167, 171-177
# ===================================================================

class TestTableExtractorGaps:
    """Covers all extractor lines."""

    @pytest.fixture
    def extractor(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        return TableExtractor()

    def _make_docx_cell(self, text: str = "", bold: bool = False, has_nested: bool = False):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.text = text
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []
        run = MagicMock()
        run.bold = bold
        cell.paragraphs = [MagicMock(runs=[run])]
        cell._element = MagicMock()
        cell._element.findall.return_value = []
        cell._parent = MagicMock()
        cell._parent._parent = MagicMock()
        cell._parent._parent._parent = MagicMock()
        return cell

    def _make_docx_table(self, data, header_row=False):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        tbl = MagicMock()
        rows = []
        for r_idx, row_data in enumerate(data):
            row = MagicMock()
            cells = []
            for c_idx, text in enumerate(row_data):
                is_bold = header_row and r_idx == 0
                cells.append(self._make_docx_cell(text=text, bold=is_bold))
            row.cells = cells
            rows.append(row)
        tbl.rows = rows
        return tbl

    # -- extract method (lines 31-138) --

    def test_basic_2x2_extraction(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["A1", "B1"], ["A2", "B2"]])
        result = extractor.extract(docx_tbl, "tbl_001", 0, 0)
        assert result.table_id == "tbl_001"
        assert result.num_rows == 2
        assert result.num_cols == 2
        assert result.data[0][0] == "A1"
        assert result.data[1][1] == "B2"

    def test_single_cell(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["only"]])
        result = extractor.extract(docx_tbl, "tbl_single", 0, 0)
        assert result.num_rows == 1
        assert result.num_cols == 1

    def test_empty_cells_preserved(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["", "B1"], ["A2", ""]])
        result = extractor.extract(docx_tbl, "tbl_empty", 0, 0)
        assert result.data[0][0] == ""
        assert result.data[1][1] == ""

    def test_header_via_bold(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["Name", "Value"], ["x", "1"]], header_row=True)
        result = extractor.extract(docx_tbl, "tbl_hdr", 0, 0)
        assert result.has_header is True
        assert result.header_rows == 1

    def test_header_via_keywords(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["Name", "Value"], ["x", "1"]], header_row=False)
        result = extractor.extract(docx_tbl, "tbl_kw", 0, 0)
        assert result.has_header is True

    def test_no_header(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["apple", "banana"], ["cherry", "date"]], header_row=False)
        result = extractor.extract(docx_tbl, "tbl_nh", 0, 0)
        assert result.has_header is False

    def test_padding_preserves_empty_cells(self, extractor):
        """Rows with different cell counts get padded (lines 58-60)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        tbl = MagicMock()
        cell_a = self._make_docx_cell(text="A")
        cell_b = self._make_docx_cell(text="B")
        cell_c = self._make_docx_cell(text="C")
        empty_cell = self._make_docx_cell(text="")
        row1 = MagicMock()
        row1.cells = [cell_a, cell_b]
        row2 = MagicMock()
        row2.cells = [cell_c, empty_cell]
        tbl.rows = [row1, row2]
        result = extractor.extract(tbl, "tbl_pad", 0, 0)
        assert result.num_cols == 2
        assert result.data[0] == ["A", "B"]
        assert result.data[1] == ["C", ""]

    def test_deep_xml_fallback_fills_empty(self, extractor):
        """When cell.text is empty but deep XML has text (lines 42-49)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.text = ""
        cell._tc = MagicMock()
        text_node = MagicMock(tag="}t", text="hidden_deep_text")
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
        assert result.data[0][0] == "hidden_deep_text"

    def test_deep_xml_no_text_returns_empty(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.text = ""
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []
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

    def test_deep_xml_exception_caught(self, extractor):
        """Exception in deep XML extraction is logged and doesn't crash (line 48-49)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.text = ""
        cell._tc = MagicMock()
        cell._tc.iter.side_effect = RuntimeError("xml error")
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
        result = extractor.extract(tbl, "tbl_xml_fail", 0, 0)
        assert result.data[0][0] == ""

    def test_nested_table_extraction(self, extractor):
        """Covers nested table extraction (lines 88-106)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        inner_tbl = MagicMock()
        inner_row = MagicMock()
        inner_cell = self._make_docx_cell(text="inner")
        inner_row.cells = [inner_cell]
        inner_tbl.rows = [inner_row]

        cell = MagicMock()
        cell.text = "outer"
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []
        run = MagicMock()
        run.bold = False
        cell.paragraphs = [MagicMock(runs=[run])]

        tbl_xml = MagicMock()
        inner_ref = MagicMock()
        inner_ref.rows = inner_tbl.rows
        tbl_xml._inner_mock = inner_ref

        def findall_side_effect(ns):
            from app.models import PipelineDocument, Block, BlockType, Table, TableCell
            return [tbl_xml] if ns.endswith('}tbl') else []

        cell._element = MagicMock()
        cell._element.findall.side_effect = findall_side_effect
        cell._parent = MagicMock()
        cell._parent._parent = MagicMock()
        cell._parent._parent._parent = MagicMock()

        row = MagicMock()
        row.cells = [cell]
        tbl = MagicMock()
        tbl.rows = [row]

        def patched_table_constructor(tbl_xml, parent):
            from app.models import PipelineDocument, Block, BlockType, Table, TableCell
            return tbl_xml._inner_mock

        with patch("docx.table.Table", side_effect=patched_table_constructor):
            result = extractor.extract(tbl, "tbl_nested", 0, 0)
            assert len(result.cells) == 1
            nested = result.cells[0].metadata.get("nested_tables", [])
            assert len(nested) == 1
            assert nested[0].data[0][0] == "inner"

    def test_nested_extraction_failure_handled(self, extractor):
        """Exception in nested extraction is caught (line 102-103)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.text = "outer"
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []
        run = MagicMock()
        run.bold = False
        cell.paragraphs = [MagicMock(runs=[run])]

        tbl_xml = MagicMock()
        cell._element = MagicMock()
        cell._element.findall.return_value = [tbl_xml]
        cell._parent = MagicMock()
        cell._parent._parent = MagicMock()
        cell._parent._parent._parent = MagicMock()

        row = MagicMock()
        row.cells = [cell]
        tbl = MagicMock()
        tbl.rows = [row]

        with patch("docx.table.Table", side_effect=Exception("nested fail")):
            result = extractor.extract(tbl, "tbl_nest_fail", 0, 0)
            assert "nested_tables" not in result.cells[0].metadata

    def test_table_id_and_indices(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["a"]])
        result = extractor.extract(docx_tbl, "my_id", 42, 7)
        assert result.table_id == "my_id"
        assert result.index == 42
        assert result.block_index == 7

    def test_unicode_text(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        docx_tbl = self._make_docx_table([["café", "über"]])
        result = extractor.extract(docx_tbl, "tbl_uni", 0, 0)
        assert result.data[0][0] == "café"

    # -- _normalize_cell_text (lines 142-144) --

    def test_normalize_cell_text_none(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._normalize_cell_text(None) == ""

    def test_normalize_cell_text_whitespace(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._normalize_cell_text("   \t  ") == ""

    def test_normalize_cell_text_preserves(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._normalize_cell_text("  hello\nworld  ") == "hello\nworld"

    def test_normalize_cell_text_already_clean(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._normalize_cell_text("hello") == "hello"

    # -- _extract_deep_xml_text (lines 151-159) --

    def test_extract_deep_xml_text_success(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell._tc = MagicMock()
        n1 = MagicMock(tag="}t", text="Hello ")
        n2 = MagicMock(tag="}t", text="World")
        cell._tc.iter.return_value = [n1, n2]
        result = extractor._extract_deep_xml_text(cell)
        assert result == "Hello World"

    def test_extract_deep_xml_text_no_nodes(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell._tc = MagicMock()
        cell._tc.iter.return_value = []
        result = extractor._extract_deep_xml_text(cell)
        assert result == ""

    def test_extract_deep_xml_text_exception(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell._tc = MagicMock()
        cell._tc.iter.side_effect = RuntimeError("iter fail")
        result = extractor._extract_deep_xml_text(cell)
        assert result == ""

    def test_extract_deep_xml_not_t_tag(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell._tc = MagicMock()
        fake = MagicMock(tag="w:r", text="ignored")
        cell._tc.iter.return_value = [fake]
        result = extractor._extract_deep_xml_text(cell)
        assert result == ""

    # -- _is_cell_bold (lines 163-167) --

    def test_is_cell_bold_true(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        run = MagicMock()
        run.bold = True
        cell.paragraphs = [MagicMock(runs=[run])]
        assert extractor._is_cell_bold(cell) is True

    def test_is_cell_bold_false(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        run = MagicMock()
        run.bold = False
        cell.paragraphs = [MagicMock(runs=[run])]
        assert extractor._is_cell_bold(cell) is False

    def test_is_cell_bold_no_runs(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        cell.paragraphs = [MagicMock(runs=[])]
        assert extractor._is_cell_bold(cell) is False

    def test_is_cell_bold_multiple_paragraphs(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        cell = MagicMock()
        run1 = MagicMock()
        run1.bold = False
        run2 = MagicMock()
        run2.bold = True
        cell.paragraphs = [
            MagicMock(runs=[run1]),
            MagicMock(runs=[run2]),
        ]
        assert extractor._is_cell_bold(cell) is True

    # -- _contains_header_keywords (lines 171-177) --

    def test_contains_header_keywords_common(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._contains_header_keywords(["Name", "Date"]) is True

    def test_contains_header_keywords_substring(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._contains_header_keywords(["Unit Price", "Amount"]) is True

    def test_contains_header_keywords_no_match(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._contains_header_keywords(["apple", "banana"]) is False

    def test_contains_header_keywords_empty(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._contains_header_keywords([]) is False

    def test_contains_header_keywords_mixed_case(self, extractor):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert extractor._contains_header_keywords(["name", "VALUE"]) is True

# ===================================================================
# TABLE CAPTION MATCHER — Lines 37-44, 53-163, 167-175, 179-180
# ===================================================================

class TestTableCaptionMatcherGaps:
    """Covers all caption_matcher lines."""

    @pytest.fixture
    def matcher(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        return TableCaptionMatcher()

    # -- __init__ (lines 37-44) --

    def test_init_defaults(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        matcher = TableCaptionMatcher()
        assert matcher.search_window_above == 2
        assert matcher.search_window_below == 1
        assert matcher.caption_regex is not None

    def test_init_custom(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        matcher = TableCaptionMatcher(search_window_above=5, search_window_below=3)
        assert matcher.search_window_above == 5
        assert matcher.search_window_below == 3

    def test_caption_regex_compiled(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        assert matcher.caption_regex.match("Table 1: Results")
        assert matcher.caption_regex.match("TABLE 2. Data")
        assert matcher.caption_regex.match("Table 1.1: Sub")
        assert matcher.caption_regex.match("Table I: Roman")
        assert matcher.caption_regex.match("Table A: Letter")
        assert not matcher.caption_regex.match("Figure 1: Not a table")

    # -- process (lines 53-163) --

    def test_no_tables_early_return(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_no_blocks_early_return(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0),
        ])
        result = matcher.process(doc)
        assert result is doc

    def test_empty_blocks_and_tables(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t")
        result = matcher.process(doc)
        assert result is doc

    def test_references_boundary_excludes_candidates_after(self, matcher):
        """Caption candidates after refs heading are excluded (lines 69-70, 116-117)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="x1", index=0, text="Data.", block_type=BlockType.BODY),
            Block(block_id="ref", index=1, text="References", block_type=BlockType.REFERENCES_HEADING),
            Block(block_id="c1", index=2, text="Table 1. After.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0),
        ])
        result = matcher.process(doc)
        # Caption at index 2 is after refs, so excluded from block_map.
        # No other caption candidate available, so no match.
        assert result.tables[0].caption_text is None

    def test_heading_excluded_from_block_map(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="h1", index=0, text="Table 1. Intro", block_type=BlockType.HEADING_1),
            Block(block_id="b1", index=1, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text is None

    def test_already_assigned_block_id_skipped(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="shared", index=0, text="Table 1. Shared.", block_type=BlockType.BODY),
            Block(block_id="b1", index=1, text="Body.", block_type=BlockType.BODY),
            Block(block_id="b2", index=2, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
            Table(table_id="t2", num_rows=1, num_cols=1, index=1, block_index=2),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. Shared."
        assert result.tables[1].caption_text is None

    def test_references_heading_skipped_as_caption(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="rh", index=0, text="Table 1. Refs", block_type=BlockType.REFERENCES_HEADING),
            Block(block_id="b1", index=1, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text is None

    def test_prev_table_boundary(self, matcher):
        """Caption before prev_table_idx excluded (line 118)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. First.", block_type=BlockType.BODY),
            Block(block_id="x1", index=1, text="Data.", block_type=BlockType.BODY),
            Block(block_id="c2", index=2, text="Table 2. Second.", block_type=BlockType.BODY),
            Block(block_id="x2", index=3, text="Data.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
            Table(table_id="t2", num_rows=1, num_cols=1, index=1, block_index=3),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. First."
        assert result.tables[1].caption_text == "Table 2. Second."

    def test_equal_distance_tiebreaker_prefers_above(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="above", index=0, text="Table 1. Above.", block_type=BlockType.BODY),
            Block(block_id="body", index=1, text="Body.", block_type=BlockType.BODY),
            Block(block_id="below", index=2, text="Table 1. Below.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. Above."

    def test_missing_caption_sets_metadata(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="No caption.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0),
        ])
        result = matcher.process(doc)
        assert result.tables[0].metadata.get("caption_status") == "Missing"

    def test_existing_caption_preserved(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0,
                  caption_text="Already set."),
        ])
        result = matcher.process(doc)
        assert "caption_status" not in result.tables[0].metadata

    def test_table_list_pos_fallback_linear_search(self, matcher):
        """block_index not in list_index_map triggers linear search (lines 84-91)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. Caption.", block_type=BlockType.BODY),
            Block(block_id="b1", index=10, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=5),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. Caption."

    def test_table_list_pos_fallback_to_end(self, matcher):
        """block_index > all indices => pos = len(blocks)-1 (line 91)."""
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. Caption.", block_type=BlockType.BODY),
            Block(block_id="b1", index=1, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=99),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1. Caption."

    def test_caption_block_type_changed(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. Type.", block_type=BlockType.BODY),
            Block(block_id="b1", index=1, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
        ])
        result = matcher.process(doc)
        cap_block = next(b for b in result.blocks if b.block_id == "c1")
        assert cap_block.block_type == BlockType.TABLE_CAPTION
        assert cap_block.metadata.get("linked_table_id") == "t1"

    def test_per_table_exception_caught(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="Table 1. Test.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0),
        ])
        with patch.object(matcher, "caption_regex") as mock_regex:
            mock_regex.match.side_effect = Exception("regex fail")
            result = matcher.process(doc)
            assert result is doc

    def test_top_level_exception_caught(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="b1", index=0, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0),
        ])
        with patch.object(matcher, "_find_references_start_index", side_effect=Exception("boom")):
            result = matcher.process(doc)
            stages = {s.stage_name: s.status for s in result.processing_history}
            assert stages.get("table_caption_matching") == "error"

    def test_success_stage_added(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. Match.", block_type=BlockType.BODY),
            Block(block_id="x1", index=1, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1),
        ])
        result = matcher.process(doc)
        stages = {s.stage_name: s.status for s in result.processing_history}
        assert stages.get("table_caption_matching") == "success"

    def test_search_window_respected(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        matcher.search_window_above = 1
        doc = PipelineDocument(document_id="t", blocks=[
            Block(block_id="c1", index=0, text="Table 1. Far.", block_type=BlockType.BODY),
            Block(block_id="x1", index=1, text="Mid.", block_type=BlockType.BODY),
            Block(block_id="x2", index=2, text="Body.", block_type=BlockType.BODY),
        ], tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=2),
        ])
        result = matcher.process(doc)
        assert result.tables[0].caption_text is None

    # -- _find_references_start_index (lines 167-175) --

    def test_find_refs_via_block_type(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="r1", index=5, text="References", block_type=BlockType.REFERENCES_HEADING),
        ]
        assert matcher._find_references_start_index(blocks) == 5

    def test_find_refs_via_keyword_heading_1(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="r1", index=3, text="References ", block_type=BlockType.HEADING_1),
        ]
        assert matcher._find_references_start_index(blocks) == 3

    def test_find_refs_via_bibliography(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="b1", index=7, text="Bibliography ", block_type=BlockType.HEADING_2),
        ]
        assert matcher._find_references_start_index(blocks) == 7

    def test_find_refs_via_works_cited(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="b1", index=9, text="Works Cited ", block_type=BlockType.HEADING_3),
        ]
        assert matcher._find_references_start_index(blocks) == 9

    def test_find_refs_keyword_non_heading(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="b1", index=4, text="references", block_type=BlockType.BODY),
        ]
        assert matcher._find_references_start_index(blocks) is None

    def test_find_refs_none(self, matcher):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        blocks = [
            Block(block_id="b1", index=0, text="Introduction", block_type=BlockType.HEADING_1),
        ]
        assert matcher._find_references_start_index(blocks) is None

    # -- match_table_captions convenience (lines 179-180) --

    def test_match_table_captions_convenience(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = PipelineDocument(document_id="t", blocks=[], tables=[])
        result = match_table_captions(doc)
        assert result is doc

# ===================================================================
# TABLE RENDERER — Lines 23, 29-86
# ===================================================================

class TestTableRendererGaps:
    """Covers all renderer lines."""

    @pytest.fixture
    def renderer(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        return TableRenderer()

    @pytest.fixture
    def simple_table(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        return Table(
            table_id="tbl_001",
            num_rows=2, num_cols=2,
            index=0, block_index=0,
            cells=[
                TableCell(row=0, col=0, text="A1", bold=True),
                TableCell(row=0, col=1, text="B1", bold=True),
                TableCell(row=1, col=0, text="A2"),
                TableCell(row=1, col=1, text="B2"),
            ],
            data=[["A1", "B1"], ["A2", "B2"]],
            rows=[["A1", "B1"], ["A2", "B2"]],
            has_header=True,
        )

    # -- __init__ (line 23) --

    def test_init(self):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        renderer = TableRenderer()
        assert renderer is not None

    # -- render (lines 29-86) --

    def test_none_table_returns(self, renderer):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        renderer.render(doc, None)
        doc.add_table.assert_not_called()

    def test_no_rows_returns(self, renderer):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        tbl = Table(table_id="e", num_rows=0, num_cols=0, index=0, block_index=0)
        renderer.render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_no_cols_returns(self, renderer):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        tbl = Table(table_id="e", num_rows=1, num_cols=0, index=0, block_index=0,
                     data=[[]], rows=[[]])
        renderer.render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_caption_with_exact_prefix(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        para = MagicMock()
        doc.add_paragraph.return_value = para
        simple_table.caption_text = "Table 1: Experimental results"
        renderer.render(doc, simple_table)
        calls = para.add_run.call_args_list
        assert any("Table 1:" in str(c[0]) for c in calls)
        assert any("Experimental results" in str(c[0]) for c in calls)

    def test_caption_with_different_number(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        para = MagicMock()
        doc.add_paragraph.return_value = para
        simple_table.caption_text = "Table 2: Results"
        renderer.render(doc, simple_table)
        calls = para.add_run.call_args_list
        assert any("Table 1:" in str(c[0]) for c in calls)

    def test_caption_without_table_prefix(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        para = MagicMock()
        doc.add_paragraph.return_value = para
        simple_table.caption_text = "Performance metrics"
        renderer.render(doc, simple_table)
        calls = para.add_run.call_args_list
        assert any("Table 1:" in str(c[0]) for c in calls)

    def test_caption_center_alignment(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        para = MagicMock()
        doc.add_paragraph.return_value = para
        simple_table.caption_text = "Some caption"
        renderer.render(doc, simple_table)
        assert para.alignment is not None

    def test_no_caption_skips_paragraph(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        simple_table.caption_text = None
        renderer.render(doc, simple_table)
        doc.add_paragraph.assert_not_called()

    def test_style_application(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()
        renderer.render(doc, simple_table)
        assert word_tbl.style == "Table Grid"

    def test_style_not_present(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {}
        doc.add_table.return_value = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        renderer.render(doc, simple_table)
        word_tbl = doc.add_table.return_value
        assert not hasattr(word_tbl, "style") or word_tbl.style != "Table Grid"

    def test_style_application_exception(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()

        def raise_on_set(inst, val):
            from app.models import PipelineDocument, Block, BlockType, Table, TableCell
            raise Exception("style fail")
        type(word_tbl).style = property(fget=lambda s: "mock", fset=raise_on_set)
        renderer.render(doc, simple_table)
        doc.add_table.assert_called_once()

    def test_cell_population(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        doc.add_table.return_value = word_tbl
        row0 = MagicMock()
        row1 = MagicMock()
        c00 = MagicMock()
        c01 = MagicMock()
        c10 = MagicMock()
        c11 = MagicMock()
        row0.cells = [c00, c01]
        row1.cells = [c10, c11]
        word_tbl.rows = [row0, row1]
        doc.add_paragraph.return_value = MagicMock()
        renderer.render(doc, simple_table)
        assert c00.text == "A1"
        assert c11.text == "B2"

    def test_cell_empty_text(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        row0 = MagicMock()
        c00 = MagicMock()
        row0.cells = [c00]
        word_tbl.rows = [row0]
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()
        simple_table.cells = [TableCell(row=0, col=0, text="")]
        renderer.render(doc, simple_table)
        assert c00.text == ""

    def test_cell_out_of_bounds_skipped(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        row0 = MagicMock()
        row0.cells = [MagicMock()]
        word_tbl.rows = [row0]
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()
        simple_table.cells = [
            TableCell(row=0, col=0, text="ok"),
            TableCell(row=5, col=5, text="out"),
        ]
        renderer.render(doc, simple_table)

    def test_cell_population_exception_handled(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        row = MagicMock()
        row.cells = MagicMock()
        row.cells.__getitem__.side_effect = IndexError("no cell")
        word_tbl.rows = [row]
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()
        renderer.render(doc, simple_table)

    def test_nested_table_rendering(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        row0 = MagicMock()
        c00 = MagicMock()
        row0.cells = [c00]
        word_tbl.rows = [row0]
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()

        nested = Table(table_id="n1", num_rows=1, num_cols=1, index=1, block_index=1,
                       data=[["inner"]], cells=[TableCell(row=0, col=0, text="inner")])
        simple_table.cells = [
            TableCell(row=0, col=0, text="parent", metadata={"nested_tables": [nested]})
        ]
        renderer.render(doc, simple_table)

    def test_nested_table_failure_adds_fallback(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        word_tbl = MagicMock()
        row0 = MagicMock()
        c00 = MagicMock()
        row0.cells = [c00]
        word_tbl.rows = [row0]
        doc.add_table.return_value = word_tbl
        doc.add_paragraph.return_value = MagicMock()

        failing_nested = Table(table_id="bad_nest", num_rows=1, num_cols=1,
                               index=1, block_index=1,
                               data=[["x"]], cells=[TableCell(row=0, col=0, text="x")])
        simple_table.cells = [
            TableCell(row=0, col=0, text="parent",
                      metadata={"nested_tables": [failing_nested]})
        ]

        original_render = renderer.render
        def render_side_effect(d, tbl, number=None):
            from app.models import PipelineDocument, Block, BlockType, Table, TableCell
            if d is c00:
                raise Exception("nested fail")
            return original_render(d, tbl, number=number)

        with patch.object(renderer, "render", side_effect=render_side_effect):
            renderer.render(doc, simple_table)
        c00.add_paragraph.assert_called_once()

    def test_outer_exception_raised(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_paragraph.side_effect = RuntimeError("caption fail")
        simple_table.caption_text = "Table 1: Test"
        with pytest.raises(RuntimeError, match="caption fail"):
            renderer.render(doc, simple_table)

    def test_render_with_number_override(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        para = MagicMock()
        doc.add_paragraph.return_value = para
        simple_table.caption_text = "Test caption"
        renderer.render(doc, simple_table, number=5)
        calls = para.add_run.call_args_list
        assert any("Table 5:" in str(c[0]) for c in calls)

    def test_render_returns_none(self, renderer, simple_table):
        from app.models import PipelineDocument, Block, BlockType, Table, TableCell
        doc = MagicMock()
        doc.styles = {"Table Grid": MagicMock()}
        doc.add_table.return_value = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        result = renderer.render(doc, simple_table)
        assert result is None
