# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os

import pytest

from app.pipeline.contracts.loader import ContractLoader, load_contract

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "contracts")


class TestContractLoader:
    def test_load_existing_contract(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = loader.load("none")
        assert isinstance(contract, dict)
        assert contract.get("publisher") == "none"

    def test_load_caches_result(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        c1 = loader.load("none")
        c2 = loader.load("none")
        assert c1 is c2

    def test_load_fallback_to_none(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = loader.load("nonexistent_style")
        assert contract is not None
        assert "publisher" in contract

    def test_load_missing_fallback_raises(self):
        loader = ContractLoader(contracts_dir=os.path.join(FIXTURES_DIR, "nonexistent"))
        with pytest.raises(FileNotFoundError):
            loader.load("anything")

    def test_normalize_non_dict(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        result = loader._normalize_contract("not_a_dict", "/fake/path")
        assert result == {}

    def test_normalize_adds_publisher(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = {"layout": {"spacing": 1.0}}
        result = loader._normalize_contract(contract, os.path.join(FIXTURES_DIR, "ieee", "contract.yaml"))
        assert result["publisher"] == "ieee"

    def test_normalize_extracts_spacing(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = {"layout": {"spacing": 2.0}}
        result = loader._normalize_contract(contract, "/fake/path")
        assert result["spacing"] == 2.0

    def test_get_canonical_name(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        name = loader.get_canonical_name("none", "intro")
        assert name == "introduction"

    def test_get_canonical_name_fallback(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        name = loader.get_canonical_name("none", "unknown_section")
        assert name == "unknown_section"

    def test_is_required_true(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        assert loader.is_required("none", "abstract") is True

    def test_is_required_false(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        assert loader.is_required("none", "acknowledgments") is False

    def test_load_contract_convenience(self):
        with pytest.MonkeyPatch.context():
            import app.pipeline.contracts.loader as cl
            original = cl._default_pipeline_loader.contracts_dir
            cl._default_pipeline_loader.contracts_dir = FIXTURES_DIR
            try:
                contract = load_contract("none")
                assert contract is not None
            finally:
                cl._default_pipeline_loader.contracts_dir = original


class TestContractLoaderEdgeCases:
    def test_load_corrupt_yaml(self, tmp_path):
        contract_dir = tmp_path / "bad"
        contract_dir.mkdir()
        (contract_dir / "contract.yaml").write_text("{bad: yaml: unclosed")
        loader = ContractLoader(contracts_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="Failed to load contract"):
            loader.load("bad")

    def test_normalize_preserves_existing_publisher(self):
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = {"publisher": "custom"}
        result = loader._normalize_contract(contract, "/fake/path")
        assert result["publisher"] == "custom"
