# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
import os
import tempfile
import yaml
from app.pipeline.contracts.loader import ContractLoader


@pytest.fixture
def temp_contracts(tmp_path):
    """Create a temporary contracts directory with test contract."""
    ieee_dir = tmp_path / "ieee"
    ieee_dir.mkdir(parents=True)
    contract = {
        "layout": {"spacing": 1.5},
        "sections": {"required": ["abstract", "references"]},
    }
    with open(ieee_dir / "contract.yaml", "w") as f:
        yaml.dump(contract, f)
    return str(tmp_path)


@pytest.fixture
def loader(temp_contracts):
    return ContractLoader(contracts_dir=temp_contracts)


class TestContractLoader:
    def test_load_existing(self, loader):
        contract = loader.load("ieee")
        assert contract["publisher"] == "ieee"
        assert contract["layout"]["spacing"] == 1.5

    def test_load_caching(self, loader, temp_contracts):
        c1 = loader.load("ieee")
        c2 = loader.load("ieee")
        assert c1 is c2

    def test_load_fallback_to_none(self, loader, temp_contracts):
        none_dir = os.path.join(temp_contracts, "none")
        os.makedirs(none_dir, exist_ok=True)
        with open(os.path.join(none_dir, "contract.yaml"), "w") as f:
            yaml.dump({"publisher": "none", "sections": {}}, f)
        contract = loader.load("nonexistent_publisher")
        assert contract["publisher"] == "none"

    def test_load_no_fallback_raises(self):
        loader = ContractLoader(contracts_dir="__nonexistent__")
        with pytest.raises(FileNotFoundError):
            loader.load("anything")

    def test_normalize_adds_publisher(self, loader, temp_contracts):
        """Legacy callers expect a top-level publisher field."""
        contract = loader.load("ieee")
        assert "publisher" in contract

    def test_normalize_adds_spacing(self, loader, temp_contracts):
        """Legacy callers expect top-level spacing from layout."""
        contract = loader.load("ieee")
        assert "spacing" in contract

    def test_normalize_non_dict_returns_empty(self):
        loader = ContractLoader(contracts_dir="__nonexistent__")
        result = loader._normalize_contract([], "/fake/path")
        assert result == {}

    def test_get_canonical_name(self, loader, temp_contracts):
        name = loader.get_canonical_name("ieee", "Introduction")
        assert name == "introduction"

    def test_is_required_true(self, loader, temp_contracts):
        assert loader.is_required("ieee", "abstract") is True

    def test_is_required_false(self, loader, temp_contracts):
        assert loader.is_required("ieee", "introduction") is False


class TestLoadContractConvenience:
    def test_load_contract_convenience(self):
        from app.pipeline.contracts.loader import load_contract
        contract = load_contract("ieee")
        assert isinstance(contract, dict)
