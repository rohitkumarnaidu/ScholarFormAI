# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import ANY, MagicMock, PropertyMock, patch

# ─── Fixtures ──────────────────────────────────────────────────────────────────


def _mock_block(index, text="", block_type="BODY", is_heading=False, block_id=None):
    b = MagicMock()
    b.index = index
    b.text = text
    b.block_type = block_type
    b.block_id = block_id or f"b{index}"
    b.metadata = {}
    b.is_heading.return_value = is_heading
    return b


def _mock_table(table_id="T1", block_index=0, rows=None, caption_text=""):
    t = MagicMock()
    t.table_id = table_id
    t.block_index = block_index
    t.caption_text = caption_text
    t.caption_block_id = None
    t.metadata = {}
    t.rows = rows or []
    return t


# ─── TableExtractor ────────────────────────────────────────────────────────────


class TestTableExtractor:
    def test_normalize_cell_text_none(self):
        from app.pipeline.tables.extractor import TableExtractor

        assert TableExtractor()._normalize_cell_text("") == ""
        assert TableExtractor()._normalize_cell_text(None) == ""

    def test_normalize_cell_text_strip(self):
        from app.pipeline.tables.extractor import TableExtractor

        assert TableExtractor()._normalize_cell_text("  hello  ") == "hello"

    def test_contains_header_keywords_true(self):
        from app.pipeline.tables.extractor import TableExtractor

        assert TableExtractor()._contains_header_keywords(["Name", "Date"]) is True

    def test_contains_header_keywords_false(self):
        from app.pipeline.tables.extractor import TableExtractor

        assert TableExtractor()._contains_header_keywords(["foo", "bar"]) is False

    def test_contains_header_keywords_substring_match(self):
        from app.pipeline.tables.extractor import TableExtractor

        assert TableExtractor()._contains_header_keywords(["Quantity", "Amount"]) is True

    def test_is_cell_bold_true(self):
        from app.pipeline.tables.extractor import TableExtractor

        cell = MagicMock()
        run = MagicMock()
        run.bold = True
        para = MagicMock()
        para.runs = [run]
        cell.paragraphs = [para]
        assert TableExtractor()._is_cell_bold(cell) is True

    def test_is_cell_bold_false(self):
        from app.pipeline.tables.extractor import TableExtractor

        cell = MagicMock()
        run = MagicMock()
        run.bold = False
        para = MagicMock()
        para.runs = [run]
        cell.paragraphs = [para]
        assert TableExtractor()._is_cell_bold(cell) is False

    def test_extract_deep_xml_text_success(self):
        from app.pipeline.tables.extractor import TableExtractor

        cell = MagicMock()
        node1 = MagicMock()
        node1.tag = "}t"
        node1.text = "Hello"
        node2 = MagicMock()
        node2.tag = "}t"
        node2.text = " World"
        cell._tc.iter.return_value = [node1, node2]
        assert TableExtractor()._extract_deep_xml_text(cell) == "Hello World"

    def test_extract_deep_xml_text_empty(self):
        from app.pipeline.tables.extractor import TableExtractor

        cell = MagicMock()
        node = MagicMock()
        node.tag = "}something"
        node.text = "text"
        cell._tc.iter.return_value = [node]
        assert TableExtractor()._extract_deep_xml_text(cell) == ""

    def test_extract_deep_xml_text_exception(self):
        from app.pipeline.tables.extractor import TableExtractor

        cell = MagicMock()
        cell._tc.iter.side_effect = Exception("boom")
        assert TableExtractor()._extract_deep_xml_text(cell) == ""

    def test_extract_basic(self):
        from app.pipeline.tables.extractor import TableExtractor

        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "A"
        cell11.paragraphs = []
        cell12 = MagicMock()
        cell12.text = "B"
        cell12.paragraphs = []
        row1.cells = [cell11, cell12]
        row2 = MagicMock()
        cell21 = MagicMock()
        cell21.text = "1"
        cell21.paragraphs = []
        cell22 = MagicMock()
        cell22.text = "2"
        cell22.paragraphs = []
        row2.cells = [cell21, cell22]
        docx_table.rows = [row1, row2]

        result = TableExtractor().extract(docx_table, "T1", 0, 0)
        assert result.table_id == "T1"
        assert result.num_rows == 2
        assert result.num_cols == 2
        assert result.data == [["A", "B"], ["1", "2"]]

    def test_extract_with_row_normalization(self):
        from app.pipeline.tables.extractor import TableExtractor

        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "A"
        cell11.paragraphs = []
        cell12 = MagicMock()
        cell12.text = ""
        cell12.paragraphs = []
        row1.cells = [cell11, cell12]
        row2 = MagicMock()
        cell21 = MagicMock()
        cell21.text = "X"
        cell21.paragraphs = []
        cell22 = MagicMock()
        cell22.text = "Y"
        cell22.paragraphs = []
        row2.cells = [cell21, cell22]
        docx_table.rows = [row1, row2]

        result = TableExtractor().extract(docx_table, "T1", 0, 0)
        assert result.num_cols == 2
        assert result.data[0] == ["A", ""]

    def test_extract_with_deep_fallback(self):
        from app.pipeline.tables.extractor import TableExtractor

        docx_table = MagicMock()
        row1 = MagicMock()
        cell_empty = MagicMock()
        cell_empty.text = ""
        cell_empty.paragraphs = []
        cell_empty._tc = MagicMock()
        node = MagicMock()
        node.tag = "}t"
        node.text = "DeepText"
        cell_empty._tc.iter.return_value = [node]
        row1.cells = [cell_empty]
        docx_table.rows = [row1]

        result = TableExtractor().extract(docx_table, "T1", 0, 0)
        assert result.data[0][0] == "DeepText"

    def test_extract_with_header_detection_bold(self):
        from app.pipeline.tables.extractor import TableExtractor

        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "Name"
        cell11.paragraphs = []
        run = MagicMock()
        run.bold = True
        para = MagicMock()
        para.runs = [run]
        cell11.paragraphs = [para]
        row1.cells = [cell11]
        docx_table.rows = [row1]

        result = TableExtractor().extract(docx_table, "T1", 0, 0)
        assert result.has_header is True

    def test_extract_with_header_detection_keywords(self):
        from app.pipeline.tables.extractor import TableExtractor

        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "Name"
        cell11.paragraphs = []
        row1.cells = [cell11]
        docx_table.rows = [row1]

        result = TableExtractor().extract(docx_table, "T1", 0, 0)
        assert result.has_header is True

    def test_extract_nested_table(self):
        from app.pipeline.tables.extractor import TableExtractor

        ext = TableExtractor()
        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "A"
        cell11.paragraphs = []
        cell11._element = MagicMock()
        tbl_xml = MagicMock()
        cell11._element.findall.return_value = [tbl_xml]
        cell11._parent._parent._parent = MagicMock()
        row1.cells = [cell11]
        docx_table.rows = [row1]

        result = ext.extract(docx_table, "T1", 0, 0)
        nested = result.cells[0].metadata.get("nested_tables", [])
        assert len(nested) == 1
        assert nested[0].table_id == "T1_n0"

    def test_extract_nested_table_exception(self):
        from app.pipeline.tables.extractor import TableExtractor

        ext = TableExtractor()
        docx_table = MagicMock()
        row1 = MagicMock()
        cell11 = MagicMock()
        cell11.text = "A"
        cell11.paragraphs = []
        cell11._element = MagicMock()
        cell11._element.findall.side_effect = Exception("xml err")
        row1.cells = [cell11]
        docx_table.rows = [row1]

        result = ext.extract(docx_table, "T1", 0, 0)
        assert result.data[0][0] == "A"


# ─── TableCaptionMatcher ───────────────────────────────────────────────────────


class TestTableCaptionMatcher:
    def test_init_defaults(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        cm = TableCaptionMatcher()
        assert cm.search_window_above == 2
        assert cm.search_window_below == 1

    def test_init_custom(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        cm = TableCaptionMatcher(search_window_above=3, search_window_below=2)
        assert cm.search_window_above == 3
        assert cm.search_window_below == 2

    def test_find_references_start_index_none(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        assert TableCaptionMatcher()._find_references_start_index([]) is None

    def test_find_references_start_index_by_type(self):
        from app.models import BlockType
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        blk = _mock_block(5, "REFERENCES", block_type=BlockType.REFERENCES_HEADING)
        assert TableCaptionMatcher()._find_references_start_index([blk]) == 5

    def test_find_references_start_index_by_keyword(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        blk = _mock_block(10, "References", is_heading=True)
        assert TableCaptionMatcher()._find_references_start_index([blk]) == 10

    def test_process_no_tables(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        doc = MagicMock()
        doc.blocks = []
        doc.tables = []
        result = TableCaptionMatcher().process(doc)
        assert result is doc

    def test_process_no_blocks(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        doc = MagicMock()
        doc.blocks = []
        doc.tables = [_mock_table()]
        result = TableCaptionMatcher().process(doc)
        assert result is doc

    def test_process_matches_caption(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        tbl = _mock_table("T1", block_index=5, rows=[[]])
        cap_block = _mock_block(3, "Table 1: Results")
        blocks = [cap_block, _mock_block(5, "[table]", block_type="TABLE")]
        doc = MagicMock()
        doc.blocks = blocks
        doc.tables = [tbl]

        result = TableCaptionMatcher().process(doc)
        assert result is doc
        assert tbl.caption_text == "Table 1: Results"
        assert tbl.caption_block_id == "b3"
        doc.add_processing_stage.assert_called_once()

    def test_process_skips_heading_block(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        tbl = _mock_table("T1", block_index=5)
        heading = _mock_block(3, "Table 1: Results", is_heading=True)
        blocks = [heading, _mock_block(5, "[table]")]
        doc = MagicMock()
        doc.blocks = blocks
        doc.tables = [tbl]

        TableCaptionMatcher().process(doc)
        assert tbl.caption_text == ""

    def test_process_missing_caption(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        tbl = _mock_table("T1", block_index=5)
        blocks = [_mock_block(3, "Not a caption"), _mock_block(5, "[table]")]
        doc = MagicMock()
        doc.blocks = blocks
        doc.tables = [tbl]

        TableCaptionMatcher().process(doc)
        assert tbl.metadata.get("caption_status") == "Missing"

    def test_process_exception(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        doc = MagicMock()
        doc.blocks = [_mock_block(0, "x")]
        doc.tables = [MagicMock()]
        doc.tables[0].block_index = 0
        cm = TableCaptionMatcher()
        with patch.object(cm, "_find_references_start_index", side_effect=ValueError("boom")):
            result = cm.process(doc)
        assert result is doc
        doc.add_processing_stage.assert_called_once_with(
            stage_name="table_caption_matching", status="error", message=ANY
        )

    def test_caption_regex_matches(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        cm = TableCaptionMatcher()
        assert cm.caption_regex.match("Table 1: Results")
        assert cm.caption_regex.match("TABLE 2. Data")
        assert cm.caption_regex.match("Table 1.1: Sub")
        assert cm.caption_regex.match("Table I: Roman")
        assert cm.caption_regex.match("Table A: Letter")

    def test_caption_regex_no_match(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher

        cm = TableCaptionMatcher()
        assert not cm.caption_regex.match("Figure 1: test")
        assert not cm.caption_regex.match("Not a table caption")

    def test_match_table_captions_convenience(self):
        from app.pipeline.tables.caption_matcher import match_table_captions

        doc = MagicMock()
        doc.blocks = []
        doc.tables = []
        result = match_table_captions(doc)
        assert result is doc


# ─── TableRenderer ─────────────────────────────────────────────────────────────


class TestTableRenderer:
    def test_render_none_table(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        TableRenderer().render(doc, None)
        doc.add_paragraph.assert_not_called()
        doc.add_table.assert_not_called()

    def test_render_no_rows(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        tbl = _mock_table("T1", rows=[])
        TableRenderer().render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_render_no_caption(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        tbl = _mock_table("T1", rows=[["A", "B"]])
        tbl.cells = []
        TableRenderer().render(doc, tbl)
        doc.add_table.assert_called_once()

    def test_render_with_caption_exact_match(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        tbl = _mock_table("T1", block_index=0, caption_text="Table 1: Results")
        tbl.cells = []
        tbl.rows = [["A"]]
        tbl.index = 0
        with patch("app.pipeline.tables.renderer.WD_ALIGN_PARAGRAPH"):
            TableRenderer().render(doc, tbl)
        doc.add_paragraph.assert_called_once_with(style="Caption")
        doc.add_table.assert_called_once()

    def test_render_with_caption_different_number(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        tbl = _mock_table("T1", block_index=5, caption_text="Data table")
        tbl.cells = []
        tbl.rows = [["A"]]
        tbl.index = 5
        TableRenderer().render(doc, tbl, number=3)
        doc.add_paragraph.assert_called_once_with(style="Caption")
        doc.add_table.assert_called_once()

    def test_render_populates_cells(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        word_cell = MagicMock()
        word_row = MagicMock()
        word_row.cells = [word_cell]
        word_table = MagicMock()
        word_table.rows = [word_row]
        doc.add_table.return_value = word_table

        cell_model = MagicMock()
        cell_model.row = 0
        cell_model.col = 0
        cell_model.text = "Hello"
        cell_model.metadata = {}

        tbl = _mock_table("T1", rows=[["Hello"]])
        tbl.cells = [cell_model]
        TableRenderer().render(doc, tbl)
        assert word_cell.text == "Hello"

    def test_render_nested_table(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        word_table = MagicMock()
        word_cell = MagicMock()
        word_table.rows[0].cells[0] = word_cell
        doc.add_table.return_value = word_table

        nested_tbl = _mock_table("N1", rows=[["X"]])
        nested_tbl.cells = []
        cell_model = MagicMock()
        cell_model.row = 0
        cell_model.col = 0
        cell_model.text = "A"
        cell_model.metadata = {"nested_tables": [nested_tbl]}

        tbl = _mock_table("T1", rows=[["A"]])
        tbl.cells = [cell_model]
        TableRenderer().render(doc, tbl)
        word_cell.add_paragraph.assert_not_called()

    def test_render_nested_table_failure(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        word_cell = MagicMock()
        word_row = MagicMock()
        word_row.cells = [word_cell]
        word_table = MagicMock()
        word_table.rows = [word_row]
        doc.add_table.return_value = word_table

        nested_tbl = _mock_table("N1", rows=[["X"]])
        nested_tbl.cells = []
        # Make the nested table's rows raise to trigger the failure path
        type(nested_tbl).rows = PropertyMock(side_effect=ValueError("nested render error"))

        cell_model = MagicMock()
        cell_model.row = 0
        cell_model.col = 0
        cell_model.text = "A"
        cell_model.metadata = {"nested_tables": [nested_tbl]}

        tbl = _mock_table("T1", rows=[["A"]])
        tbl.cells = [cell_model]

        TableRenderer().render(doc, tbl)
        word_cell.add_paragraph.assert_called_once()

    def test_render_style_exception(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        style_prop = PropertyMock(side_effect=Exception("style err"))
        type(doc).styles = style_prop
        tbl = _mock_table("T1", rows=[["A"]])
        tbl.cells = []
        TableRenderer().render(doc, tbl)
        doc.add_table.assert_called_once()

    def test_render_cols_zero(self):
        from app.pipeline.tables.renderer import TableRenderer

        doc = MagicMock()
        tbl = _mock_table("T1", rows=[[]])
        tbl.cells = []
        TableRenderer().render(doc, tbl)
        doc.add_table.assert_not_called()
