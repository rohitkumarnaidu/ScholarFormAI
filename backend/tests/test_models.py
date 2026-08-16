import pytest

from app.models.equation import Equation
from app.models.figure import Figure, FigureType, ImageFormat
from app.models.reference import CitationStyle, Reference, ReferenceType
from app.models.table import Table, TableCell


class TestFigure:
    def test_create_figure(self):
        fig = Figure(figure_id="fig_001", index=0, width=800, height=600)
        assert fig.figure_id == "fig_001"
        assert fig.width == 800
        assert not fig.has_caption()

    def test_has_caption(self):
        fig = Figure(figure_id="fig_001", index=0, caption_text="Figure 1: Test")
        assert fig.has_caption()

    def test_no_caption_empty(self):
        fig = Figure(figure_id="fig_001", index=0, caption_text="")
        assert not fig.has_caption()

    def test_get_display_label_with_label(self):
        fig = Figure(figure_id="fig_001", index=0, label="Fig. 1")
        assert fig.get_display_label() == "Fig. 1"

    def test_get_display_label_with_number(self):
        fig = Figure(figure_id="fig_001", index=0, number=5)
        assert fig.get_display_label() == "Figure 5"

    def test_get_display_label_fallback(self):
        fig = Figure(figure_id="fig_001", index=0)
        assert "Figure fig_001" in fig.get_display_label()

    def test_image_format_default(self):
        fig = Figure(figure_id="fig_001", index=0)
        assert fig.image_format == ImageFormat.UNKNOWN

    def test_figure_type_default(self):
        fig = Figure(figure_id="fig_001", index=0)
        assert fig.figure_type == FigureType.UNKNOWN


class TestEquation:
    def test_create_equation(self):
        eq = Equation(equation_id="eqn_001", index=0, text="x = y", mathml="<math><mi>x</mi></math>")
        assert eq.equation_id == "eqn_001"
        assert eq.text == "x = y"
        assert eq.is_block

    def test_has_content_all_forms(self):
        eq = Equation(equation_id="eqn_001", index=0, text="x = y")
        assert eq.has_content()

    def test_has_content_no_forms(self):
        eq = Equation(equation_id="eqn_001", index=0)
        assert not eq.has_content()

    def test_get_display_number(self):
        eq = Equation(equation_id="eqn_001", index=0, number="(1)")
        assert eq.get_display_number() == "(1)"

    def test_get_display_number_empty(self):
        eq = Equation(equation_id="eqn_001", index=0)
        assert eq.get_display_number() == ""

    def test_inline_equation(self):
        eq = Equation(equation_id="eqn_001", index=0, is_block=False)
        assert not eq.is_block


class TestTableCell:
    def test_create_cell(self):
        cell = TableCell(row=0, col=0, text="Header")
        assert cell.text == "Header"
        assert cell.row == 0
        assert cell.col == 0

    def test_invalid_alignment(self):
        cell = TableCell(row=0, col=0, text="x", alignment="invalid")
        assert cell.alignment is None

    def test_valid_alignment(self):
        cell = TableCell(row=0, col=0, text="x", alignment="center")
        assert cell.alignment == "center"

    def test_header_cell(self):
        cell = TableCell(row=0, col=0, text="Header", is_header=True)
        assert cell.is_header


class TestTable:
    def test_create_table(self):
        tbl = Table(table_id="tbl_001", num_rows=3, num_cols=2, index=0, block_index=0)
        assert tbl.table_id == "tbl_001"
        assert tbl.num_rows == 3

    def test_has_caption(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0, caption_text="Table 1: Results")
        assert tbl.has_caption()

    def test_has_caption_empty(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0, caption_text="")
        assert not tbl.has_caption()

    def test_get_cell(self):
        cell = TableCell(row=1, col=2, text="Value")
        tbl = Table(table_id="tbl_001", num_rows=3, num_cols=3, index=0, block_index=0, cells=[cell])
        result = tbl.get_cell(1, 2)
        assert result is not None
        assert result.text == "Value"

    def test_get_cell_not_found(self):
        tbl = Table(table_id="tbl_001", num_rows=3, num_cols=3, index=0, block_index=0)
        assert tbl.get_cell(99, 99) is None

    def test_get_cell_negative(self):
        tbl = Table(table_id="tbl_001", num_rows=3, num_cols=3, index=0, block_index=0)
        assert tbl.get_cell(-1, 0) is None

    def test_get_display_label_with_label(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0, label="Table 1")
        assert tbl.get_display_label() == "Table 1"

    def test_get_display_label_with_number(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0, number=3)
        assert tbl.get_display_label() == "Table 3"

    def test_get_display_label_fallback(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0)
        assert "Table tbl_001" in tbl.get_display_label()

    def test_get_row_data_from_rows(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0, rows=[["a", "b"], ["c", "d"]])
        assert tbl.get_row_data(0) == ["a", "b"]

    def test_get_row_data_negative(self):
        tbl = Table(table_id="tbl_001", num_rows=2, num_cols=2, index=0, block_index=0)
        assert tbl.get_row_data(-1) == []

    def test_table_id_validation(self):
        with pytest.raises(ValueError):
            Table(table_id="", num_rows=0, num_cols=0, index=0, block_index=0)


class TestReference:
    def test_create_reference(self):
        ref = Reference(
            reference_id="ref_001", citation_key="Smith2020", raw_text="Smith, J. (2020). A paper.", index=0
        )
        assert ref.reference_id == "ref_001"
        assert ref.citation_key == "Smith2020"

    def test_get_primary_author(self):
        ref = Reference(
            reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0, authors=["Smith, J.", "Doe, A."]
        )
        assert ref.get_primary_author() == "Smith, J."

    def test_get_primary_author_empty(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0)
        assert ref.get_primary_author() is None

    def test_get_author_list_under_limit(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0, authors=["Smith, J."])
        assert ref.get_author_list() == "Smith, J."

    def test_get_author_list_et_al(self):
        ref = Reference(
            reference_id="ref_001",
            citation_key="Smith2020",
            raw_text="",
            index=0,
            authors=["Smith, J.", "Doe, A.", "Lee, K.", "Wang, L."],
        )
        assert "et al." in ref.get_author_list(max_authors=3)

    def test_get_author_list_empty(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0)
        assert ref.get_author_list() == "Unknown"

    def test_get_short_citation(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0)
        assert ref.get_short_citation() == "Smith2020"

    def test_has_doi(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0, doi="10.1234/abc")
        assert ref.has_doi()

    def test_has_no_doi(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0)
        assert not ref.has_doi()

    def test_reference_type_default(self):
        ref = Reference(reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0)
        assert ref.reference_type == ReferenceType.UNKNOWN

    def test_citation_style(self):
        ref = Reference(
            reference_id="ref_001", citation_key="Smith2020", raw_text="", index=0, style=CitationStyle.IEEE
        )
        assert ref.style == CitationStyle.IEEE
