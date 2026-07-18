# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Vancouver citation fallback formatter.

Implements Vancouver (numeric) citation formatting rules for in-text citations,
reference entries, and bibliography. Used when citeproc-py is
unavailable or CSL file loading fails.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class VancouverFormatter:
    """
    Vancouver citation formatting.

    Rules implemented:
    - Numbered in order of appearance
    - Author list: up to 6 authors, et al after 6
    - In-text citations: superscript numbers [1], [1,2], [1-3]
    - Reference entries: numbered list
    - Journal abbreviations recommended
    - DOI included when available
    """

    def __init__(self):
        self._ref_counter = 0

    def format_intext_citation(self, ref_numbers: List[int]) -> str:
        """
        Format in-text citation using Vancouver (numeric) style.

        Args:
            ref_numbers: List of reference numbers.

        Returns:
            Formatted citation string like "[1]" or "[1,3,5]" or "[1-3]".
        """
        if not ref_numbers:
            return ""

        sorted_nums = sorted(ref_numbers)

        if len(sorted_nums) == 1:
            return f"[{sorted_nums[0]}]"

        # Detect consecutive ranges
        ranges: List[str] = []
        start = sorted_nums[0]
        end = sorted_nums[0]

        for num in sorted_nums[1:]:
            if num == end + 1:
                end = num
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = num
                end = num

        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return f"[{','.join(ranges)}]"

    def format_reference_entry(
        self,
        authors: List[str],
        title: Optional[str] = None,
        journal: Optional[str] = None,
        year: Optional[int] = None,
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
    ) -> str:
        """
        Format a single reference entry per Vancouver style.

        Vancouver format (journal article):
        Author(s). Title. Abbreviated Journal Name. Year Month Day;Volume(Issue):Pages. DOI.

        Args:
            authors: List of author names.
            title: Article title.
            journal: Journal name.
            year: Publication year.
            volume: Volume number.
            issue: Issue number.
            pages: Page range.
            publisher: Publisher name.
            doi: Digital Object Identifier.
            url: URL.
            book_title: Book title (for chapters).
            edition: Edition (for books).
            conference: Conference name.
            reference_type: Type of reference.

        Returns:
            Formatted Vancouver reference entry.
        """
        author_str = self._format_authors(authors)
        title_str = f"{title or 'Untitled'}."
        doi_str = self._format_doi(doi)
        year_str = str(year) if year else ""

        if reference_type == "journal_article":
            venue_parts = []
            if journal:
                venue_parts.append(f"{journal}.")
            if year_str:
                venue_parts.append(year_str)
            vol_issue = ""
            if volume:
                vol_issue = volume
            if issue:
                vol_issue = f"{vol_issue}({issue})"
            if vol_issue:
                venue_parts.append(vol_issue)
            if pages:
                venue_parts.append(f":{pages}.")

            venue_text = " ".join(venue_parts) if venue_parts else ""

            entry = f"{author_str} {title_str}"
            if venue_text:
                entry = f"{entry} {venue_text}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

        elif reference_type == "book":
            pub = f"{publisher}." if publisher else ""
            entry = f"{author_str} {title_str}"
            if edition:
                entry = f"{entry} ({edition} ed.)."
            if year_str:
                entry = f"{entry} {year_str}."
            if pub:
                entry = f"{entry} {pub}"
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

        elif reference_type == "book_chapter":
            entry = f"{author_str} {title_str}"
            if book_title:
                entry = f"{entry} In: {book_title}."
            if year_str:
                entry = f"{entry} {year_str}."
            if publisher:
                entry = f"{entry} {publisher}."
            if pages:
                entry = f"{entry} p. {pages}."
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

        elif reference_type == "thesis":
            entry = f"{author_str} {title_str}"
            if year_str:
                entry = f"{entry} {year_str}."
            entry = f"{entry} [Dissertation]. {publisher or 'Unknown Institution'}."
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

        elif reference_type == "conference_paper":
            entry = f"{author_str} {title_str}"
            if conference:
                entry = f"{entry} {conference}."
            if year_str:
                entry = f"{entry} {year_str}."
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

        else:
            entry = f"{author_str} {title_str}"
            if year_str:
                entry = f"{entry} {year_str}."
            if doi_str:
                entry = f"{entry} {doi_str}"
            if not entry.endswith("."):
                entry = f"{entry}."
            return entry

    def _format_authors(self, authors: List[str]) -> str:
        """
        Format authors per Vancouver style.

        Rules:
        - Up to 6 authors: list all, comma-separated
        - More than 6: first 6, then 'et al.'
        """
        if not authors:
            return "Unknown"

        if len(authors) <= 6:
            author_list = ", ".join(authors)
        else:
            author_list = f"{', '.join(authors[:6])}, et al."

        return author_list

    def _format_doi(self, doi: Optional[str]) -> str:
        """Format DOI for Vancouver style."""
        if not doi:
            return ""
        doi_value = doi.strip()
        if doi_value.lower().startswith("http"):
            parts = doi_value.rsplit("/", 1)
            if len(parts) > 1:
                return f"doi: {parts[-1]}."
            return f"doi: {doi_value}."
        return f"doi: {doi_value}."

    def sort_references(self, refs: List[Dict]) -> List[Dict]:
        """
        Vancouver style: references numbered in order of appearance.
        This method ensures the list maintains citation order.
        If refs have 'index' field, sort by it; otherwise return as-is.
        """
        if not refs:
            return refs

        if all("index" in r for r in refs):
            return sorted(refs, key=lambda r: r["index"])

        return refs
