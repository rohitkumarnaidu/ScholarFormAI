# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from typing import Dict, List, Optional
from app.models import PipelineDocument as Document, Block, BlockType
from app.pipeline.contracts.loader import ContractLoader

class NumberingEngine:
    """
    Enforces sequential numbering for headings, figures, and tables.
    Driven by numbering rules in contract.yaml.
    """
    def __init__(self, contract_loader: ContractLoader):
        self.contract_loader = contract_loader

    def apply_numbering(self, document: Document, publisher: str) -> Document:
        """
        Walk through the document and apply numbering to headings, figs, and tables.
        """
        contract = self.contract_loader.load(publisher)
        rules = contract.get("numbering", {})
        
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
            scope = eq_rules.get("scope", "global")
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
