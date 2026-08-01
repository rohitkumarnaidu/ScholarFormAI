# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Shared serialization helpers for backend pipeline payloads.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from datetime import time as time_type
from enum import Enum
from typing import Any


def sanitize_for_json(value: Any) -> Any:
    """Recursively sanitize values so they are JSON-serializable."""
    if isinstance(value, dict):
        return {str(key): sanitize_for_json(val) for key, val in value.items()}
    if isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, set):
        return [sanitize_for_json(item) for item in sorted(value, key=str)]
    if isinstance(value, bytes):
        preview = base64.b64encode(value[:16]).decode("ascii") if value else ""
        return {
            "encoding": "binary",
            "size_bytes": len(value),
            "omitted": True,
            "preview_b64": preview,
        }
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time_type)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def safe_model_dump(model_obj: Any) -> dict[str, Any]:
    """
    Dump a model-like object to a JSON-safe dict.
    Supports Pydantic v2 (`model_dump`) and v1 (`dict`) style payloads.
    """
    if model_obj is None:
        return {}

    try:
        if hasattr(model_obj, "model_dump"):
            try:
                return model_obj.model_dump(mode="json")
            except Exception:
                return sanitize_for_json(model_obj.model_dump(mode="python"))

        if hasattr(model_obj, "dict"):
            return sanitize_for_json(model_obj.dict())

        if isinstance(model_obj, dict):
            return sanitize_for_json(model_obj)
    except Exception:
        pass  # intentionally ignored

    sanitized = sanitize_for_json(model_obj)
    if isinstance(sanitized, dict):
        return sanitized
    return {"value": sanitized}


def _normalize_block_type(block_type: Any) -> str:
    raw_value = getattr(block_type, "value", block_type)
    return str(raw_value)


def build_structured_data(doc_obj: Any, partial: bool = False) -> dict[str, Any]:
    """
    Build the structured_data payload used by persistence and edit/review flows.
    """
    sections: dict[str, list[Any]] = {}
    blocks_payload: list[dict[str, Any]] = []
    headings_payload: list[dict[str, Any]] = []

    for block in getattr(doc_obj, "blocks", []) or []:
        block_type = getattr(block, "block_type", None)
        if not block_type:
            continue

        section_key = _normalize_block_type(block_type)
        sections.setdefault(section_key, []).append(getattr(block, "text", None))
        block_payload = safe_model_dump(block)
        blocks_payload.append(block_payload)

        if str(section_key).startswith("heading_") or section_key in {
            "abstract_heading",
            "keywords_heading",
            "references_heading",
        }:
            level = getattr(block, "level", None)
            if level is None and isinstance(getattr(block, "metadata", None), dict):
                level = block.metadata.get("heading_level")
            headings_payload.append(
                {
                    "text": getattr(block, "text", None),
                    "level": level,
                    "section_name": getattr(block, "section_name", None),
                    "block_type": section_key,
                }
            )

    payload: dict[str, Any] = {
        "sections": sections,
        "blocks": blocks_payload,
        "headings": headings_payload,
        "metadata": safe_model_dump(getattr(doc_obj, "metadata", None)),
        "references": [safe_model_dump(ref) for ref in getattr(doc_obj, "references", []) or []],
        "history": [safe_model_dump(stage) for stage in getattr(doc_obj, "processing_history", []) or []],
    }
    if partial:
        payload["partial"] = True
    return payload
