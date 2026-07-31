# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set


_TEMPLATE_REQUIREMENTS = {
    "ieee": [
        {"abstract"},
        {"introduction"},
        {"methods", "methodology"},
        {"results"},
        {"conclusion"},
        {"references"},
    ],
    "apa": [
        {"abstract"},
        {"introduction"},
        {"discussion"},
        {"conclusion"},
        {"references"},
    ],
    "acm": [
        {"abstract"},
        {"introduction"},
        {"system design", "methods", "methodology"},
        {"references"},
    ],
    "nature": [
        {"abstract"},
        {"introduction"},
        {"analysis", "results"},
        {"conclusion"},
        {"references"},
    ],
    "resume": [
        {"summary", "professional summary"},
        {"experience", "work experience"},
        {"education"},
        {"skills"},
    ],
}


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _flatten_aliases(alias_groups: Iterable[Set[str]]) -> List[str]:
    flattened: List[str] = []
    for alias_group in alias_groups:
        flattened.extend(sorted(alias_group))
    return flattened


def _display_section_name(alias_group: Set[str]) -> str:
    alias = sorted(alias_group)[0] if alias_group else "Section"
    return " ".join(part.capitalize() for part in _normalize(alias).split())


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        normalized = _normalize(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value)
    return ordered


def _infer_provider_from_model(model_name: Any) -> str | None:
    normalized = _normalize(model_name)
    if not normalized:
        return None
    if "groq" in normalized:
        return "groq"
    if "nvidia" in normalized or "llama 3.3 70b" in normalized:
        return "nvidia"
    if "ollama" in normalized or "deepseek" in normalized:
        return "ollama"
    if "openai" in normalized or normalized.startswith("gpt"):
        return "openai"
    if "anthropic" in normalized or "claude" in normalized:
        return "anthropic"
    if "rule_based" in normalized or "rule based" in normalized:
        return "rule_based"
    return None


def _extract_missing_sections(validation_results: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for item in (validation_results.get("errors") or []) + (validation_results.get("warnings") or []):
        if not isinstance(item, str):
            continue
        prefix = "missing required section:"
        lowered = item.strip().lower()
        if lowered.startswith(prefix):
            missing.append(item.split(":", 1)[1].strip())
    return _dedupe_preserve_order(missing)


def _extract_llm_provider(validation_results: Dict[str, Any]) -> str | None:
    direct_provider = _normalize(validation_results.get("llm_provider_used"))
    if direct_provider:
        return direct_provider

    semantic_audit = validation_results.get("ai_semantic_audit") or {}
    semantic_provider = _normalize(semantic_audit.get("llm_provider"))
    if semantic_provider:
        return semantic_provider

    return _infer_provider_from_model(semantic_audit.get("model"))


def _collect_present_sections(structured_data: Dict[str, Any]) -> Set[str]:
    present: Set[str] = set()
    metadata = structured_data.get("metadata") or {}
    if _normalize(metadata.get("abstract")):
        present.add("abstract")
    if structured_data.get("references"):
        present.add("references")

    for heading in structured_data.get("headings") or []:
        normalized = _normalize(heading.get("text"))
        if normalized:
            present.add(normalized)

    return present


def _section_has_content(
    aliases: Set[str],
    structured_data: Dict[str, Any],
) -> bool:
    normalized_aliases = {_normalize(alias) for alias in aliases}
    metadata = structured_data.get("metadata") or {}
    if "abstract" in normalized_aliases and _normalize(metadata.get("abstract")):
        return True
    if "references" in normalized_aliases and structured_data.get("references"):
        return True

    for block in structured_data.get("blocks") or []:
        block_type = _normalize(block.get("block_type"))
        if block_type in {"heading_1", "heading_2", "heading_3", "heading_4", "abstract_heading", "references_heading"}:
            continue

        section_name = _normalize(block.get("section_name"))
        text = _normalize(block.get("text"))
        if not text:
            continue

        if section_name and any(alias in section_name for alias in normalized_aliases):
            return True

    return False


def compute_quality_score(
    structured_data: dict,
    template_name: str,
    validation_results: dict,
) -> dict:
    """Compute structural quality metrics for a formatted document."""
    normalized_template = _normalize(template_name) or "default"
    requirements = _TEMPLATE_REQUIREMENTS.get(
        normalized_template,
        [{"abstract"}, {"references"}],
    )

    present_sections = _collect_present_sections(structured_data)
    compliant_sections = 0
    content_complete_sections = 0
    missing_sections = _extract_missing_sections(validation_results)

    for alias_group in requirements:
        normalized_aliases = {_normalize(alias) for alias in alias_group}
        if present_sections.intersection(normalized_aliases):
            compliant_sections += 1
        else:
            missing_sections.append(_display_section_name(alias_group))
        if _section_has_content(alias_group, structured_data):
            content_complete_sections += 1

    total_required = max(1, len(requirements))
    template_compliance_pct = round((compliant_sections / total_required) * 100, 2)
    content_completeness_pct = round((content_complete_sections / total_required) * 100, 2)

    references = structured_data.get("references") or []
    citation_count = len([reference for reference in references if reference])
    citation_target = max(1, int(validation_results.get("citation_target") or 5))
    citation_score_pct = round(min(citation_count / citation_target, 1.0) * 100, 2)

    overall_score = round(
        (template_compliance_pct * 0.4) + (content_completeness_pct * 0.4) + (citation_score_pct * 0.2),
        2,
    )
    llm_provider_used = _extract_llm_provider(validation_results)

    return {
        "template_compliance_pct": template_compliance_pct,
        "content_completeness_pct": content_completeness_pct,
        "template_compliance": template_compliance_pct,
        "content_quality": content_completeness_pct,
        "citation_count": citation_count,
        "overall_score": overall_score,
        "missing_sections": _dedupe_preserve_order(missing_sections),
        "llm_provider_used": llm_provider_used,
        "required_sections": _flatten_aliases(requirements),
    }
