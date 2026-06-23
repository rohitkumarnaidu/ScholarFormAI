# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.services.llm_service import generate, sanitize_for_llm

logger = logging.getLogger(__name__)

_DEFAULT_SECTIONS = [
    "Abstract",
    "Introduction",
    "Literature Review",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "References",
]

_DEFAULT_SPEC: Dict[str, Any] = {
    "doc_type": "research_paper",
    "template": "IEEE",
    "sections": list(_DEFAULT_SECTIONS),
    "tone": "academic",
    "length": "medium",
    "citation_style": "ieee",
    "title": "Untitled Research Paper",
    "keywords": [],
}

_KNOWN_DOC_TYPES = {"research_paper", "review", "thesis", "report", "essay"}
_KNOWN_TONES = {"formal", "academic", "technical"}
_KNOWN_LENGTHS = {"short", "medium", "long"}
_KNOWN_CITATION_STYLES = {
    "ieee",
    "apa",
    "vancouver",
    "mla",
    "chicago",
    "harvard",
    "nature",
    "springer",
    "acm",
    "elsevier",
    "numeric",
}


def _load_templates() -> Dict[str, str]:
    app_dir = Path(__file__).resolve().parents[2]
    templates_dir = app_dir / "templates"
    mapping: Dict[str, str] = {}
    if templates_dir.is_dir():
        for entry in templates_dir.iterdir():
            if entry.is_dir():
                mapping[entry.name.lower()] = entry.name.upper()
    return mapping


_TEMPLATE_MAP = _load_templates()


def _extract_json(text: str) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return cleaned[start : end + 1]


def _keywords_from_prompt(prompt: str, limit: int = 6) -> List[str]:
    tokens = [t.strip(".,;:()[]{}\"'").lower() for t in str(prompt or "").split()]
    keywords: List[str] = []
    for token in tokens:
        if len(token) < 4:
            continue
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


class TaskParser:
    def __init__(self) -> None:
        self.last_turn: Dict[str, str] | None = None

    async def parse(self, user_prompt: str) -> Dict[str, Any]:
        system = (
            "You are an academic document planning assistant. Parse the user's request into "
            "a structured task specification. If information is missing, infer reasonable defaults "
            "for an academic paper."
        )
        user = (
            "Return ONLY valid JSON with keys: "
            "doc_type, template, sections, tone, length, citation_style, title, keywords.\n\n"
            f"User prompt: {sanitize_for_llm(user_prompt)}"
        )

        try:
            raw = await asyncio.to_thread(
                generate,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=600,
            )
            self.last_turn = {"system": system, "user": user, "assistant": raw}
            parsed_text = _extract_json(raw)
            if parsed_text:
                data = json.loads(parsed_text)
                return self._validate_spec(data, user_prompt)
        except Exception as exc:
            logger.warning("TaskParser.parse failed, using defaults: %s", exc)

        return self._validate_spec({}, user_prompt)

    def _validate_spec(self, raw: Dict[str, Any], user_prompt: str) -> Dict[str, Any]:
        data = dict(_DEFAULT_SPEC)
        if isinstance(raw, dict):
            data.update({k: v for k, v in raw.items() if v is not None})

        doc_type = str(data.get("doc_type") or "").strip().lower()
        if doc_type not in _KNOWN_DOC_TYPES:
            doc_type = _DEFAULT_SPEC["doc_type"]
        data["doc_type"] = doc_type

        template_raw = str(data.get("template") or "").strip().lower()
        if not template_raw:
            template_raw = _DEFAULT_SPEC["template"].lower()
        template = _TEMPLATE_MAP.get(template_raw, template_raw.upper())
        if template_raw not in _TEMPLATE_MAP and template.upper() not in _TEMPLATE_MAP.values():
            template = _DEFAULT_SPEC["template"]
        data["template"] = template

        tone = str(data.get("tone") or "").strip().lower()
        if tone not in _KNOWN_TONES:
            tone = _DEFAULT_SPEC["tone"]
        data["tone"] = tone

        length = str(data.get("length") or "").strip().lower()
        if length not in _KNOWN_LENGTHS:
            length = _DEFAULT_SPEC["length"]
        data["length"] = length

        citation_style = str(data.get("citation_style") or "").strip().lower()
        if not citation_style:
            citation_style = template.lower()
        if citation_style not in _KNOWN_CITATION_STYLES:
            citation_style = _DEFAULT_SPEC["citation_style"]
        data["citation_style"] = citation_style

        title = str(data.get("title") or "").strip()
        if not title:
            title = f"{doc_type.replace('_', ' ').title()} Draft"
        data["title"] = title

        sections = data.get("sections")
        if not isinstance(sections, list) or not sections:
            sections = list(_DEFAULT_SECTIONS)
        normalized_sections: List[str] = []
        for section in sections:
            section_name = str(section).strip()
            if section_name and section_name not in normalized_sections:
                normalized_sections.append(section_name)
        if "References" not in normalized_sections:
            normalized_sections.append("References")
        data["sections"] = normalized_sections

        keywords = data.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            keywords = _keywords_from_prompt(user_prompt)
        cleaned_keywords = [str(k).strip() for k in keywords if str(k).strip()]
        data["keywords"] = cleaned_keywords[:10]

        return data
