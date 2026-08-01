import pytest
from unittest.mock import MagicMock


def _make_table(rows=None, caption_text=None, index=0, table_id="tbl_001"):
    tbl = MagicMock()
    tbl.rows = rows or [["A", "B"], ["C", "D"]]
    tbl.caption_text = caption_text
    tbl.index = index
    tbl.table_id = table_id
    cells = []
    for r_idx, row in enumerate(tbl.rows):
        for c_idx in range(len(row)):
            cell = MagicMock()
            cell.row = r_idx
            cell.col = c_idx
            cell.text = row[c_idx]
            cell.metadata = {"nested_tables": []}
            cells.append(cell)
    tbl.cells = cells
    return tbl


class TestRender:
    def test_no_table_model(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        renderer.render(doc, None)
        doc.add_table.assert_not_called()

    def test_empty_rows(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        tbl = MagicMock()
        tbl.rows = []
        tbl.caption_text = None
        renderer.render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_no_cols(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        tbl = _make_table(rows=[[]])
        renderer.render(doc, tbl)
        doc.add_table.assert_not_called()

    def test_basic_render(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.add_table.return_value = MagicMock()
        doc.styles = []

        tbl = _make_table()
        renderer.render(doc, tbl)
        doc.add_table.assert_called_once_with(rows=2, cols=2)

    def test_caption_added(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        doc.add_table.return_value = MagicMock()
        doc.styles = []

        tbl = _make_table(caption_text="Table 1: Results")
        renderer.render(doc, tbl, number=1)
        doc.add_paragraph.assert_called_with(style="Caption")

    def test_caption_matching_format(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.add_paragraph.return_value = MagicMock()
        doc.add_table.return_value = MagicMock()
        doc.styles = []

        tbl = _make_table(caption_text="Table 1: Results", index=0)
        renderer.render(doc, tbl, number=1)
        doc.add_paragraph.assert_called_with(style="Caption")

    def test_render_with_style(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.styles = ["Table Grid"]
        doc.add_table.return_value = MagicMock()

        tbl = _make_table()
        renderer.render(doc, tbl)
        word_table = doc.add_table.return_value
        assert word_table.style == 'Table Grid'

    def test_render_exception_raised(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.add_table.side_effect = Exception("render error")

        tbl = _make_table()
        with pytest.raises(Exception):
            renderer.render(doc, tbl)

    def test_nested_table_rendering(self):
        from app.pipeline.tables.renderer import TableRenderer
        renderer = TableRenderer()
        doc = MagicMock()
        doc.add_table.return_value = MagicMock()
        word_table = doc.add_table.return_value
        word_cell = MagicMock()
        word_table.rows[0].cells[0] = word_cell

        nested = _make_table(rows=[["Nested"]], table_id="tbl_nested")
        cell_with_nested = MagicMock()
        cell_with_nested.row = 0
        cell_with_nested.col = 0
        cell_with_nested.text = "Outer"
        cell_with_nested.metadata = {"nested_tables": [nested]}
        inner_cell = MagicMock()
        inner_cell.row = 0
        inner_cell.col = 0
        inner_cell.text = "Inner"
        inner_cell.metadata = {"nested_tables": []}
        nested.cells = [inner_cell]
        nested.rows = [["Nested"]]
        tbl_with_nested = MagicMock()
        tbl_with_nested.rows = [["Outer"]]
        tbl_with_nested.cells = [cell_with_nested]
        tbl_with_nested.caption_text = None
        tbl_with_nested.index = 0
        tbl_with_nested.table_id = "tbl_main"
        doc.styles = []

        renderer.render(doc, tbl_with_nested)
        assert renderer is not None
