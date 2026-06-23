# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

# -*- coding: utf-8 -*-
"""
ContentParser -- converts raw LLM response string into List[Block].

Handles:
  - JSON wrapped in markdown code fences (```json ... ```)
  - Plain JSON arrays
  - Partial / malformed responses (raises ValueError with clear message)
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Allowlist of all valid block types the generator can produce
VALID_BLOCK_TYPES = {
    "TITLE", "AUTHOR_INFO", "AFFILIATION", "ABSTRACT", "KEYWORDS",
    "SUMMARY", "CONTACT_INFO",
    "HEADING_1", "HEADING_2", "HEADING_3",
    "BODY", "BULLET", "BULLET_LIST",
    "FIGURE_CAPTION", "TABLE_CAPTION",
    "REFERENCE_ENTRY", "METHODOLOGY", "CONCLUSION",
}

# Map any LLM variants onto canonical names
TYPE_ALIASES: dict[str, str] = {
    "H1": "HEADING_1", "H2": "HEADING_2", "H3": "HEADING_3",
    "PARAGRAPH": "BODY", "TEXT": "BODY", "CONTENT": "BODY",
    "LIST_ITEM": "BULLET", "BULLET_POINT": "BULLET",
    "REF": "REFERENCE_ENTRY", "REFERENCE": "REFERENCE_ENTRY",
    "AUTHOR": "AUTHOR_INFO", "AUTHORS": "AUTHOR_INFO",
    "AFFILIATION_INFO": "AFFILIATION",
    "CONTACT": "CONTACT_INFO",
}


class ContentParser:
    """
    Parses the raw LLM string response into a list of plain dicts
    that can be fed into the formatter.

    Each output dict has keys: type, content, level, metadata.
    """

    def parse(self, llm_response: str, doc_type: str) -> list[dict[str, Any]]:
        """
        Parse LLM response string into block dicts.

        Args:
            llm_response: Raw string from the LLM (may contain code fences).
            doc_type:     The generation type (for logging/context only).

        Returns:
            List of block dicts.

        Raises:
            ValueError: If the response cannot be parsed as valid block JSON.
        """
        json_str = self._extract_json(llm_response)
        raw_list = self._load_json(json_str)
        blocks   = [self._normalise(raw, idx) for idx, raw in enumerate(raw_list)]
        logger.info("ContentParser: parsed %d blocks for doc_type='%s'", len(blocks), doc_type)
        return blocks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> str:
        """Remove markdown code fences and return the raw JSON string."""
        text = text.strip()

        # Case 1: ```json ... ```
        if "```json" in text:
            start = text.index("```json") + len("```json")
            end   = text.index("```", start)
            return text[start:end].strip()

        # Case 2: ``` ... ```
        if text.startswith("```"):
            start = text.index("```") + 3
            # Skip optional language tag on same line
            nl = text.index("\n", start)
            end = text.rindex("```")
            return text[nl:end].strip()

        # Case 3: plain JSON (starts with '[')
        if text.startswith("["):
            return text

        # Case 4: try to find '[' anywhere
        bracket = text.find("[")
        if bracket != -1:
            return text[bracket:]

        raise ValueError(
            "LLM response does not contain a JSON array. "
            f"Response preview: {text[:200]!r}"
        )

    @staticmethod
    def _load_json(json_str: str) -> list[dict]:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from LLM: {exc}. Preview: {json_str[:300]!r}") from exc

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array, got {type(data).__name__}. "
                f"Preview: {json_str[:200]!r}"
            )
        return data

    @classmethod
    def _normalise(cls, raw: dict, idx: int) -> dict[str, Any]:
        """Normalise one raw block dict into the canonical schema."""
        if not isinstance(raw, dict):
            logger.warning("Block %d is not a dict (%s) — using empty BODY", idx, type(raw))
            raw = {"type": "BODY", "content": str(raw)}

        raw_type = str(raw.get("type", "BODY")).upper().strip()
        block_type = TYPE_ALIASES.get(raw_type, raw_type)
        if block_type not in VALID_BLOCK_TYPES:
            logger.warning("Unknown block type '%s' at index %d — falling back to BODY", block_type, idx)
            block_type = "BODY"

        content = str(raw.get("content", "")).strip()
        level   = int(raw.get("level", 0))

        return {
            "type":     block_type,
            "content":  content,
            "level":    level,
            "metadata": raw.get("metadata", {}),
        }
