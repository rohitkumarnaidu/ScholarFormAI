# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference Formatter — citeproc-py backed with legacy fallback.

Uses industry-standard CSL (Citation Style Language) files via citeproc-py
to format references. Falls back to the original regex-based formatting
if citeproc is unavailable or the template lacks a styles.csl file.
"""

import os
import logging
import re
from typing import Optional, Dict, Any, List

from app.models import Reference, CitationStyle
from app.pipeline.contracts.loader import ContractLoader

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Try to import citeproc-py (optional dependency)
# --------------------------------------------------------------------------- #
try:
    from citeproc import CitationStylesStyle, CitationStylesBibliography, formatter
    from citeproc import Citation, CitationItem
    from citeproc.source import BibliographySource
    from citeproc.source.json import CiteProcJSON

    CITEPROC_AVAILABLE = True
    logger.info("citeproc-py loaded successfully.")
except ImportError:
    CITEPROC_AVAILABLE = False
    logger.warning(
        "citeproc-py is not installed. Reference formatting will use legacy fallback. "
        "Install with: pip install citeproc-py"
    )


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")


def _resolve_csl_path(publisher: str) -> Optional[str]:
    """Resolve the CSL file path for a given publisher/template name."""
    if not publisher:
        return None
    name = publisher.lower().strip()
    csl_path = os.path.normpath(os.path.join(_TEMPLATES_DIR, name, "styles.csl"))
    if os.path.isfile(csl_path):
        return csl_path
    return None


def _reference_type_to_csl(ref: Reference) -> str:
    """Map our ReferenceType enum to CSL type strings."""
    mapping = {
        "journal_article": "article-journal",
        "conference_paper": "paper-conference",
        "book": "book",
        "book_chapter": "chapter",
        "thesis": "thesis",
        "technical_report": "report",
        "patent": "patent",
        "web_page": "webpage",
        "preprint": "article",
    }
    return mapping.get(ref.reference_type, "article")


def _parse_author_name(name_str: str) -> Dict[str, str]:
    """
    Parse a name string like 'Smith, J.' or 'Jane Doe' into CSL name parts.
    Returns dict with 'family' and optionally 'given'.
    """
    name_str = name_str.strip()
    if not name_str:
        return {"family": "Unknown"}

    if "," in name_str:
        parts = [p.strip() for p in name_str.split(",", 1)]
        return {"family": parts[0], "given": parts[1] if len(parts) > 1 else ""}
    else:
        parts = name_str.rsplit(" ", 1)
        if len(parts) == 2:
            return {"given": parts[0], "family": parts[1]}
        return {"family": parts[0]}


def _reference_to_csl_json(ref: Reference) -> Dict[str, Any]:
    """
    Convert a Reference model object to a CSL-JSON dict suitable
    for citeproc-py's CiteProcJSON source.
    """
    item: Dict[str, Any] = {
        "id": ref.reference_id,
        "type": _reference_type_to_csl(ref),
    }

    # Authors
    if ref.authors:
        item["author"] = [_parse_author_name(a) for a in ref.authors]

    # Title
    if ref.title:
        item["title"] = ref.title

    # Container (journal / conference / book)
    container = ref.journal or ref.conference or ref.book_title
    if container:
        item["container-title"] = container

    # Publisher
    if ref.publisher:
        item["publisher"] = ref.publisher

    # Date
    if ref.year:
        item["issued"] = {"date-parts": [[ref.year]]}

    # Volume / Issue / Pages
    if ref.volume:
        item["volume"] = ref.volume
    if ref.issue:
        item["issue"] = ref.issue
    if ref.pages:
        item["page"] = ref.pages

    # Identifiers
    if ref.doi:
        item["DOI"] = ref.doi
    if ref.isbn:
        item["ISBN"] = ref.isbn
    if ref.issn:
        item["ISSN"] = ref.issn
    if ref.url:
        item["URL"] = ref.url

    # Edition
    if ref.edition:
        item["edition"] = ref.edition

    # Note
    if ref.note:
        item["note"] = ref.note

    return item


# --------------------------------------------------------------------------- #
#  Main class
# --------------------------------------------------------------------------- #
class ReferenceFormatter:
    """
    Normalizes and formats references based on citation style rules.

    Primary:  citeproc-py + CSL file from templates/<publisher>/styles.csl
    Fallback: Original regex-based formatting if citeproc is unavailable
              or the template has no CSL file.
    """

    def __init__(self, contract_loader: ContractLoader):
        self.contract_loader = contract_loader
        # Cache loaded CSL styles to avoid re-parsing for every reference
        self._style_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    #  Public API (unchanged signature)
    # ------------------------------------------------------------------ #
    def format_reference(self, reference: Reference, publisher: str) -> str:
        """Format a reference according to publisher guidelines.

        Args:
            reference: A Reference model object with bibliographic fields.
            publisher: Template / publisher name (e.g. 'ieee', 'apa').

        Returns:
            Formatted reference string.
        """
        # Attempt citeproc formatting first
        if CITEPROC_AVAILABLE:
            try:
                result = self._format_with_citeproc(reference, publisher)
                if result:
                    return result
            except Exception as exc:
                logger.warning(
                    "citeproc formatting failed for ref '%s' (publisher=%s): %s. Falling back to legacy formatter.",
                    reference.reference_id,
                    publisher,
                    exc,
                )

        # Fallback to legacy formatting
        return self._format_legacy(reference, publisher)

    def format_references(self, references: List[Reference], publisher: str) -> List[str]:
        """Format a list of references. Convenience wrapper.

        Args:
            references: List of Reference model objects.
            publisher: Template / publisher name.

        Returns:
            List of formatted reference strings.
        """
        return [self.format_reference(ref, publisher) for ref in references]

    # ------------------------------------------------------------------ #
    #  citeproc-py formatting
    # ------------------------------------------------------------------ #
    def _format_with_citeproc(self, reference: Reference, publisher: str) -> Optional[str]:
        """Format a single reference using citeproc-py."""
        csl_path = _resolve_csl_path(publisher)
        if not csl_path:
            logger.debug("No CSL file found for publisher '%s'. Skipping citeproc.", publisher)
            return None

        # Load or retrieve cached style
        style = self._get_or_load_style(csl_path)
        if style is None:
            return None

        # Build source from single reference
        csl_data = [_reference_to_csl_json(reference)]
        bib_source = CiteProcJSON(csl_data)

        # Create bibliography
        bibliography = CitationStylesBibliography(style, bib_source, formatter.plain)

        # Register the citation
        citation = Citation([CitationItem(reference.reference_id)])
        bibliography.register(citation)

        # Render
        bib_entries = bibliography.bibliography()
        if bib_entries and len(bib_entries) > 0:
            # bib_entries is a list of formatted strings
            rendered = str(bib_entries[0]).strip()
            if rendered:
                return rendered

        return None

    def _get_or_load_style(self, csl_path: str) -> Optional[Any]:
        """Load a CSL style file, caching the result."""
        if csl_path in self._style_cache:
            return self._style_cache[csl_path]

        try:
            style = CitationStylesStyle(csl_path, validate=False)
            self._style_cache[csl_path] = style
            logger.info("Loaded CSL style from: %s", csl_path)
            return style
        except Exception as exc:
            logger.error("Failed to load CSL style '%s': %s", csl_path, exc)
            self._style_cache[csl_path] = None
            return None

    # ------------------------------------------------------------------ #
    #  Legacy fallback formatting (original code)
    # ------------------------------------------------------------------ #
    def _format_legacy(self, reference: Reference, publisher: str) -> str:
        """Original regex-based formatting. Kept as fallback."""
        contract = self.contract_loader.load(publisher)
        style_rule = contract.get("references", {}).get("style", "IEEE")

        # Simplified formatting for IEEE
        if style_rule == "IEEE":
            authors = reference.get_author_list(max_authors=3)
            title = f'"{reference.title}"' if reference.title else "Untitled"
            venue = reference.journal or reference.conference or ""
            year = reference.year or ""
            return f"[{reference.number}] {authors}, {title}, {venue}, {year}."

        # Light cleanup for "none" style: preserve original, normalize whitespace
        if style_rule == "none":
            text = reference.raw_text if hasattr(reference, "raw_text") and reference.raw_text else str(reference)
            text = " ".join(text.split())  # Remove duplicate spaces
            return text.strip()

        return reference.raw_text
