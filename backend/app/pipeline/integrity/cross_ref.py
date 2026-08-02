from __future__ import annotations

import re
from typing import Any

from app.models import BlockType
from app.models import PipelineDocument as Document


class CrossReferenceEngine:
    """
    Scans document text for internal references and validates integrity.
    """

    def __init__(self, auto_resolve: bool = False):
        self.auto_resolve = auto_resolve
        # Patterns for common academic cross-references
        self.fig_pattern = re.compile(r"\b(?P<prefix>Figure|Fig\.)\s*(?P<num>[\d\.]+)\b", re.IGNORECASE)
        self.tbl_pattern = re.compile(r"\b(?P<prefix>Table)\s*(?P<num>[\d\.]+)\b", re.IGNORECASE)
        self.eq_pattern = re.compile(r"\b(?P<prefix>Equation|Eq\.)\s*\((?P<num>[\d\.]+)\)", re.IGNORECASE)
        self.sect_pattern = re.compile(r"\b(?P<prefix>Section|Sect\.)\s*(?P<id>[I|V|X|L|C]+|\d+)\b", re.IGNORECASE)

    def resolve_references(
        self,
        blocks: list[Any],
        equation_map: dict[int | str, str] | None = None,
        figure_map: dict[int | str, str] | None = None,
        table_map: dict[int | str, str] | None = None,
    ) -> list[Any]:
        """
        Resolve and rewrite cross-references in text blocks based on mapping tables.
        """
        eq_map = equation_map or {}
        fig_map = figure_map or {}
        tbl_map = table_map or {}

        for block in blocks:
            text = getattr(block, "text", "")
            if not text:
                continue

            if eq_map:
                def _replace_eq(m: re.Match) -> str:
                    prefix = m.group("prefix")
                    num_str = m.group("num")
                    val = None
                    try:
                        val = eq_map.get(int(num_str))
                    except ValueError:
                        pass
                    if val is None:
                        val = eq_map.get(num_str)
                    if val is not None:
                        clean_val = str(val).strip("()")
                        return f"{prefix} ({clean_val})"
                    return m.group(0)

                text = self.eq_pattern.sub(_replace_eq, text)

            if fig_map:
                def _replace_fig(m: re.Match) -> str:
                    prefix = m.group("prefix")
                    num_str = m.group("num")
                    val = None
                    try:
                        val = fig_map.get(int(num_str))
                    except ValueError:
                        pass
                    if val is None:
                        val = fig_map.get(num_str)
                    if val is not None:
                        return f"{prefix} {val}"
                    return m.group(0)

                text = self.fig_pattern.sub(_replace_fig, text)

            if tbl_map:
                def _replace_tbl(m: re.Match) -> str:
                    prefix = m.group("prefix")
                    num_str = m.group("num")
                    val = None
                    if "." in num_str:
                        val = tbl_map.get(num_str)
                        if val is None:
                            try:
                                val = tbl_map.get(int(num_str.split(".")[-1]))
                            except ValueError:
                                pass
                    else:
                        try:
                            val = tbl_map.get(int(num_str))
                        except ValueError:
                            pass
                    if val is None:
                        val = tbl_map.get(num_str)
                    if val is not None:
                        return f"{prefix} {val}"
                    return m.group(0)

                text = self.tbl_pattern.sub(_replace_tbl, text)

            block.text = text

        return blocks

    def validate_integrity(self, document: Document) -> list[str]:
        """
        Scan all body blocks and validate references against extracted items.
        Returns a list of violation messages.
        """
        violations = []

        # 1. Collect existing item numbers/IDs
        # Figures and Tables are 1-indexed based on sequential order
        fig_nums = {i + 1 for i in range(len(document.figures))}
        tbl_nums = {i + 1 for i in range(len(document.tables))}
        eq_nums = {i + 1 for i in range(len(document.equations))}

        # Sections (titles or canonical names)
        {b.section_name.lower() for b in document.blocks if b.section_name}

        # 2. Scan Text Blocks
        for block in document.blocks:
            if block.block_type not in {BlockType.BODY, BlockType.ABSTRACT_BODY}:
                continue

            text = block.text

            # Figures
            for match in self.fig_pattern.finditer(text):
                num = int(match.group("num"))
                if num not in fig_nums:
                    violations.append(
                        f"Dangling reference: '{match.group(0)}' in block {block.block_id}. Found {len(fig_nums)} figures."
                    )

            # Tables
            for match in self.tbl_pattern.finditer(text):
                num = int(match.group("num"))
                if num not in tbl_nums:
                    violations.append(
                        f"Dangling reference: '{match.group(0)}' in block {block.block_id}. Found {len(tbl_nums)} tables."
                    )

            # Equations
            for match in self.eq_pattern.finditer(text):
                num = int(match.group("num"))
                if num not in eq_nums:
                    violations.append(
                        f"Dangling reference: '{match.group(0)}' in block {block.block_id}. Found {len(eq_nums)} equations."
                    )

        return violations
