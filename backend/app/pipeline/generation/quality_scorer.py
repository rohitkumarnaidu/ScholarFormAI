# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import math
import re
from typing import Any

_CITATION_PATTERNS = [
    re.compile(r"\[\d+(?:\s*,\s*\d+)*\]"),
    re.compile(r"\([A-Z][^)]*\d{4}[a-z]?\)"),
    re.compile(r"\[[A-Z][^\]]*\d{4}[a-z]?\]"),
]


class QualityScorer:
    def score(self, content: dict[str, Any], template: str, task_spec: dict[str, Any]) -> dict[str, Any]:
        sections_map = self._normalize_sections(content)
        required_sections = self._required_sections(task_spec, sections_map)

        present_sections = [s for s in required_sections if sections_map.get(s)]
        template_compliance = self._percentage(len(present_sections), len(required_sections))

        completeness = 0.0
        if required_sections:
            adequate = 0
            for section in required_sections:
                if self._word_count(sections_map.get(section, "")) >= 100:
                    adequate += 1
            completeness = self._percentage(adequate, len(required_sections))

        full_text = "\n\n".join(sections_map.values())
        citation_count = self._count_citations(full_text)
        word_count = self._word_count(full_text)

        section_balance = self._section_balance(sections_map, required_sections)
        citations_score = self._citation_score(citation_count, max(len(required_sections), 1))

        overall = template_compliance * 0.30 + completeness * 0.30 + citations_score * 0.20 + section_balance * 0.20

        return {
            "template_compliance": round(template_compliance, 2),
            "content_completeness": round(completeness, 2),
            "citation_count": int(citation_count),
            "word_count": int(word_count),
            "section_balance": round(section_balance, 2),
            "overall_score": round(overall, 2),
        }

    @staticmethod
    def _normalize_sections(content: dict[str, Any]) -> dict[str, str]:
        if not content:
            return {}
        if "sections" in content and isinstance(content["sections"], list):
            sections_map: dict[str, str] = {}
            for item in content["sections"]:
                if isinstance(item, dict):
                    title = str(item.get("title") or item.get("section") or "").strip()
                    text = str(item.get("content") or "").strip()
                    if title:
                        sections_map[title] = text
            return sections_map
        return {str(k): str(v) for k, v in content.items() if isinstance(v, (str, int, float))}

    @staticmethod
    def _required_sections(task_spec: dict[str, Any], sections_map: dict[str, str]) -> list[str]:
        required = task_spec.get("sections") if isinstance(task_spec, dict) else None
        if isinstance(required, list) and required:
            return [str(item).strip() for item in required if str(item).strip()]
        if sections_map:
            return list(sections_map.keys())
        return []

    @staticmethod
    def _word_count(text: str) -> int:
        if not text:
            return 0
        return len([w for w in str(text).split() if w.strip()])

    @staticmethod
    def _count_citations(text: str) -> int:
        if not text:
            return 0
        total = 0
        for pattern in _CITATION_PATTERNS:
            total += len(pattern.findall(text))
        return total

    @staticmethod
    def _section_balance(sections: dict[str, str], required_sections: list[str]) -> float:
        counts: list[int] = []
        for section in required_sections:
            counts.append(len(sections.get(section, "").split()))
        if not counts:
            return 0.0
        if len(counts) == 1:
            return 100.0
        mean = sum(counts) / len(counts)
        if mean <= 0:
            return 0.0
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean if mean else 0.0
        balance = 100.0 - min(100.0, cv * 100.0)
        return max(0.0, balance)

    @staticmethod
    def _citation_score(citation_count: int, section_count: int) -> float:
        if section_count <= 0:
            return 0.0
        citations_per_section = citation_count / max(section_count, 1)
        return min(100.0, citations_per_section * 100.0)

    @staticmethod
    def _percentage(part: int, whole: int) -> float:
        if whole <= 0:
            return 0.0
        return (part / whole) * 100.0
