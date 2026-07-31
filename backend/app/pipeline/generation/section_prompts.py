# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from typing import Any, Dict

SECTION_PROMPTS = {
    "Abstract": (
        "Write a concise academic abstract (150-300 words) summarizing the paper's purpose, "
        "methods, key findings, and conclusions. Use formal academic tone. Do not include "
        "citations in the abstract."
    ),
    "Introduction": (
        "Write the introduction section. Include: background context, problem statement, "
        "research objectives, significance of the study, and a brief outline of the paper "
        "structure. Cite relevant literature where appropriate."
    ),
    "Literature Review": (
        "Write a comprehensive literature review. Organize thematically. Critically analyze "
        "and synthesize existing research. Identify gaps that this work addresses. Use proper "
        "academic citations."
    ),
    "Methods": (
        "Write the methodology section. Describe: research design, data collection methods, "
        "analysis techniques, tools/software used, and any ethical considerations. Be specific "
        "and reproducible."
    ),
    "Results": (
        "Write the results section. Present findings clearly and systematically. Reference "
        "tables and figures where applicable. Do not interpret results here -- save interpretation "
        "for Discussion."
    ),
    "Discussion": (
        "Write the discussion section. Interpret findings in context of existing literature. "
        "Address implications, limitations, and compare with previous studies. Suggest future "
        "research directions."
    ),
    "Conclusion": (
        "Write a concise conclusion. Summarize key findings, restate their significance, "
        "acknowledge limitations briefly, and end with future research directions or "
        "practical implications."
    ),
}


def _truncate(text: str, limit: int = 1200) -> str:
    if not text:
        return ""
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def get_section_prompt(section_name: str, context: Dict[str, Any]) -> str:
    system_prompt = SECTION_PROMPTS.get(
        section_name,
        "Write a rigorous academic section for the specified heading. Use formal tone and "
        "include citations where appropriate.",
    )
    task_spec = context.get("task_spec") or {}
    template_rules = context.get("template_rules") or []
    outline = context.get("outline") or []
    previous_sections = context.get("previous_sections") or {}

    prev_payload = {
        key: _truncate(value) for key, value in previous_sections.items() if isinstance(value, str) and value.strip()
    }

    prompt_parts = [
        system_prompt,
        "",
        "Document context (JSON):",
        json.dumps(task_spec, ensure_ascii=False, indent=2),
        "",
        "Template rules:",
        json.dumps(template_rules, ensure_ascii=False, indent=2),
        "",
        "Outline:",
        json.dumps(outline, ensure_ascii=False, indent=2),
    ]

    if prev_payload:
        prompt_parts.extend(
            [
                "",
                "Previous sections (summarized):",
                json.dumps(prev_payload, ensure_ascii=False, indent=2),
            ]
        )

    return "\n".join(prompt_parts).strip()
