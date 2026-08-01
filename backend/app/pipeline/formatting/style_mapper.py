# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import Block
from app.pipeline.contracts.loader import ContractLoader


class StyleMapper:
    """
    Maps semantic block labels to Word-compatible style names.
    Driven by contract.yaml.
    """

    def __init__(self, contract_loader: ContractLoader):
        self.contract_loader = contract_loader

    def get_style_name(self, block: Block, publisher: str) -> str:
        """
        Determine the Word style name for a block based on its type.
        """
        contract = self.contract_loader.load(publisher)
        style_map = contract.get("styles", {})

        # Standardize key (e.g. "heading_1" -> "BLOCK_HEADING_1")
        bt = str(block.block_type).upper()
        if bt.startswith("BLOCK_"):
            key = bt
        else:
            key = f"BLOCK_{bt}"

        return style_map.get(key, "Normal")
