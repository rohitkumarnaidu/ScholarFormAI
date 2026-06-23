# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple

from app.models import Reference, ReferenceType
from app.pipeline.services.csl_engine import CSLEngine
from app.services.crossref_client import get_crossref_client

logger = logging.getLogger(__name__)


_AUTHOR_YEAR_PARENS = re.compile(r"\(([A-Z][^)]*\d{4}[a-z]?)\)")
_AUTHOR_YEAR_BRACKETS = re.compile(r"\[([A-Z][^\]]*\d{4}[a-z]?)\]")
_NUMERIC_BRACKETS = re.compile(r"\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]")


class CitationAssemblyService:
    def __init__(self) -> None:
        self.crossref = get_crossref_client()
        self.csl_engine = CSLEngine()

    async def extract_citations(self, content: str) -> List[str]:
        citations: List[str] = []
        if not content:
            return citations

        for match in _AUTHOR_YEAR_PARENS.findall(content):
            cleaned = self._normalize(match)
            if cleaned and cleaned not in citations:
                citations.append(cleaned)

        for match in _AUTHOR_YEAR_BRACKETS.findall(content):
            cleaned = self._normalize(match)
            if cleaned and cleaned not in citations:
                citations.append(cleaned)

        for match in _NUMERIC_BRACKETS.findall(content):
            numbers = [num.strip() for num in match.split(",") if num.strip()]
            for number in numbers:
                if number not in citations:
                    citations.append(number)

        return citations

    async def lookup_citations(self, citations: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not citations:
            return results

        for citation in citations:
            payload: Dict[str, Any] = {"raw": citation}
            try:
                data = await asyncio.to_thread(self.crossref.validate_citation, citation)
            except Exception as exc:
                logger.warning("CrossRef lookup failed for '%s': %s", citation, exc)
                data = {}
            payload.update(data or {})
            results.append(payload)
            await asyncio.sleep(0.2)
        return results

    async def format_references(self, citations: List[Dict[str, Any]], style: str) -> str:
        if not citations:
            return ""

        references: List[Reference] = []
        for idx, citation in enumerate(citations, start=1):
            authors = []
            raw_authors = citation.get("authors") or ""
            if raw_authors:
                authors = [a.strip() for a in str(raw_authors).split(",") if a.strip()]
            references.append(
                Reference(
                    reference_id=f"ref_{idx:03d}",
                    citation_key=f"[{idx}]",
                    raw_text=str(citation.get("raw") or ""),
                    index=idx - 1,
                    authors=authors,
                    title=citation.get("title"),
                    doi=citation.get("doi"),
                    url=citation.get("url"),
                    reference_type=ReferenceType.UNKNOWN,
                )
            )

        formatted = self.csl_engine.format_references(references, style=style)
        return "\n".join([line for line in formatted if line])

    async def assemble(
        self,
        content_sections: Dict[str, str],
        citation_style: str,
    ) -> Tuple[Dict[str, str], str]:
        merged = "\n\n".join(content_sections.values())
        citations = await self.extract_citations(merged)
        citation_meta = await self.lookup_citations(citations)
        reference_list = await self.format_references(citation_meta, citation_style)

        mapping = {citation: idx + 1 for idx, citation in enumerate(citations)}
        updated_sections = {
            name: self._replace_citations(text, mapping)
            for name, text in content_sections.items()
        }

        return updated_sections, reference_list

    @staticmethod
    def _normalize(raw: str) -> str:
        return " ".join(str(raw).strip().split())

    def _replace_citations(self, text: str, mapping: Dict[str, int]) -> str:
        if not text:
            return text

        def _replace_author_year(match: re.Match) -> str:
            key = self._normalize(match.group(1))
            number = mapping.get(key)
            return f"[{number}]" if number else match.group(0)

        def _replace_numeric(match: re.Match) -> str:
            numbers = [num.strip() for num in match.group(1).split(",") if num.strip()]
            mapped = [str(mapping.get(num, num)) for num in numbers]
            return f"[{', '.join(mapped)}]"

        text = _AUTHOR_YEAR_PARENS.sub(_replace_author_year, text)
        text = _AUTHOR_YEAR_BRACKETS.sub(_replace_author_year, text)
        text = _NUMERIC_BRACKETS.sub(_replace_numeric, text)
        return text
