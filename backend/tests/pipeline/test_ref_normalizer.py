# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from app.pipeline.references.normalizer import (
    clean_author_name,
    clean_title,
    normalize_page_range,
)


class TestCleanAuthorName:
    def test_strips_whitespace(self):
        assert clean_author_name('  Smith, J.  ') == 'Smith, J.'

    def test_removes_surrounding_quotes(self):
        assert clean_author_name('"Smith, J."') == 'Smith, J.'

    def test_removes_surrounding_single_quotes(self):
        assert clean_author_name("'Smith, J.'") == 'Smith, J.'

    def test_empty_string(self):
        assert clean_author_name('') == ''

    def test_already_clean(self):
        assert clean_author_name('J. Smith') == 'J. Smith'


class TestCleanTitle:
    def test_removes_double_quotes(self):
        assert clean_title('"A Paper Title"') == 'A Paper Title'

    def test_removes_single_quotes(self):
        assert clean_title("'A Paper Title'") == 'A Paper Title'

    def test_removes_curly_quotes(self):
        assert clean_title('\u201cA Paper Title\u201d') == 'A Paper Title'

    def test_strips_trailing_punctuation(self):
        assert clean_title('Title,') == 'Title'

    def test_strips_trailing_period(self):
        assert clean_title('Title.') == 'Title'

    def test_no_change_needed(self):
        assert clean_title('A Paper Title') == 'A Paper Title'

    def test_empty_string(self):
        assert clean_title('') == ''


class TestNormalizePageRange:
    def test_strips_pp_prefix(self):
        assert normalize_page_range('pp. 123-145') == '123-145'

    def test_strips_p_prefix(self):
        assert normalize_page_range('p. 123') == '123'

    def test_already_clean(self):
        assert normalize_page_range('123-145') == '123-145'

    def test_empty_string(self):
        assert normalize_page_range('') == ''

    def test_none_input(self):
        assert normalize_page_range(None) == ''

    def test_case_insensitive(self):
        assert normalize_page_range('PP. 12-34') == '12-34'
