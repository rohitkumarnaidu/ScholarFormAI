# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest

from app.pipeline.references.csl.vancouver_fallback import VancouverFormatter

pytestmark = [pytest.mark.pipeline]


class TestVancouverFormatterAuthorFormatting:
    """Test Vancouver author formatting rules."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_one_author(self):
        result = self.fmt._format_authors(["Smith J."])
        assert result == "Smith J."

    def test_two_authors(self):
        result = self.fmt._format_authors(["Smith J.", "Doe A."])
        assert result == "Smith J., Doe A."

    def test_six_authors(self):
        authors = [f"Author{i} F." for i in range(6)]
        result = self.fmt._format_authors(authors)
        assert "Author0" in result
        assert "Author5" in result
        assert "et al." not in result

    def test_seven_authors_et_al(self):
        authors = [f"Author{i} F." for i in range(7)]
        result = self.fmt._format_authors(authors)
        assert "Author0" in result
        assert "Author5" in result
        assert "et al." in result

    def test_no_authors(self):
        result = self.fmt._format_authors([])
        assert result == "Unknown"


class TestVancouverFormatterIntextCitations:
    """Test Vancouver in-text citation formatting."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_single_ref(self):
        result = self.fmt.format_intext_citation([1])
        assert result == "[1]"

    def test_multiple_refs(self):
        result = self.fmt.format_intext_citation([1, 3, 5])
        assert result == "[1,3,5]"

    def test_consecutive_range(self):
        result = self.fmt.format_intext_citation([1, 2, 3])
        assert result == "[1-3]"

    def test_mixed_ranges(self):
        result = self.fmt.format_intext_citation([1, 2, 3, 5, 7, 8, 9])
        assert result == "[1-3,5,7-9]"

    def test_single_range(self):
        result = self.fmt.format_intext_citation([2, 3, 4, 5])
        assert result == "[2-5]"

    def test_unsorted_input(self):
        result = self.fmt.format_intext_citation([5, 1, 3])
        assert result == "[1,3,5]"

    def test_empty(self):
        result = self.fmt.format_intext_citation([])
        assert result == ""


class TestVancouverFormatterReferenceEntries:
    """Test Vancouver reference entry formatting."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_journal_article(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J.", "Doe A."],
            title="A study on machine learning",
            journal="J Mach Learn Res",
            year=2020,
            volume="15",
            issue="3",
            pages="100-120",
            doi="10.1234/example",
        )
        assert "Smith" in result
        assert "A study" in result
        assert "J Mach Learn Res" in result
        assert "doi:" in result

    def test_journal_article_no_doi(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="A study",
            journal="J Res",
            year=2020,
            volume="10",
            pages="50-60",
        )
        assert "A study" in result
        assert "J Res" in result
        assert "doi:" not in result

    def test_book(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="The Book Title",
            publisher="Oxford University Press",
            year=2020,
            reference_type="book",
        )
        assert "Oxford University Press" in result
        assert "The Book Title" in result

    def test_book_with_edition(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="The Book",
            publisher="Oxford University Press",
            year=2020,
            edition="3rd",
            reference_type="book",
        )
        assert "3rd ed." in result

    def test_book_chapter(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="Chapter Title",
            book_title="The Book",
            publisher="Oxford University Press",
            pages="30-50",
            year=2020,
            reference_type="book_chapter",
        )
        assert "Chapter Title" in result
        assert "The Book" in result
        assert "p." in result

    def test_conference_paper(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="Paper Title",
            conference="Conf on AI 2020",
            year=2020,
            doi="10.1234/conf",
            reference_type="conference_paper",
        )
        assert "Paper Title" in result
        assert "Conf on AI" in result

    def test_thesis(self):
        result = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="Thesis Title",
            publisher="MIT",
            year=2020,
            reference_type="thesis",
        )
        assert "Thesis Title" in result
        assert "Dissertation" in result

    def test_no_authors_ref_entry(self):
        result = self.fmt.format_reference_entry(
            authors=[],
            title="Title",
            year=2020,
        )
        assert "Unknown" in result


class TestVancouverFormatterDOI:
    """Test Vancouver DOI formatting."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_doi_standard(self):
        result = self.fmt._format_doi("10.1234/example")
        assert "doi: 10.1234/example." in result

    def test_doi_as_url(self):
        result = self.fmt._format_doi("https://doi.org/10.1234/example")
        assert "doi: example." in result or "doi: 10.1234" in result

    def test_doi_empty(self):
        result = self.fmt._format_doi(None)
        assert result == ""


class TestVancouverFormatterSort:
    """Test Vancouver reference sorting."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_sort_by_index(self):
        refs = [
            {"authors": ["Zebra A."], "index": 3},
            {"authors": ["Alpha B."], "index": 1},
        ]
        sorted_refs = self.fmt.sort_references(refs)
        assert sorted_refs[0]["index"] == 1
        assert sorted_refs[1]["index"] == 3

    def test_empty_list(self):
        assert self.fmt.sort_references([]) == []

    def test_no_index_field(self):
        refs = [{"authors": ["A"]}, {"authors": ["B"]}]
        result = self.fmt.sort_references(refs)
        assert result == refs


class TestVancouverFormatterIntegration:
    """Integration tests for Vancouver formatter."""

    def setup_method(self):
        self.fmt = VancouverFormatter()

    def test_citation_then_entry(self):
        intext = self.fmt.format_intext_citation([1, 2])
        entry1 = self.fmt.format_reference_entry(
            authors=["Smith J."],
            title="First article",
            journal="J Med",
            year=2020,
            volume="5",
            pages="10-20",
        )
        entry2 = self.fmt.format_reference_entry(
            authors=["Doe A."],
            title="Second article",
            journal="J Sci",
            year=2021,
            volume="8",
            pages="30-40",
        )
        assert intext == "[1-2]"
        assert "Smith" in entry1
        assert "Doe" in entry2

    def test_seven_authors_et_al(self):
        authors = [
            "Smith J.",
            "Doe A.",
            "Lee B.",
            "Kim C.",
            "Chen D.",
            "Wang E.",
            "Liu F.",
        ]
        entry = self.fmt.format_reference_entry(
            authors=authors,
            title="Multi-author article",
            journal="J Big Data",
            year=2020,
        )
        assert "et al." in entry
