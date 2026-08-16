class TestCleanAuthorName:
    def test_removes_surrounding_quotes(self):
        from app.pipeline.references.normalizer import clean_author_name

        assert clean_author_name('"Smith, J."') == "Smith, J."

    def test_strips_whitespace(self):
        from app.pipeline.references.normalizer import clean_author_name

        assert clean_author_name("  Smith, J.  ") == "Smith, J."

    def test_passes_clean_name(self):
        from app.pipeline.references.normalizer import clean_author_name

        assert clean_author_name("Smith, J.") == "Smith, J."


class TestCleanTitle:
    def test_removes_double_quotes(self):
        from app.pipeline.references.normalizer import clean_title

        assert clean_title('"A Great Paper"') == "A Great Paper"

    def test_removes_curly_quotes(self):
        from app.pipeline.references.normalizer import clean_title

        assert clean_title("\u201cA Great Paper\u201d") == "A Great Paper"

    def test_removes_trailing_punctuation(self):
        from app.pipeline.references.normalizer import clean_title

        assert clean_title("Title.") == "Title"

    def test_handles_empty(self):
        from app.pipeline.references.normalizer import clean_title

        assert clean_title("") == ""


class TestNormalizePageRange:
    def test_removes_pp_prefix(self):
        from app.pipeline.references.normalizer import normalize_page_range

        assert normalize_page_range("pp. 123-145") == "123-145"

    def test_removes_p_prefix(self):
        from app.pipeline.references.normalizer import normalize_page_range

        assert normalize_page_range("p. 42") == "42"

    def test_passes_bare_range(self):
        from app.pipeline.references.normalizer import normalize_page_range

        assert normalize_page_range("123-145") == "123-145"

    def test_returns_empty_for_none(self):
        from app.pipeline.references.normalizer import normalize_page_range

        assert normalize_page_range("") == ""
