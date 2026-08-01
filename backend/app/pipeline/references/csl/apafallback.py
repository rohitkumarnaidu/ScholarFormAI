# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
APA 7th Edition citation fallback formatter.

Implements APA 7th edition citation formatting rules for in-text citations,
reference entries, and bibliography sorting. Used when citeproc-py is
unavailable or CSL file loading fails.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class APA7Formatter:
    """
    APA 7th Edition citation formatting.

    Rules implemented:
    - Author formatting: 1 author, 2 authors (&), 3-20 authors (comma-separated
      with & before last), 21+ authors (first 19, ..., last)
    - In-text citations: parenthetical (Author, Year) and narrative (Author, Year)
    - Reference entries: author, year, title, source, DOI as hyperlink
    - Hanging indent on reference entries
    - DOI formatted as https://doi.org/xxxx
    - Sorting: alphabetical by surname of first author
    """

    # Common name prefixes to handle in surname extraction
    _NAME_PREFIXES = {"van", "von", "de", "del", "der", "den", "la", "le", "du", "da", "di"}

    def __init__(self, hanging_indent: bool = True):
        self.hanging_indent = hanging_indent

    def format_intext_citation(
        self,
        authors: List[str],
        year: Optional[int] = None,
        page: Optional[str] = None,
        narrative: bool = False,
    ) -> str:
        """
        Format an APA 7th edition in-text citation.

        Args:
            authors: List of author name strings (e.g., ['Smith, J.', 'Doe, A.'])
            year: Publication year.
            page: Page number for direct quotes.
            narrative: If True, format as narrative citation (author as part of text).

        Returns:
            Formatted APA in-text citation string.
        """
        year_str = str(year) if year else "n.d."
        page_str = f", p. {page}" if page else ""

        # Build author portion
        author_str = self._format_intext_authors(authors)

        if narrative:
            if page:
                return f"{author_str} ({year_str}{page_str})"
            return f"{author_str} ({year_str})"
        else:
            if page:
                return f"({author_str}, {year_str}{page_str})"
            return f"({author_str}, {year_str})"

    def _format_intext_authors(self, authors: List[str]) -> str:
        """
        Format author list for in-text citation according to APA 7.

        - 1 author: Smith
        - 2 authors: Smith and Doe
        - 3+ authors: Smith et al.
        """
        if not authors:
            return "Unknown"

        surnames = [self._extract_surname(a) for a in authors]

        if len(authors) == 1:
            return surnames[0]

        if len(authors) == 2:
            return f"{surnames[0]} and {surnames[1]}"

        # 3+ authors: et al.
        return f"{surnames[0]} et al."

    def _extract_surname(self, author: str) -> str:
        """
        Extract surname from an author name string.

        Handles formats:
        - 'Smith, J.' -> 'Smith'
        - 'van der Waals, J.' -> 'van der Waals'
        - 'Smith' -> 'Smith'
        - 'John Smith' -> 'Smith'
        """
        name = author.strip()
        if not name:
            return "Unknown"

        if "," in name:
            parts = name.split(",")
            return parts[0].strip()

        parts = name.split()
        if len(parts) == 1:
            return parts[0]

        # Could be "John Smith" or "John von Neumann"
        # APA 7: surname is usually last part, but check for known prefixes
        candidate = parts[-1]
        if len(parts) > 2 and parts[-2].lower() in self._NAME_PREFIXES:
            return " ".join(parts[-2:])

        return candidate

    def format_reference_entry(
        self,
        authors: List[str],
        year: Optional[int] = None,
        title: Optional[str] = None,
        journal: Optional[str] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        publisher: Optional[str] = None,
        doi: Optional[str] = None,
        url: Optional[str] = None,
        book_title: Optional[str] = None,
        edition: Optional[str] = None,
        conference: Optional[str] = None,
        reference_type: str = "journal_article",
        hanging_indent: Optional[bool] = None,
    ) -> str:
        """
        Format a full reference entry per APA 7th edition.

        Reference types:
        - journal_article: Author. (Year). Title. Journal, Volume(Issue), Pages. DOI
        - book: Author. (Year). Title. Publisher. DOI
        - book_chapter: Author. (Year). Title. In Editor (Ed.), Book Title (pp.). Publisher. DOI
        - conference_paper: Author. (Year). Title. Conference. DOI
        - thesis: Author. (Year). Title (Type of thesis). Institution. DOI
        - web_page: Author. (Year). Title. Site Name. URL
        """
        use_hanging = hanging_indent if hanging_indent is not None else self.hanging_indent
        indent_str = "    " if use_hanging else ""

        author_str = self._format_authors(authors)
        year_str = f"({year})." if year else "(n.d.)."
        title_str = self._format_title(title or "Untitled")
        doi_str = self._format_doi(doi)

        if reference_type == "journal_article":
            venue = self._format_journal_article(journal, volume, issue, pages)
            entry = f"{indent_str}{author_str} {year_str} {title_str} {venue}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

        elif reference_type == "book":
            pub = f"{publisher}." if publisher else ""
            entry = f"{indent_str}{author_str} {year_str} {title_str}"
            if edition:
                entry = f"{entry} ({edition} ed.)."
            if pub:
                entry = f"{entry} {pub}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

        elif reference_type == "book_chapter":
            venue = f"In {book_title}." if book_title else ""
            if pages:
                venue = f"In {book_title} (pp. {pages})." if book_title else f"(pp. {pages})."
            elif book_title:
                venue = f"In {book_title}."
            pub = f"{publisher}." if publisher else ""
            entry = f"{indent_str}{author_str} {year_str} {title_str} {venue}"
            if pub:
                entry = f"{entry} {pub}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

        elif reference_type == "conference_paper":
            venue = f"{conference}." if conference else ""
            entry = f"{indent_str}{author_str} {year_str} {title_str}"
            if venue:
                entry = f"{entry} {venue}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

        elif reference_type == "thesis":
            entry = (
                f"{indent_str}{author_str} {year_str} {title_str} [Doctoral dissertation, {publisher or 'Unknown Institution'}]."
                if publisher
                else f"{indent_str}{author_str} {year_str} {title_str} [Doctoral dissertation]."
            )
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

        elif reference_type == "web_page":
            site = f"{publisher or 'Website'}."
            url_str = f"{url}" if url else ""
            entry = f"{indent_str}{author_str} {year_str} {title_str} {site}"
            if url_str:
                entry = f"{entry} {url_str}"
            return entry.strip()

        else:
            entry = f"{indent_str}{author_str} {year_str} {title_str}"
            if journal:
                entry = f"{entry} {journal}."
            if doi_str:
                entry = f"{entry} {doi_str}"
            return entry.strip()

    def _format_authors(self, authors: List[str]) -> str:
        """
        Format author list per APA 7th edition.

        Rules:
        - 1 author: Smith, J.
        - 2 authors: Smith, J., & Doe, A.
        - 3-20 authors: Smith, J., Doe, A., ..., & Last, B.
        - 21+ authors: Smith, J., ..., Last, B. (first 19, ..., last)
        """
        if not authors:
            return "Unknown"

        formatted = [self._format_single_author(a) for a in authors]

        if len(formatted) == 1:
            return f"{formatted[0]}"

        if len(formatted) == 2:
            return f"{formatted[0]}, & {formatted[1]}"

        if len(formatted) <= 20:
            return f"{', '.join(formatted[:-1])}, & {formatted[-1]}"

        # 21+ authors: first 19, ..., last
        first_19 = formatted[:19]
        return f"{', '.join(first_19)}, ... {formatted[-1]}"

    def _format_single_author(self, author: str) -> str:
        """
        Format a single author name for reference list.

        'Smith, John' -> 'Smith, J.'
        'Smith, J.' -> 'Smith, J.'
        'John Smith' -> 'Smith, J.'
        """
        name = author.strip()
        if not name:
            return "Unknown"

        if "," in name:
            parts = name.split(",")
            surname = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
            if given:
                initials = " ".join([f"{w[0]}." for w in given.split() if w])
                return f"{surname}, {initials}"
            return surname

        parts = name.split()
        if len(parts) == 1:
            return parts[0]

        surname = parts[-1]
        given_initials = " ".join([f"{w[0]}." for w in parts[:-1] if w])
        return f"{surname}, {given_initials}"

    def _format_title(self, title: str) -> str:
        """Format title per APA 7: sentence case, italic for books."""
        if not title:
            return ""
        title = title.strip()
        if not title.endswith("."):
            title = f"{title}."
        return title

    def _format_journal_article(
        self, journal: Optional[str], volume: Optional[str], issue: Optional[str], pages: Optional[str]
    ) -> str:
        """Format a journal article venue part per APA 7."""
        parts = []
        if journal:
            parts.append(f"*{journal}*,")

        vol_issue = ""
        if volume:
            vol_issue = f"*{volume}*"
        if issue:
            vol_issue = f"{vol_issue}({issue})"
        if vol_issue:
            parts.append(vol_issue)

        if pages:
            parts.append(pages)

        if parts:
            result = " ".join(parts)
            if not result.endswith("."):
                result = f"{result}."
            return result

        return ""

    def _format_doi(self, doi: Optional[str]) -> str:
        """Format DOI as hyperlink per APA 7."""
        if not doi:
            return ""

        doi_value = doi.strip()
        if doi_value.lower().startswith("http"):
            return doi_value
        return f"https://doi.org/{doi_value}"

    def sort_references(self, refs: List[Dict]) -> List[Dict]:
        """
        Sort references alphabetically by surname of first author per APA 7.

        Args:
            refs: List of reference dicts, each must have 'authors' key.

        Returns:
            Sorted list of reference dicts.
        """

        def sort_key(ref):
            authors = ref.get("authors", [])
            if authors:
                return self._extract_surname(authors[0]).lower()
            return ""

        return sorted(refs, key=sort_key)
