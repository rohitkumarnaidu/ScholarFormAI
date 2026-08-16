from unittest.mock import MagicMock, patch


class TestResolveCslPath:
    def test_empty_publisher(self):
        from app.pipeline.formatting.reference_formatter import _resolve_csl_path

        assert _resolve_csl_path(None) is None
        assert _resolve_csl_path("") is None

    def test_file_exists(self, tmp_path):
        from app.pipeline.formatting.reference_formatter import _resolve_csl_path

        csl_dir = tmp_path / "ieee"
        csl_dir.mkdir(parents=True)
        csl_file = csl_dir / "styles.csl"
        csl_file.write_text("dummy")

        with patch("app.pipeline.formatting.reference_formatter._TEMPLATES_DIR", str(tmp_path)):
            result = _resolve_csl_path("IEEE")
            assert result is not None
            assert result.endswith("styles.csl")

    def test_file_not_found(self, tmp_path):
        from app.pipeline.formatting.reference_formatter import _resolve_csl_path

        with patch("app.pipeline.formatting.reference_formatter._TEMPLATES_DIR", str(tmp_path)):
            assert _resolve_csl_path("nonexistent") is None


class TestReferenceTypeToCsl:
    def test_known_types(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl

        ref = MagicMock()
        for our_type, csl_type in [
            ("journal_article", "article-journal"),
            ("conference_paper", "paper-conference"),
            ("book", "book"),
            ("book_chapter", "chapter"),
            ("thesis", "thesis"),
            ("technical_report", "report"),
            ("patent", "patent"),
            ("web_page", "webpage"),
            ("preprint", "article"),
        ]:
            ref.reference_type = our_type
            assert _reference_type_to_csl(ref) == csl_type

    def test_unknown_type_defaults_to_article(self):
        from app.pipeline.formatting.reference_formatter import _reference_type_to_csl

        ref = MagicMock()
        ref.reference_type = "unknown_type"
        assert _reference_type_to_csl(ref) == "article"


class TestParseAuthorName:
    def test_last_first_with_comma(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name

        result = _parse_author_name("Smith, J.")
        assert result["family"] == "Smith"
        assert result["given"] == "J."

    def test_first_last_without_comma(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name

        result = _parse_author_name("Jane Doe")
        assert result["given"] == "Jane"
        assert result["family"] == "Doe"

    def test_single_name(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name

        result = _parse_author_name("Plato")
        assert result["family"] == "Plato"
        assert "given" not in result

    def test_empty_name(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name

        result = _parse_author_name("")
        assert result["family"] == "Unknown"

    def test_whitespace_stripped(self):
        from app.pipeline.formatting.reference_formatter import _parse_author_name

        result = _parse_author_name("  Smith, J.  ")
        assert result["family"] == "Smith"


class TestReferenceToCslJson:
    def test_minimal_ref(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json

        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.reference_type = "journal_article"
        ref.authors = []
        ref.title = None
        ref.journal = None
        ref.conference = None
        ref.book_title = None
        ref.publisher = None
        ref.year = None
        ref.volume = None
        ref.issue = None
        ref.pages = None
        ref.doi = None
        ref.isbn = None
        ref.issn = None
        ref.url = None
        ref.edition = None
        ref.note = None

        result = _reference_to_csl_json(ref)
        assert result["id"] == "ref1"
        assert result["type"] == "article-journal"

    def test_full_ref(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json

        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.reference_type = "book"
        ref.authors = ["Smith, J.", "Doe, J."]
        ref.title = "Test Book"
        ref.journal = None
        ref.conference = None
        ref.book_title = None
        ref.publisher = "Academic Press"
        ref.year = 2024
        ref.volume = "Vol. 1"
        ref.issue = "No. 2"
        ref.pages = "100-200"
        ref.doi = "10.1234/test"
        ref.isbn = "978-1-234-567"
        ref.issn = None
        ref.url = "https://example.com"
        ref.edition = "2nd"
        ref.note = "Important work"

        result = _reference_to_csl_json(ref)
        assert result["author"] == [{"family": "Smith", "given": "J."}, {"family": "Doe", "given": "J."}]
        assert result["title"] == "Test Book"
        assert result["publisher"] == "Academic Press"
        assert result["issued"] == {"date-parts": [[2024]]}
        assert result["DOI"] == "10.1234/test"

    def test_container_prefers_journal(self):
        from app.pipeline.formatting.reference_formatter import _reference_to_csl_json

        ref = MagicMock()
        ref.journal = "Journal of Testing"
        ref.conference = "Test Conf"
        ref.book_title = "Test Book"
        ref.reference_id = "r1"
        ref.reference_type = "journal_article"
        ref.authors = []
        ref.title = None
        ref.publisher = None
        ref.year = None
        ref.volume = None
        ref.issue = None
        ref.pages = None
        ref.doi = None
        ref.isbn = None
        ref.issn = None
        ref.url = None
        ref.edition = None
        ref.note = None

        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "Journal of Testing"


class FakeCiteProc:
    """Mock citeproc-py classes."""

    class CitationStylesStyle:
        def __init__(self, path, validate=False):
            pass

    class CitationStylesBibliography:
        def __init__(self, style, source, fmt):
            self._style = style

        def register(self, citation):
            pass

        def bibliography(self):
            return ["Formatted. (2024). Test Article. Journal, 1(2), 100."]

    class formatter:
        plain = "plain"

    class Citation:
        def __init__(self, items):
            self.items = items

    class CitationItem:
        def __init__(self, ref_id):
            self.ref_id = ref_id

    class CiteProcJSON:
        def __init__(self, data):
            self.data = data

    class BibliographySource:
        pass


class TestFormatReference:
    def test_legacy_ieee(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "IEEE"}}

        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.reference_type = "journal_article"
        ref.title = "Test Article"
        ref.authors = ["Smith, J."]
        ref.journal = "Journal"
        ref.year = 2024
        ref.number = 1
        ref.volume = "1"
        ref.issue = "2"
        ref.pages = "100-200"
        ref.doi = "10.1234/test"
        ref.isbn = None
        ref.issn = None
        ref.url = None
        ref.edition = None
        ref.note = None
        ref.conference = None
        ref.book_title = None
        ref.publisher = None
        ref.raw_text = "Raw ref text"
        ref.get_author_list.return_value = "J. Smith"

        with patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", False):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "ieee")
        assert "Smith" in result
        assert "Test Article" in result

    def test_legacy_none_style(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "none"}}

        ref = MagicMock()
        ref.reference_id = "ref2"
        ref.raw_text = "  Raw   reference   text  "
        ref.title = None
        ref.authors = []
        ref.journal = None
        ref.conference = None
        ref.book_title = None
        ref.publisher = None
        ref.year = None
        ref.volume = None
        ref.issue = None
        ref.pages = None
        ref.doi = None
        ref.isbn = None
        ref.issn = None
        ref.url = None
        ref.edition = None
        ref.note = None
        ref.number = 2

        with patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", False):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "none")
        assert result == "Raw reference text"

    def test_legacy_default_to_raw(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "other"}}

        ref = MagicMock()
        ref.raw_text = "Raw reference text"
        ref.number = 3

        with patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", False):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "other")
        assert result == "Raw reference text"

    def test_citeproc_path(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "IEEE"}}

        ref = MagicMock()
        ref.reference_id = "ref4"
        ref.reference_type = "journal_article"
        ref.title = "Test"
        ref.authors = ["Smith, J."]
        ref.journal = "Journal"
        ref.year = 2024
        ref.number = 4
        ref.volume = None
        ref.issue = None
        ref.pages = None
        ref.doi = None
        ref.isbn = None
        ref.issn = None
        ref.url = None
        ref.edition = None
        ref.note = None
        ref.conference = None
        ref.book_title = None
        ref.publisher = None
        ref.raw_text = "fallback"
        ref.get_author_list.return_value = "J. Smith"

        with (
            patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True),
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value="/tmp/styles.csl"),
            patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle", FakeCiteProc.CitationStylesStyle),
            patch(
                "app.pipeline.formatting.reference_formatter.CitationStylesBibliography",
                FakeCiteProc.CitationStylesBibliography,
            ),
            patch("app.pipeline.formatting.reference_formatter.formatter", FakeCiteProc.formatter),
            patch("app.pipeline.formatting.reference_formatter.Citation", FakeCiteProc.Citation),
            patch("app.pipeline.formatting.reference_formatter.CitationItem", FakeCiteProc.CitationItem),
            patch("app.pipeline.formatting.reference_formatter.CiteProcJSON", FakeCiteProc.CiteProcJSON),
        ):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "ieee")
        assert "Formatted" in result

    def test_citeproc_no_csl_falls_back(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "IEEE"}}

        ref = MagicMock()
        ref.reference_id = "ref5"
        ref.title = None
        ref.journal = None
        ref.year = None
        ref.raw_text = "fallback result"
        ref.number = 5
        ref.get_author_list.return_value = "Author"

        with (
            patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True),
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value=None),
        ):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "ieee")
        assert "Untitled" in result

    def test_citeproc_exception_falls_back(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "IEEE"}}

        ref = MagicMock()
        ref.reference_id = "ref6"
        ref.title = None
        ref.journal = None
        ref.conference = None
        ref.book_title = None
        ref.year = None
        ref.number = 6
        ref.get_author_list.return_value = "Author"

        with (
            patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True),
            patch("app.pipeline.formatting.reference_formatter._resolve_csl_path", return_value="/tmp/s.csl"),
            patch(
                "app.pipeline.formatting.reference_formatter.CitationStylesStyle", side_effect=Exception("bad style")
            ),
        ):
            formatter = ReferenceFormatter(loader)
            result = formatter.format_reference(ref, "ieee")
        assert "Untitled" in result

    def test_format_references_list(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()
        loader.load.return_value = {"references": {"style": "IEEE"}}

        ref1 = MagicMock()
        ref1.reference_id = "r1"
        ref1.title = "Paper 1"
        ref1.authors = ["A"]
        ref1.journal = "J"
        ref1.year = 2024
        ref1.number = 1
        ref1.raw_text = "raw1"
        ref1.get_author_list.return_value = "A."

        ref2 = MagicMock()
        ref2.reference_id = "r2"
        ref2.title = "Paper 2"
        ref2.authors = ["B"]
        ref2.journal = "J"
        ref2.year = 2023
        ref2.number = 2
        ref2.raw_text = "raw2"
        ref2.get_author_list.return_value = "B."

        with patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", False):
            formatter = ReferenceFormatter(loader)
            results = formatter.format_references([ref1, ref2], "ieee")
        assert len(results) == 2

    def test_style_cache_hit(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()

        formatter = ReferenceFormatter(loader)
        formatter._style_cache["/tmp/s.csl"] = "cached"
        style = formatter._get_or_load_style("/tmp/s.csl")
        assert style == "cached"

    def test_style_cache_miss_and_fail(self):
        from app.pipeline.formatting.reference_formatter import ReferenceFormatter

        loader = MagicMock()

        with patch(
            "app.pipeline.formatting.reference_formatter.CitationStylesStyle", side_effect=Exception("load error")
        ):
            formatter = ReferenceFormatter(loader)
            style = formatter._get_or_load_style("/tmp/bad.csl")
            assert style is None
            assert formatter._style_cache["/tmp/bad.csl"] is None
