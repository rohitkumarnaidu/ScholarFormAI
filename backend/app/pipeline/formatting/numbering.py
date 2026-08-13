from __future__ import annotations

from typing import Any

from app.models import PipelineDocument as Document
from app.pipeline.contracts.loader import ContractLoader


class NumberingEngine:
    """
    Enforces sequential numbering for headings, figures, and tables.
    Driven by numbering rules in contract.yaml.
    """

    def __init__(self, contract_loader: ContractLoader | None = None, scope: str = "global"):
        self.contract_loader = contract_loader
        self.scope = scope

    def set_scope(self, scope: str) -> None:
        """Update numbering scope ('global' or 'per_section')."""
        self.scope = scope

    def number_equations(self, blocks: list[Any], scope: str | None = None) -> list[Any]:
        """
        Number equations in blocks list with scope support (global or per_section).
        """
        effective_scope = scope or self.scope
        current_section = 1
        eq_counter = 0

        for block in blocks:
            b_type = getattr(block, "block_type", "")
            b_type_str = b_type.lower() if isinstance(b_type, str) else getattr(b_type, "value", str(b_type)).lower()

            if "heading_1" in b_type_str or "section" in b_type_str:
                sn = getattr(block, "section_number", None)
                if isinstance(sn, int):
                    current_section = sn
                eq_counter = 0
            elif "equation" in b_type_str or b_type == "equation":
                sn = getattr(block, "section_number", None)
                if isinstance(sn, int):
                    current_section = sn
                eq_counter += 1
                if effective_scope == "per_section":
                    block.number = f"({current_section}.{eq_counter})"
                else:
                    block.number = f"({eq_counter})"

        return blocks

    def number_tables(self, blocks: list[Any], scope: str | None = None) -> list[Any]:
        """
        Number tables in blocks list with scope support (global or per_section).
        """
        effective_scope = scope or self.scope
        current_section = 1
        table_counter = 0

        for block in blocks:
            b_type = getattr(block, "block_type", "")
            b_type_str = b_type.lower() if isinstance(b_type, str) else getattr(b_type, "value", str(b_type)).lower()

            if "heading_1" in b_type_str or "section" in b_type_str:
                sn = getattr(block, "section_number", None)
                if isinstance(sn, int):
                    current_section = sn
                table_counter = 0
            elif "table" in b_type_str:
                table_counter += 1
                if effective_scope == "per_section":
                    block.number = f"Table {current_section}.{table_counter}"
                else:
                    block.number = f"Table {table_counter}"

        return blocks

    def apply_numbering(self, document: Document, publisher: str) -> Document:
        """
        Walk through the document and apply numbering to headings, figs, and tables.
        """
        contract = self.contract_loader.load(publisher) if self.contract_loader else {}
        contract.get("numbering", {})

        # Heading counters: level -> count
        counters = {1: 0, 2: 0, 3: 0, 4: 0}

        for block in document.blocks:
            if block.is_heading():
                level = block.level or 1
                # Increment current level
                counters[level] += 1
                # Reset lower levels
                for l in range(level + 1, 5):
                    counters[l] = 0

                # Format numbering string (simplified)
                num_str = ".".join([str(counters[l]) for l in range(1, level + 1)])
                block.metadata["number_string"] = num_str

                # Idempotency check: Don't double-number if already present
                prefix = f"{num_str} "
                if not block.text.startswith(prefix):
                    block.text = f"{prefix}{block.text}"

        # Figure and Table numbering
        for i, fig in enumerate(document.figures):
            fig.number = i + 1

        for i, tbl in enumerate(document.tables):
            tbl.number = i + 1

        # Equation Numbering
        eq_rules = contract.get("equations", {})
        if eq_rules:
            eq_rules.get("scope", "global")
            brackets = eq_rules.get("brackets", "()")

            # Simplified global numbering
            for i, eqn in enumerate(document.equations):
                num = i + 1
                if brackets == "()":
                    eqn.number = f"({num})"
                elif brackets == "[]":
                    eqn.number = f"[{num}]"
                else:
                    eqn.number = str(num)

        return document
