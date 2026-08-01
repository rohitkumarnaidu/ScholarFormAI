# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import os
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ContractLoader:
    """
    Loads and provides access to template contracts.
    """

    def __init__(self, contracts_dir: str = "app/templates"):
        self.contracts_dir = contracts_dir
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, name: str) -> dict[str, Any]:
        """
        Load a contract by name (e.g., 'ieee').
        """
        name = name.lower()
        if name in self._cache:
            return self._cache[name]

        contract_path = os.path.join(self.contracts_dir, name, "contract.yaml")
        if not os.path.exists(contract_path):
            logger.warning("Contract not found for '%s', falling back to 'none'", name)
            contract_path = os.path.join(self.contracts_dir, "none", "contract.yaml")
            if not os.path.exists(contract_path):
                raise FileNotFoundError(f"Fallback contract 'none' not found. Original requested: {name}")

        try:
            with open(contract_path) as f:
                contract = yaml.safe_load(f) or {}
                contract = self._normalize_contract(contract, contract_path)
                self._cache[name] = contract
                return contract
        except Exception as e:
            raise RuntimeError(f"Failed to load contract {name}: {e}")

    def _normalize_contract(self, contract: dict[str, Any], contract_path: str) -> dict[str, Any]:
        """
        Normalize contract shape for backward compatibility with legacy callers.
        """
        if not isinstance(contract, dict):
            return {}

        # Legacy callers expect top-level "spacing".
        layout = contract.get("layout")
        if isinstance(layout, dict) and "spacing" not in contract and "spacing" in layout:
            contract["spacing"] = layout["spacing"]

        # Legacy callers/tests may expect a top-level publisher/template identifier.
        if "publisher" not in contract:
            inferred_name = os.path.basename(os.path.dirname(contract_path))
            contract["publisher"] = inferred_name

        return contract

    def get_canonical_name(self, publisher: str, section_name: str) -> str:
        """
        Get canonical section name for a given publisher.
        """
        contract = self.load(publisher)
        canonical_map = contract.get("sections", {}).get("canonical_names", {})
        return canonical_map.get(section_name.lower(), section_name.lower())

    def is_required(self, publisher: str, section_name: str) -> bool:
        """
        Check if a section is required by the contract.
        """
        contract = self.load(publisher)
        required = contract.get("sections", {}).get("required", [])
        return section_name.lower() in [s.lower() for s in required]


_default_pipeline_loader = ContractLoader(contracts_dir="app/pipeline/contracts")


def load_contract(name: str) -> dict[str, Any]:
    """Convenience loader for call-sites that only need one contract by name."""
    return _default_pipeline_loader.load(name)
