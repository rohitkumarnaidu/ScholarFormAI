# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference Formatter Engine - CSL-first reference formatting stage.

Uses citeproc-py through CSLEngine and falls back to deterministic templates
from contract.yaml when CSL formatting is unavailable.
"""

import logging

from app.models import PipelineDocument as Document
from app.models import Reference
from app.pipeline.contracts.loader import ContractLoader
from app.pipeline.services.csl_engine import CSLEngine

logger = logging.getLogger(__name__)


class ReferenceFormatterEngine:
    """
    Formats references according to publisher rules.
    CSL is attempted first to support standard and custom citation styles.
    """

    def __init__(self, contract_loader: ContractLoader, csl_engine: CSLEngine | None = None):
        if contract_loader is None:
            raise ValueError("contract_loader cannot be None")
        self.contract_loader = contract_loader
        self.csl_engine = csl_engine or CSLEngine()

    def process(self, document: Document) -> Document:
        """Standard pipeline stage entry point."""
        publisher = document.template.template_name if document.template else "IEEE"
        document.references = self.format_all(document.references, publisher)
        return document

    def format_all(self, references: list[Reference], publisher: str) -> list[Reference]:
        """Format a list of references."""
        if not references:
            return references

        contract = self.contract_loader.load(publisher)
        reference_cfg = contract.get("references", {})

        style_name = str(reference_cfg.get("style") or publisher or "ieee").lower()
        style_path = reference_cfg.get("csl_style_path")

        try:
            rendered = self.csl_engine.format_references(
                references,
                style=style_name,
                style_path=style_path,
            )
            if len(rendered) != len(references):
                raise ValueError(f"CSL output length mismatch: expected {len(references)}, got {len(rendered)}")

            for ref, formatted in zip(references, rendered, strict=False):
                ref.formatted_text = formatted
            return references
        except Exception as exc:
            logger.warning(
                "CSL formatting failed for publisher '%s' (style '%s'): %s. "
                "Falling back to contract normalization templates.",
                publisher,
                style_name,
                exc,
            )

        rules = reference_cfg.get("normalization", {})
        if not rules:
            return references

        for ref in references:
            ref.formatted_text = self.format_single(ref, rules)

        return references

    def format_single(self, ref: Reference, rules: dict) -> str:
        """Apply deterministic fallback template formatting to a single reference."""
        ref_type = getattr(ref.reference_type, "value", ref.reference_type)
        ref_type = str(ref_type).lower()

        if ref_type == "journal_article":
            template = rules.get("journal_format")
        elif ref_type == "conference_paper":
            template = rules.get("conference_format")
        else:
            template = rules.get("default_format", "{authors}, {title}, {year}.")

        max_authors = rules.get("max_authors", 99)
        et_al = rules.get("et_al_suffix", "et al.")

        if len(ref.authors) > max_authors:
            authors_str = f"{ref.authors[0]} {et_al}"
        else:
            authors_str = ", ".join(ref.authors) if ref.authors else "Unknown Author"

        data = {
            "authors": authors_str,
            "title": ref.title or "[Missing Title]",
            "journal": ref.journal or ref.metadata.get("journal_full", ""),
            "conference": ref.conference or ref.metadata.get("conf_full", ""),
            "year": str(ref.year) if ref.year else "[n.d.]",
            "volume": ref.volume or "",
            "issue": ref.issue or "",
            "pages": ref.pages or "",
            "doi": f"doi: {ref.doi}" if ref.doi else "",
        }

        try:
            formatted = template.format(**data)
            return formatted.replace("..", ".").replace(",,", ",").strip()
        except Exception:
            return ref.raw_text
