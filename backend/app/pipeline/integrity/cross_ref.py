# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Cross-Reference Integrity Engine - Validates internal document links.
Scans for Fig, Table, Eq, and Section references.
"""

import re
from typing import List, Dict, Any, Set
from app.models import PipelineDocument as Document, BlockType


class CrossReferenceEngine:
    """
    Scans document text for internal references and validates integrity.
    """

    def __init__(self):
        # Patterns for common academic cross-references
        self.fig_pattern = re.compile(r"\b(Figure|Fig\.)\s*(?P<num>\d+)\b", re.IGNORECASE)
        self.tbl_pattern = re.compile(r"\b(Table)\s*(?P<num>\d+)\b", re.IGNORECASE)
        self.eq_pattern = re.compile(r"\b(Equation|Eq\.)\s*\((?P<num>\d+)\)", re.IGNORECASE)
        self.sect_pattern = re.compile(r"\b(Section|Sect\.)\s*(?P<id>[I|V|X|L|C]+|\d+)\b", re.IGNORECASE)

    def validate_integrity(self, document: Document) -> List[str]:
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
        sections = {b.section_name.lower() for b in document.blocks if b.section_name}

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
