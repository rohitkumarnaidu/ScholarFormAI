

class TestNormalizeUnicode:
    def test_no_changes(self):
        from app.utils.text_utils import normalize_unicode
        assert normalize_unicode("Hello World") == "Hello World"

    def test_fancy_quotes(self):
        from app.utils.text_utils import normalize_unicode
        result = normalize_unicode("\u201cquote\u201d")
        assert '"' in result

    def test_em_dash(self):
        from app.utils.text_utils import normalize_unicode
        result = normalize_unicode("\u2014hello")
        assert result == "--hello"

    def test_non_breaking_space(self):
        from app.utils.text_utils import normalize_unicode
        result = normalize_unicode("a\u00A0b")
        assert result == "a b"

    def test_bullet_char(self):
        from app.utils.text_utils import normalize_unicode
        result = normalize_unicode("\u2023 item")
        assert "•" in result

    def test_combined_mappings(self):
        from app.utils.text_utils import normalize_unicode
        text = "\u201cHello\u201d \u2014 \u2018world\u2019\u00A0test"
        result = normalize_unicode(text)
        assert result == '"Hello" -- \'world\' test'


class TestNormalizeWhitespace:
    def test_collapses_spaces(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("Hello    world")
        assert result == "Hello world"

    def test_replaces_tabs(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("Hello\tworld")
        assert " " in result

    def test_collapse_newlines(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("a\n\n\n\nb", collapse_newlines=True)
        assert result == "a\n\nb"

    def test_preserves_single_newline(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("Hello\nworld", collapse_newlines=True)
        assert result == "Hello\nworld"

    def test_collapse_newlines_default_false(self):
        from app.utils.text_utils import normalize_whitespace
        lines = "a\n\n\n\nb"
        result = normalize_whitespace(lines, collapse_newlines=False)
        assert result == "a\n\n\n\nb"

    def test_empty_string(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("")
        assert result == ""

    def test_trailing_leading_spaces(self):
        from app.utils.text_utils import normalize_whitespace
        result = normalize_whitespace("  foo  ")
        assert result == "foo"


class TestNormalizeListMarkers:
    def test_bullet_marker(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("\u2022 Item")
        assert "•" in result

    def test_no_marker(self):
        from app.utils.text_utils import normalize_list_markers
        assert normalize_list_markers("Plain text") == "Plain text"

    def test_empty_string(self):
        from app.utils.text_utils import normalize_list_markers
        assert normalize_list_markers("") == ""

    def test_bullet_with_extra_trailing_space(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("\u2022   Item")
        assert result == "• Item"

    def test_triangular_bullet(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("\u2023 Item")
        assert result == "• Item"

    def test_black_circle(self):
        from app.utils.text_utils import normalize_list_markers
        result = normalize_list_markers("\u25CF Item")
        assert result == "• Item"


class TestCleanMetadataField:
    def test_basic(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("  Hello World  ")
        assert result == "Hello World"

    def test_special_chars(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("Test\u2014with\u2013dashes")
        assert "--" in result or "-" in result

    def test_none(self):
        from app.utils.text_utils import clean_metadata_field
        assert clean_metadata_field(None) is None

    def test_empty(self):
        from app.utils.text_utils import clean_metadata_field
        assert clean_metadata_field("") == ""

    def test_control_chars_removed(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("Hello\x00World\x01Test")
        assert result == "HelloWorldTest"

    def test_newlines_replaced(self):
        from app.utils.text_utils import clean_metadata_field
        result = clean_metadata_field("Hello\nWorld\r\nTest")
        assert " " in result
        assert "\n" not in result


class TestNormalizeBlockText:
    def test_none(self):
        from app.utils.text_utils import normalize_block_text
        assert normalize_block_text(None) == ""

    def test_empty_not_ok(self):
        from app.utils.text_utils import normalize_block_text
        result = normalize_block_text("   ", is_empty_ok=False)
        assert result == "   "

    def test_empty_ok(self):
        from app.utils.text_utils import normalize_block_text
        assert normalize_block_text("   ") == ""

    def test_normalization_applied(self):
        from app.utils.text_utils import normalize_block_text
        result = normalize_block_text("\u201cHello\u201d \u2014 world")
        assert result == '"Hello" -- world'


class TestNormalizeTableCellText:
    def test_empty(self):
        from app.utils.text_utils import normalize_table_cell_text
        assert normalize_table_cell_text("") == ""

    def test_none(self):
        from app.utils.text_utils import normalize_table_cell_text
        assert normalize_table_cell_text(None) == ""

    def test_newlines_replaced_with_spaces(self):
        from app.utils.text_utils import normalize_table_cell_text
        result = normalize_table_cell_text("Hello\nWorld\r\nTest")
        assert "\n" not in result
        assert "\r" not in result

    def test_multiple_whitespace_collapsed(self):
        from app.utils.text_utils import normalize_table_cell_text
        result = normalize_table_cell_text("Hello    World")
        assert result == "Hello World"

    def test_unicode_normalization(self):
        from app.utils.text_utils import normalize_table_cell_text
        result = normalize_table_cell_text("\u201cquote\u201d")
        assert '"' in result

    def test_trimmed(self):
        from app.utils.text_utils import normalize_table_cell_text
        result = normalize_table_cell_text("  text  ")
        assert result == "text"
