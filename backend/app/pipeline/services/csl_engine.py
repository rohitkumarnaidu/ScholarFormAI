# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
CSL citation formatting engine.

Uses citeproc-py when available and falls back to deterministic formatting.
This engine supports any valid CSL style file, including external style sets
with 10,000+ available styles in the broader CSL ecosystem.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.models import Reference

try:
    from citeproc import (
        Citation,
        CitationItem,
        CitationStylesBibliography,
        CitationStylesStyle,
        formatter,
    )
    from citeproc.source.json import CiteProcJSON

    CITEPROC_AVAILABLE = True
except Exception:  # pragma: no cover - import path depends on optional dependency
    CITEPROC_AVAILABLE = False

logger = logging.getLogger(__name__)


class CSLEngineError(RuntimeError):
    """Raised when CSL formatting cannot be completed."""


class CSLEngine:
    """Format references with CSL style files."""

    DEFAULT_STYLE_MAP = {
        "ieee": "ieee",
        "apa": "apa",
    }
    ESTIMATED_AVAILABLE_STYLES = 10_000

    def __init__(self, templates_dir: str | None = None):
        app_dir = Path(__file__).resolve().parents[2]
        self.templates_dir = Path(templates_dir) if templates_dir else app_dir / "templates"

    def get_capabilities(self) -> dict[str, Any]:
        """
        Return capability metadata.

        The style count is an ecosystem-level estimate based on the CSL style
        repository and compatibility with custom CSL files.
        """
        return {
            "supports_citeproc": CITEPROC_AVAILABLE,
            "supports_external_csl_files": True,
            "estimated_available_styles": self.ESTIMATED_AVAILABLE_STYLES,
        }

    def supports_10k_plus_styles(self) -> bool:
        """Whether the engine can consume the broader 10k+ CSL style ecosystem."""
        return self.ESTIMATED_AVAILABLE_STYLES >= 10_000

    def resolve_style_path(self, style: str, style_path: str | None = None) -> Path:
        """Resolve style path from explicit path or built-in template mapping."""
        if style_path:
            explicit = Path(style_path)
            if explicit.is_file():
                return explicit

            backend_dir = Path(__file__).resolve().parents[3]
            backend_relative = backend_dir / style_path
            if backend_relative.is_file():
                return backend_relative

            raise FileNotFoundError(f"CSL style file not found: {style_path}")

        style_key = (style or "ieee").strip().lower()
        style_folder = self.DEFAULT_STYLE_MAP.get(style_key, style_key)
        default_path = self.templates_dir / style_folder / "styles.csl"
        if not default_path.is_file():
            raise FileNotFoundError(f"Built-in CSL style file not found for style '{style_key}': {default_path}")
        return default_path

    def format_reference(self, reference: Reference, style: str = "ieee", style_path: str | None = None) -> str:
        """Format a single reference."""
        formatted = self.format_references([reference], style=style, style_path=style_path)
        return formatted[0] if formatted else ""

    def format_references(
        self, references: list[Reference], style: str = "ieee", style_path: str | None = None
    ) -> list[str]:
        """Format multiple references using CSL or deterministic fallback."""
        if not references:
            return []

        if CITEPROC_AVAILABLE:
            try:
                return self._format_with_citeproc(references, style=style, style_path=style_path)
            except Exception as exc:
                logger.warning(
                    "CSL formatting failed for style '%s'; falling back to deterministic formatter: %s",
                    style,
                    exc,
                )

        return [self._format_fallback(ref, style=style) for ref in references]

    def _format_with_citeproc(self, references: list[Reference], style: str, style_path: str | None) -> list[str]:
        """Format references with citeproc-py."""
        style_file = self.resolve_style_path(style=style, style_path=style_path)
        csl_items = [self._reference_to_csl_json(ref=ref, index=index) for index, ref in enumerate(references, start=1)]

        source = CiteProcJSON(csl_items)
        style_obj = CitationStylesStyle(str(style_file), validate=False)
        bibliography = CitationStylesBibliography(style_obj, source, formatter.plain)

        for item in csl_items:
            bibliography.register(Citation([CitationItem(item["id"])]))

        rendered_entries = [str(entry).strip() for entry in bibliography.bibliography()]
        if len(rendered_entries) != len(references):
            raise CSLEngineError(
                f"CSL bibliography output length mismatch (expected {len(references)}, got {len(rendered_entries)})"
            )
        return rendered_entries

    def _reference_to_csl_json(self, ref: Reference, index: int) -> dict[str, Any]:
        """Map internal reference model to CSL-JSON item."""
        ref_type = getattr(ref.reference_type, "value", ref.reference_type)
        ref_type = str(ref_type).lower()
        csl_type = {
            "journal_article": "article-journal",
            "conference_paper": "paper-conference",
            "book": "book",
            "book_chapter": "chapter",
            "thesis": "thesis",
            "technical_report": "report",
            "patent": "patent",
            "web_page": "webpage",
            "preprint": "article",
        }.get(ref_type, "article")

        csl_item: dict[str, Any] = {
            "id": ref.reference_id or f"ref_{index}",
            "type": csl_type,
            "title": ref.title or "Untitled",
        }

        if ref.authors:
            csl_item["author"] = [self._to_csl_name(name) for name in ref.authors if name.strip()]

        container_title = ref.journal or ref.conference or ref.book_title
        if container_title:
            csl_item["container-title"] = container_title

        if ref.publisher:
            csl_item["publisher"] = ref.publisher
        if ref.year:
            csl_item["issued"] = {"date-parts": [[int(ref.year)]]}
        if ref.volume:
            csl_item["volume"] = str(ref.volume)
        if ref.issue:
            csl_item["issue"] = str(ref.issue)
        if ref.pages:
            csl_item["page"] = str(ref.pages)
        if ref.doi:
            csl_item["DOI"] = ref.doi
        if ref.url:
            csl_item["URL"] = ref.url
        if ref.isbn:
            csl_item["ISBN"] = ref.isbn
        if ref.issn:
            csl_item["ISSN"] = ref.issn

        return csl_item

    def _to_csl_name(self, name: str) -> dict[str, str]:
        """Convert free-text author name to CSL name object."""
        clean_name = " ".join(name.strip().split())
        if not clean_name:
            return {"literal": "Unknown Author"}

        if "," in clean_name:
            family, given = [part.strip() for part in clean_name.split(",", 1)]
            if family and given:
                return {"family": family, "given": given}
            if family:
                return {"family": family}

        parts = clean_name.split()
        if len(parts) == 1:
            return {"literal": clean_name}

        return {"given": " ".join(parts[:-1]), "family": parts[-1]}

    def _format_fallback(self, ref: Reference, style: str) -> str:
        """Deterministic formatter used when CSL execution is unavailable."""
        style_key = (style or "ieee").strip().lower()
        if style_key == "apa":
            return self._format_apa_fallback(ref)
        return self._format_ieee_fallback(ref)

    def _format_ieee_fallback(self, ref: Reference) -> str:
        authors = ", ".join(ref.authors) if ref.authors else "Unknown Author"
        title = ref.title or "Untitled"
        venue = ref.journal or ref.conference or ref.book_title or ref.publisher or ""

        parts: list[str] = [f'{authors}, "{title},"']
        if venue:
            parts.append(venue)
        if ref.volume:
            parts.append(f"vol. {ref.volume}")
        if ref.issue:
            parts.append(f"no. {ref.issue}")
        if ref.pages:
            parts.append(f"pp. {ref.pages}")
        if ref.year:
            parts.append(str(ref.year))

        formatted = ", ".join(part for part in parts if part).strip(", ")
        if ref.doi:
            formatted = f"{formatted}. doi:{ref.doi}"
        if not formatted.endswith("."):
            formatted = f"{formatted}."
        return formatted

    def _format_apa_fallback(self, ref: Reference) -> str:
        authors = self._format_apa_authors(ref.authors)
        year_part = f"({ref.year})." if ref.year else "(n.d.)."
        title = f"{ref.title or 'Untitled'}."

        venue_parts: list[str] = []
        venue = ref.journal or ref.conference or ref.book_title or ref.publisher
        if venue:
            venue_parts.append(venue)
        if ref.volume and ref.issue:
            venue_parts.append(f"{ref.volume}({ref.issue})")
        elif ref.volume:
            venue_parts.append(str(ref.volume))
        if ref.pages:
            venue_parts.append(ref.pages)

        venue_text = ", ".join(venue_parts)
        if venue_text and not venue_text.endswith("."):
            venue_text = f"{venue_text}."

        doi_text = ""
        if ref.doi:
            doi_value = ref.doi.strip()
            doi_text = doi_value if doi_value.lower().startswith("http") else f"https://doi.org/{doi_value}"

        formatted = " ".join(part for part in [authors, year_part, title, venue_text, doi_text] if part).strip()
        return formatted

    def _format_apa_authors(self, authors: list[str]) -> str:
        if not authors:
            return "Unknown Author"
        if len(authors) == 1:
            return authors[0]
        if len(authors) == 2:
            return f"{authors[0]}, & {authors[1]}"
        return f"{', '.join(authors[:-1])}, & {authors[-1]}"
