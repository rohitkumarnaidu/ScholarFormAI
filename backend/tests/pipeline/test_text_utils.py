# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from app.utils.text_utils import (
    normalize_unicode,
    normalize_whitespace,
    normalize_list_markers,
    clean_metadata_field,
    normalize_block_text,
    normalize_table_cell_text,
)


class TestNormalizeUnicode:
    def test_quotes(self):
        result = normalize_unicode('\u201cHello\u201d')
        assert result == '"Hello"'

    def test_dashes(self):
        result = normalize_unicode('A \u2014 B \u2013 C')
        assert '--' in result or '-' in result

    def test_spaces(self):
        result = normalize_unicode('a\u00a0b')
        assert result == 'a b'

    def test_bullets(self):
        result = normalize_unicode('\u2022 item')
        assert '•' in result

    def test_empty_string(self):
        assert normalize_unicode('') == ''

    def test_ascii_passthrough(self):
        assert normalize_unicode('Hello world.') == 'Hello world.'


class TestNormalizeWhitespace:
    def test_collapse_spaces(self):
        result = normalize_whitespace('a    b   c')
        assert result == 'a b c'

    def test_tabs_to_spaces(self):
        result = normalize_whitespace('a\tb')
        assert result == 'a b'

    def test_trim_edges(self):
        result = normalize_whitespace('  hello  ')
        assert result == 'hello'

    def test_collapse_newlines(self):
        result = normalize_whitespace('a\n\n\n\nb', collapse_newlines=True)
        assert result == 'a\n\nb'

    def test_no_collapse_newlines(self):
        result = normalize_whitespace('a\n\n\nb', collapse_newlines=False)
        assert '  ' not in result

    def test_empty_string(self):
        assert normalize_whitespace('') == ''

    def test_only_whitespace(self):
        assert normalize_whitespace('   ') == ''


class TestNormalizeListMarkers:
    def test_bullet_char(self):
        assert normalize_list_markers('• item') == '• item'

    def test_triangular_bullet(self):
        result = normalize_list_markers('\u2023 item')
        assert result == '• item'

    def test_strips_whitespace(self):
        assert normalize_list_markers('  • item  ') == '• item'

    def test_hyphen_not_converted(self):
        assert normalize_list_markers('- item') == '- item'

    def test_no_marker(self):
        assert normalize_list_markers('item') == 'item'

    def test_empty_string(self):
        assert normalize_list_markers('') == ''


class TestCleanMetadataField:
    def test_normalizes_unicode(self):
        result = clean_metadata_field('\u201cTitle\u201d')
        assert '"Title"' in result

    def test_removes_control_chars(self):
        result = clean_metadata_field('hello\x00world')
        assert '\x00' not in result

    def test_strips_whitespace(self):
        result = clean_metadata_field('  hello  ')
        assert result == 'hello'

    def test_empty_string(self):
        assert clean_metadata_field('') == ''


class TestNormalizeBlockText:
    def test_basic(self):
        result = normalize_block_text('  Hello \u2014 world  ')
        assert 'Hello' in result

    def test_empty_ok_false_with_content(self):
        result = normalize_block_text('hello', is_empty_ok=False)
        assert result == 'hello'

    def test_not_empty_ok_returns_original_on_empty_strip(self):
        result = normalize_block_text('   ', is_empty_ok=False)
        assert result == '   '

    def test_none_input(self):
        assert normalize_block_text(None) == ''

    def test_simple_passthrough(self):
        assert normalize_block_text('Hello world.') == 'Hello world.'


class TestNormalizeTableCellText:
    def test_collapses_newlines(self):
        result = normalize_table_cell_text('hello\nworld')
        assert result == 'hello world'

    def test_collapses_carriage_returns(self):
        result = normalize_table_cell_text('hello\r\nworld\rfoo')
        assert ' ' in result

    def test_trims_edges(self):
        result = normalize_table_cell_text('  hello  ')
        assert result == 'hello'

    def test_empty_string(self):
        assert normalize_table_cell_text('') == ''

    def test_none_input(self):
        assert normalize_table_cell_text(None) == ''
