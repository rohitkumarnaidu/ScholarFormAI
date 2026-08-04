
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for ReferenceFormatter — coverage booster for citeproc-enabled paths.

Covers:
- _reference_to_csl_json (all fields + edge cases)
- _format_with_citeproc (all branches: no CSL, style failure, success, empty results)
- _get_or_load_style (cache hit, cache miss, load failure)
- format_reference with CITEPROC_AVAILABLE=True (success, fallback, exception)
- _resolve_csl_path with valid file detection
- _reference_type_to_csl ALL enum values
- _parse_author_name edge cases (multi-word, von names, whitespace)
"""

import sys
from unittest.mock import patch, MagicMock
import pytest

# ── Module-level citeproc-py mock ──────────────────────────────────────────
# Build a complete mock citeproc-py module tree so that
# reference_formatter's try/except ImportError block succeeds and
# CITEPROC_AVAILABLE = True.
_citeproc_source = MagicMock()
_citeproc_source.json = MagicMock()
_citeproc_source.json.CiteProcJSON = MagicMock()

_citeproc = MagicMock()
_citeproc.CitationStylesStyle = MagicMock()
_citeproc.CitationStylesBibliography = MagicMock()
_citeproc.formatter = MagicMock()
_citeproc.Citation = MagicMock()
_citeproc.CitationItem = MagicMock()
_citeproc.source = _citeproc_source

_citeproc_source.BibliographySource = MagicMock()

sys.modules["citeproc"] = _citeproc
sys.modules["citeproc.source"] = _citeproc_source
sys.modules["citeproc.source.json"] = _citeproc_source.json

# Also force the module-level flag (no-op if already set by the try block)
patch("app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE", True).start()

from app.pipeline.formatting.reference_formatter import (  # noqa: E402
    _resolve_csl_path,
    _parse_author_name,
    _reference_type_to_csl,
    _reference_to_csl_json,
)


# ======================================================================
#  _reference_to_csl_json tests  (lines 90–147)
# ======================================================================
class TestReferenceToCslJson:
    """Every field branch in _reference_to_csl_json."""

    @staticmethod
    def _ref(**kw) -> Reference:

        defaults = dict(reference_id="r1", citation_key="k", raw_text="t", index=0)
        defaults.update(kw)
        return Reference(**defaults)

    def test_all_fields(self):
        ref = self._ref(
            authors=["Smith, J.", "Doe, A."],
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            title="Full Title",
            journal="Test Jrnl",
            publisher="TestPub",
            year=2023,
            volume="10",
            issue="2",
            pages="123-145",
            doi="10.1234/abc",
            isbn="978-0-12-345678-9",
            issn="1234-5678",
            url="https://example.org",
            edition="3rd",
            note="See also ...")
        result = _reference_to_csl_json(ref)

        assert result["id"] == "r1"
        assert result["type"] == "article-journal"
        assert result["author"] == [
            {"family": "Smith", "given": "J."},
            {"family": "Doe", "given": "A."},
        ]
        assert result["title"] == "Full Title"
        assert result["container-title"] == "Test Jrnl"
        assert result["publisher"] == "TestPub"
        assert result["issued"] == {"date-parts": [[2023]]}
        assert result["volume"] == "10"
        assert result["issue"] == "2"
        assert result["page"] == "123-145"
        assert result["DOI"] == "10.1234/abc"
        assert result["ISBN"] == "978-0-12-345678-9"
        assert result["ISSN"] == "1234-5678"
        assert result["URL"] == "https://example.org"
        assert result["edition"] == "3rd"
        assert result["note"] == "See also ..."

    def test_minimal(self):
        """Only required fields → only id and type."""
        ref = self._ref()
        result = _reference_to_csl_json(ref)
        assert result == {"id": "r1", "type": "article"}

    def test_container_conference(self):
        """journal=None → use conference as container-title."""
        ref = self._ref(conference="Conf 2024")
        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "Conf 2024"

    def test_container_book_title(self):
        """journal & conference None → use book_title."""
        ref = self._ref(book_title="The Book")
        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "The Book"

    def test_container_precedence_journal_over_conference(self):
        """journal takes priority over conference and book_title."""
        ref = self._ref(
            journal="The Jrnl",
            conference="The Conf",
            book_title="The Book")
        result = _reference_to_csl_json(ref)
        assert result["container-title"] == "The Jrnl"

    def test_no_authors(self):
        """Empty authors list → no 'author' key emitted."""
        ref = self._ref(authors=[])
        result = _reference_to_csl_json(ref)
        assert "author" not in result

    def test_no_year(self):
        """year=None → no 'issued' key."""
        ref = self._ref(year=None)
        result = _reference_to_csl_json(ref)
        assert "issued" not in result

    def test_no_identifiers(self):
        """All identifiers None → no DOI/ISBN/ISSN/URL keys."""
        ref = self._ref(doi=None, isbn=None, issn=None, url=None)
        result = _reference_to_csl_json(ref)
        for key in ("DOI", "ISBN", "ISSN", "URL"):
            assert key not in result


# ======================================================================
#  _format_with_citeproc tests  (lines 211–244)
# ======================================================================
class TestFormatWithCiteproc:
    """Every branch of _format_with_citeproc."""

    @pytest.fixture
    def fmt(self):
        return ReferenceFormatter(MagicMock())

    @staticmethod
    def _ref(**kw) -> Reference:
        defaults = dict(reference_id="r1", citation_key="k", raw_text="t", index=0)
        defaults.update(kw)
        return Reference(**defaults)

    def test_no_csl_path_returns_none(self, fmt):
        """_resolve_csl_path returns None → return None immediately."""
        with patch(
            "app.pipeline.formatting.reference_formatter._resolve_csl_path",
            return_value=None,
        ):
            result = fmt._format_with_citeproc(self._ref(), "ieee")
        assert result is None

    def test_style_none_returns_none(self, fmt):
        """_get_or_load_style returns None → return None."""
        with patch(
            "app.pipeline.formatting.reference_formatter._resolve_csl_path",
            return_value="/fake/styles.csl",
        ):
            fmt._style_cache["/fake/styles.csl"] = None
            result = fmt._format_with_citeproc(self._ref(), "ieee")
        assert result is None

    @patch("app.pipeline.formatting.reference_formatter.CitationItem")
    @patch("app.pipeline.formatting.reference_formatter.Citation")
    @patch("app.pipeline.formatting.reference_formatter.CitationStylesBibliography")
    @patch("app.pipeline.formatting.reference_formatter.CiteProcJSON")
    @patch("app.pipeline.formatting.reference_formatter._resolve_csl_path")
    def test_success_path(self, m_resolve, m_cpj, m_csb, m_cit, m_ci, fmt):
        """Full success: style cached → citeproc pipeline → formatted string."""
        m_resolve.return_value = "/fake/styles.csl"
        mock_style = MagicMock()
        fmt._style_cache["/fake/styles.csl"] = mock_style

        mock_bib = MagicMock()
        mock_bib.bibliography.return_value = ["  Formatted output.  "]
        m_csb.return_value = mock_bib
        m_cpj.return_value = MagicMock()
        m_cit.return_value = MagicMock()
        m_ci.return_value = MagicMock()

        result = fmt._format_with_citeproc(self._ref(), "ieee")

        assert result == "Formatted output."
        mock_bib.register.assert_called_once()

    @patch("app.pipeline.formatting.reference_formatter.CitationItem")
    @patch("app.pipeline.formatting.reference_formatter.Citation")
    @patch("app.pipeline.formatting.reference_formatter.CitationStylesBibliography")
    @patch("app.pipeline.formatting.reference_formatter.CiteProcJSON")
    @patch("app.pipeline.formatting.reference_formatter._resolve_csl_path")
    def test_empty_bib_entries_returns_none(
        self, m_resolve, m_cpj, m_csb, m_cit, m_ci, fmt
    ):
        """bibliography() returns [] → return None."""
        m_resolve.return_value = "/fake/styles.csl"
        mock_style = MagicMock()
        fmt._style_cache["/fake/styles.csl"] = mock_style

        mock_bib = MagicMock()
        mock_bib.bibliography.return_value = []
        m_csb.return_value = mock_bib
        m_cpj.return_value = MagicMock()
        m_cit.return_value = MagicMock()
        m_ci.return_value = MagicMock()

        result = fmt._format_with_citeproc(self._ref(), "ieee")
        assert result is None

    @patch("app.pipeline.formatting.reference_formatter.CitationItem")
    @patch("app.pipeline.formatting.reference_formatter.Citation")
    @patch("app.pipeline.formatting.reference_formatter.CitationStylesBibliography")
    @patch("app.pipeline.formatting.reference_formatter.CiteProcJSON")
    @patch("app.pipeline.formatting.reference_formatter._resolve_csl_path")
    def test_empty_rendered_string_returns_none(
        self, m_resolve, m_cpj, m_csb, m_cit, m_ci, fmt
    ):
        """bib_entries[0] is blank after strip → return None."""
        m_resolve.return_value = "/fake/styles.csl"
        mock_style = MagicMock()
        fmt._style_cache["/fake/styles.csl"] = mock_style

        mock_bib = MagicMock()
        mock_bib.bibliography.return_value = ["   "]
        m_csb.return_value = mock_bib
        m_cpj.return_value = MagicMock()
        m_cit.return_value = MagicMock()
        m_ci.return_value = MagicMock()

        result = fmt._format_with_citeproc(self._ref(), "ieee")
        assert result is None


# ======================================================================
#  _get_or_load_style tests  (lines 246–259)
# ======================================================================
class TestGetOrLoadStyle:
    """Caching and failure modes of _get_or_load_style."""

    @pytest.fixture
    def fmt(self):
        return ReferenceFormatter(MagicMock())

    def test_cache_hit_returns_cached(self, fmt):
        """Existing entry in _style_cache → returned immediately."""
        mock_style = MagicMock()
        fmt._style_cache["/path/s.csl"] = mock_style
        assert fmt._get_or_load_style("/path/s.csl") is mock_style

    @patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle")
    def test_cache_miss_loads_and_caches(self, m_css, fmt):
        """First call loads style and stores in cache."""
        mock_style = MagicMock()
        m_css.return_value = mock_style
        result = fmt._get_or_load_style("/path/s.csl")
        assert result is mock_style
        assert fmt._style_cache["/path/s.csl"] is mock_style
        m_css.assert_called_once_with("/path/s.csl", validate=False)

    @patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle")
    def test_load_failure_caches_none(self, m_css, fmt):
        """Exception during load → cached as None, returns None."""
        m_css.side_effect = RuntimeError("corrupt CSL")
        result = fmt._get_or_load_style("/path/s.csl")
        assert result is None
        assert fmt._style_cache["/path/s.csl"] is None

    @patch("app.pipeline.formatting.reference_formatter.logger")
    @patch("app.pipeline.formatting.reference_formatter.CitationStylesStyle")
    def test_load_failure_logs_error(self, m_css, m_logger, fmt):
        """Exception during load → error logged."""
        m_css.side_effect = RuntimeError("parse error")
        fmt._get_or_load_style("/path/s.csl")
        m_logger.error.assert_called_once()
        assert "Failed to load CSL style" in str(m_logger.error.call_args)


# ======================================================================
#  format_reference with CITEPROC_AVAILABLE=True  (lines 181–192)
# ======================================================================
class TestReferenceFormatterCiteproc:
    """format_reference citeproc path: success, fallback, exception."""

    @pytest.fixture
    def fmt(self):
        return ReferenceFormatter(MagicMock())

    @staticmethod
    def _ref(**kw) -> Reference:
        defaults = dict(reference_id="r1", citation_key="k", raw_text="t", index=0)
        defaults.update(kw)
        return Reference(**defaults)

    def test_citeproc_success_returns_citeproc_result(self, fmt):
        """_format_with_citeproc returns string → returned as-is."""
        with patch.object(
            fmt, "_format_with_citeproc", return_value="Citeproc OK"
        ) as m_cp, patch.object(fmt, "_format_legacy") as m_legacy:
            ref = self._ref()
            result = fmt.format_reference(ref, "ieee")

        assert result == "Citeproc OK"
        m_cp.assert_called_once_with(ref, "ieee")
        m_legacy.assert_not_called()

    def test_citeproc_none_falls_back_to_legacy(self, fmt):
        """_format_with_citeproc returns None → falls to _format_legacy."""
        with patch.object(
            fmt, "_format_with_citeproc", return_value=None
        ) as m_cp, patch.object(
            fmt, "_format_legacy", return_value="Legacy OK"
        ) as m_legacy:
            ref = self._ref()
            result = fmt.format_reference(ref, "ieee")

        assert result == "Legacy OK"
        m_cp.assert_called_once_with(ref, "ieee")
        m_legacy.assert_called_once_with(ref, "ieee")

    def test_citeproc_exception_falls_back_to_legacy(self, fmt):
        """_format_with_citeproc raises → caught, logs, falls to legacy."""
        with patch.object(
            fmt, "_format_with_citeproc", side_effect=ValueError("boom")
        ) as m_cp, patch.object(
            fmt, "_format_legacy", return_value="Legacy OK"
        ) as m_legacy:
            ref = self._ref()
            result = fmt.format_reference(ref, "ieee")

        assert result == "Legacy OK"
        m_cp.assert_called_once_with(ref, "ieee")
        m_legacy.assert_called_once_with(ref, "ieee")

    def test_citeproc_flag_false_skips_citeproc(self, fmt):
        """CITEPROC_AVAILABLE=False → direct to legacy, no citeproc call."""
        with patch(
            "app.pipeline.formatting.reference_formatter.CITEPROC_AVAILABLE",
            False,
        ), patch.object(fmt, "_format_with_citeproc") as m_cp, patch.object(
            fmt, "_format_legacy", return_value="Legacy OK"
        ) as m_legacy:
            ref = self._ref()
            result = fmt.format_reference(ref, "ieee")

        assert result == "Legacy OK"
        m_cp.assert_not_called()
        m_legacy.assert_called_once_with(ref, "ieee")

    def test_format_references_calls_format_reference_each(self, fmt):
        """format_references delegates to format_reference per item."""
        refs = [
        ]
        with patch.object(
            fmt,
            "format_reference",
            side_effect=lambda r, p: f"formatted-{r.reference_id}",
        ):
            results = fmt.format_references(refs, "ieee")

        assert results == ["formatted-r1", "formatted-r2"]


# ======================================================================
#  _resolve_csl_path edge with valid file  (lines 44–52)
# ======================================================================
class TestResolveCslPathFile:
    """_resolve_csl_path when a CSL file actually exists."""

    @patch("app.pipeline.formatting.reference_formatter.os.path.isfile")
    def test_valid_publisher_found(self, m_isfile):
        """Publisher that maps to an existing styles.csl → path returned."""
        m_isfile.return_value = True
        path = _resolve_csl_path("ieee")
        assert path is not None
        assert path.endswith("styles.csl")
        m_isfile.assert_called_once()

    @patch("app.pipeline.formatting.reference_formatter.os.path.isfile")
    def test_valid_publisher_not_found(self, m_isfile):
        """Publisher whose styles.csl does not exist → None."""
        m_isfile.return_value = False
        path = _resolve_csl_path("ieee")
        assert path is None

    @patch("app.pipeline.formatting.reference_formatter.os.path.isfile")
    def test_whitespace_and_case_normalized(self, m_isfile):
        """Leading/trailing whitespace and uppercase are normalized."""
        m_isfile.return_value = True
        path = _resolve_csl_path("  IEEE  ")
        assert path is not None
        assert "ieee" in path and "IEEE" not in path


# ======================================================================
#  _reference_type_to_csl — all enum values  (lines 55–68)
# ======================================================================
class TestReferenceTypeToCslAll:
    """Map every ReferenceType value to the expected CSL type string."""

    @pytest.mark.parametrize("ref_type,expected", [
        (ReferenceType.JOURNAL_ARTICLE, "article-journal"),
        (ReferenceType.CONFERENCE_PAPER, "paper-conference"),
        (ReferenceType.BOOK, "book"),
        (ReferenceType.BOOK_CHAPTER, "chapter"),
        (ReferenceType.THESIS, "thesis"),
        (ReferenceType.TECHNICAL_REPORT, "report"),
        (ReferenceType.PATENT, "patent"),
        (ReferenceType.WEB_PAGE, "webpage"),
        (ReferenceType.PREPRINT, "article"),
        (ReferenceType.UNKNOWN, "article"),
    ])
    def test_mapping(self, ref_type, expected):
        ref = Reference(
            reference_id="r1",
            citation_key="k",
            raw_text="t",
            index=0,
            reference_type=ref_type)
        assert _reference_type_to_csl(ref) == expected


# ======================================================================
#  _parse_author_name advanced edge cases  (lines 80–87)
# ======================================================================
class TestParseAuthorNameAdvanced:
    """Edge cases in _parse_author_name — especially the rsplit else branch."""

    def test_multi_word_no_comma(self):
        """'Jane Anne Doe' → rsplit splits on last space."""
        r = _parse_author_name("Jane Anne Doe")
        assert r == {"given": "Jane Anne", "family": "Doe"}

    def test_multi_word_with_comma(self):
        """'Doe, Jane Anne' → comma split preserves multi-word family."""
        r = _parse_author_name("Doe, Jane Anne")
        assert r == {"family": "Doe", "given": "Jane Anne"}

    def test_middle_initial_no_comma(self):
        """'John M. Doe' → rsplit, given includes initial."""
        r = _parse_author_name("John M. Doe")
        assert r == {"given": "John M.", "family": "Doe"}

    def test_von_surname_with_comma(self):
        """'von Neumann, John' → comma branch, family='von Neumann'."""
        r = _parse_author_name("von Neumann, John")
        assert r == {"family": "von Neumann", "given": "John"}

    def test_comma_no_given(self):
        """'Doe,' → family='Doe', given=''."""
        r = _parse_author_name("Doe,")
        assert r == {"family": "Doe", "given": ""}

    def test_single_word_no_given(self):
        """'Aristotle' → only family key, no 'given'."""
        r = _parse_author_name("Aristotle")
        assert r == {"family": "Aristotle"}

    def test_empty_returns_unknown(self):
        """Empty string after strip → family='Unknown'."""
        r = _parse_author_name("")
        assert r == {"family": "Unknown"}

    def test_only_spaces_returns_unknown(self):
        """Whitespace-only → family='Unknown'."""
        r = _parse_author_name("   ")
        assert r == {"family": "Unknown"}
