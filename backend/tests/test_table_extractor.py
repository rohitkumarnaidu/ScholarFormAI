from unittest.mock import MagicMock, patch


def _make_docx_cell(text="", bold=False):
    cell = MagicMock()
    cell.text = text
    cell._tc = MagicMock()
    cell._tc.iter.return_value = []
    para = MagicMock()
    run = MagicMock()
    run.bold = bold
    para.runs = [run]
    cell.paragraphs = [para]
    cell._element = MagicMock()
    cell._element.findall.return_value = []
    cell._parent = MagicMock()
    return cell


def _make_docx_row(cells_texts, bold_first=False):
    row = MagicMock()
    row.cells = [_make_docx_cell(t, bold=(bold_first and i == 0)) for i, t in enumerate(cells_texts)]
    return row


class TestExtract:
    def test_basic_table(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        table = MagicMock()
        table.rows = [_make_docx_row(["Header 1", "Header 2"]),
                       _make_docx_row(["Data 1", "Data 2"])]

        result = extractor.extract(table, "tbl_001", 0, 0)
        assert result.table_id == "tbl_001"
        assert result.num_rows == 2
        assert result.num_cols == 2
        assert result.data[0] == ["Header 1", "Header 2"]
        assert result.data[1] == ["Data 1", "Data 2"]

    def test_header_detection_by_bold(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        table = MagicMock()
        table.rows = [_make_docx_row(["Name", "Value"], bold_first=True),
                       _make_docx_row(["Alice", "42"])]

        result = extractor.extract(table, "tbl_002", 1, 1)
        assert result.has_header is True

    def test_header_detection_by_keywords(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        table = MagicMock()
        table.rows = [_make_docx_row(["Name", "Date"]),
                       _make_docx_row(["Alice", "2024"])]

        result = extractor.extract(table, "tbl_003", 2, 2)
        assert result.has_header is True



    def test_empty_cell_deep_fallback(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        cell = _make_docx_cell("")
        # Mock deep extraction to return hidden text
        with patch.object(extractor, "_extract_deep_xml_text", return_value="hidden"):
            row = MagicMock()
            row.cells = [cell]
            table = MagicMock()
            table.rows = [row]

            result = extractor.extract(table, "tbl_005", 4, 4)
        assert result.data[0][0] == "hidden"

    def test_empty_data_returns_empty_table(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        table = MagicMock()
        table.rows = []

        result = extractor.extract(table, "tbl_006", 5, 5)
        assert result.num_rows == 0
        assert result.num_cols == 0


class TestIsCellBold:
    def test_bold_true(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        cell = _make_docx_cell("Text", bold=True)
        assert extractor._is_cell_bold(cell) is True

    def test_bold_false(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        cell = _make_docx_cell("Text", bold=False)
        assert extractor._is_cell_bold(cell) is False


class TestContainsHeaderKeywords:
    def test_common_header(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        assert extractor._contains_header_keywords(["Name", "Date"]) is True

    def test_no_header(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        assert extractor._contains_header_keywords(["Alice", "42"]) is False

    def test_partial_match(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        assert extractor._contains_header_keywords(["Qty", "Amount"]) is True


class TestNormalizeCellText:
    def test_strips_whitespace(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        assert extractor._normalize_cell_text("  hello  ") == "hello"

    def test_empty(self):
        from app.pipeline.tables.extractor import TableExtractor
        extractor = TableExtractor()
        assert extractor._normalize_cell_text("") == ""
        assert extractor._normalize_cell_text(None) == ""
