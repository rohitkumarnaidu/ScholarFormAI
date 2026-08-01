# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.pipeline.references.csl.apafallback import APA7Formatter

pytestmark = [pytest.mark.pipeline]


class TestAPA7FormatterAuthorFormatting:
    """Test APA 7 author formatting rules."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_one_author(self):
        result = self.fmt._format_authors(["Smith, John"])
        assert "Smith" in result

    def test_two_authors(self):
        result = self.fmt._format_authors(["Smith, John", "Doe, Jane"])
        assert "&" in result
        assert "Smith" in result
        assert "Doe" in result

    def test_three_authors(self):
        authors = ["Smith, John", "Doe, Jane", "Lee, Bob"]
        result = self.fmt._format_authors(authors)
        assert "&" in result
        assert "Smith" in result
        assert "Lee" in result

    def test_twenty_authors(self):
        authors = [f"Author{i}, First{i}" for i in range(20)]
        result = self.fmt._format_authors(authors)
        assert "&" in result

    def test_twenty_one_plus_authors(self):
        authors = [f"Author{i}, First{i}" for i in range(22)]
        result = self.fmt._format_authors(authors)
        assert "..." in result
        assert "Author0" in result
        assert "Author21" in result

    def test_no_authors(self):
        result = self.fmt._format_authors([])
        assert result == "Unknown"

    def test_single_author_name_conversion(self):
        result = self.fmt._format_single_author("Smith, John")
        assert result == "Smith, J."

    def test_single_author_initials(self):
        result = self.fmt._format_single_author("Smith, John M.")
        assert result == "Smith, J. M."

    def test_single_author_no_comma(self):
        result = self.fmt._format_single_author("John Smith")
        assert result == "Smith, J."


class TestAPA7FormatterIntextCitations:
    """Test APA 7 in-text citation formatting."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_parenthetical_one_author(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John"], year=2020
        )
        assert result == "(Smith, 2020)"

    def test_parenthetical_two_authors(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John", "Doe, Jane"], year=2020
        )
        assert result == "(Smith and Doe, 2020)"

    def test_parenthetical_three_authors(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John", "Doe, Jane", "Lee, Bob"], year=2020
        )
        assert result == "(Smith et al., 2020)"

    def test_parenthetical_with_page(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John"], year=2020, page="45"
        )
        assert result == "(Smith, 2020, p. 45)"

    def test_narrative_one_author(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John"], year=2020, narrative=True
        )
        assert result == "Smith (2020)"

    def test_narrative_with_page(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John"], year=2020, page="45", narrative=True
        )
        assert result == "Smith (2020, p. 45)"

    def test_no_year(self):
        result = self.fmt.format_intext_citation(
            ["Smith, John"]
        )
        assert "n.d." in result

    def test_no_authors(self):
        result = self.fmt.format_intext_citation([], year=2020)
        assert "Unknown" in result


class TestAPA7FormatterReferenceEntries:
    """Test APA 7 reference entry formatting."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_journal_article(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John", "Doe, Jane"],
            year=2020,
            title="A study on AI",
            journal="Journal of AI Research",
            volume="15",
            issue="3",
            pages="100-120",
            doi="10.1234/example",
        )
        assert "*Journal of AI Research*" in result
        assert "https://doi.org/" in result
        assert "Smith" in result
        assert "(2020)." in result

    def test_journal_article_no_doi(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="A study",
            journal="Journal of Research",
            volume="10",
            issue="2",
            pages="50-60",
        )
        assert "https://doi.org/" not in result
        assert "A study" in result

    def test_book(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="The Book Title",
            publisher="Oxford University Press",
            doi="10.1234/book",
            reference_type="book",
        )
        assert "Oxford University Press" in result
        assert "https://doi.org/" in result

    def test_book_with_edition(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="The Book",
            publisher="Oxford University Press",
            edition="3rd",
            reference_type="book",
        )
        assert "3rd ed." in result

    def test_book_chapter(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="Chapter Title",
            book_title="The Book",
            publisher="Oxford University Press",
            pages="30-50",
            reference_type="book_chapter",
        )
        assert "Chapter Title" in result
        assert "The Book" in result

    def test_conference_paper(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="Paper Title",
            conference="Conference on AI",
            doi="10.1234/conf",
            reference_type="conference_paper",
        )
        assert "Conference on AI" in result

    def test_thesis(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="Thesis Title",
            publisher="MIT",
            reference_type="thesis",
        )
        assert "Doctoral dissertation" in result
        assert "MIT" in result

    def test_web_page(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith, John"],
            year=2020,
            title="Web Page Title",
            publisher="Some Website",
            url="https://example.com/page",
            reference_type="web_page",
        )
        assert "Web Page Title" in result
        assert "https://example.com/page" in result

    def test_no_authors_ref_entry(self):
        result = self.fmt.format_reference_entry(
            authors=[],
            year=2020,
            title="Title",
        )
        assert "Unknown" in result


class TestAPA7FormatterDOI:
    """Test APA 7 DOI formatting."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_doi_hyperlink(self):
        result = self.fmt._format_doi("10.1234/example")
        assert result == "https://doi.org/10.1234/example"

    def test_doi_already_url(self):
        result = self.fmt._format_doi("https://doi.org/10.1234/example")
        assert result == "https://doi.org/10.1234/example"

    def test_doi_empty(self):
        result = self.fmt._format_doi(None)
        assert result == ""

    def test_doi_blank(self):
        result = self.fmt._format_doi("")
        assert result == ""


class TestAPA7FormatterSort:
    """Test APA 7 reference sorting."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_sort_by_surname(self):
        refs = [
            {"authors": ["Zebra, Alan"]},
            {"authors": ["Alpha, Bob"]},
        ]
        sorted_refs = self.fmt.sort_references(refs)
        assert sorted_refs[0]["authors"][0] == "Alpha, Bob"
        assert sorted_refs[1]["authors"][0] == "Zebra, Alan"

    def test_sort_empty(self):
        assert self.fmt.sort_references([]) == []


class TestAPA7FormatterSurnameExtraction:
    """Test surname extraction."""

    def setup_method(self):
        self.fmt = APA7Formatter()

    def test_comma_format(self):
        assert self.fmt._extract_surname("Smith, John") == "Smith"

    def test_van_der_waals(self):
        assert self.fmt._extract_surname("van der Waals, Johannes") == "van der Waals"

    def test_simple_name(self):
        assert self.fmt._extract_surname("Chomsky") == "Chomsky"

    def test_first_last(self):
        assert self.fmt._extract_surname("John Smith") == "Smith"

    def test_empty(self):
        assert self.fmt._extract_surname("") == "Unknown"
