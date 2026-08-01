# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.pipeline]


FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "contracts")


class TestContractLoader:
    def test_init_default_contracts_dir(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader()
        assert loader.contracts_dir == "app/templates"

    def test_init_custom_dir(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir="/custom/path")
        assert loader.contracts_dir == "/custom/path"
        assert loader._cache == {}

    def test_load_cached(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        c1 = loader.load("none")
        c2 = loader.load("none")
        assert c1 is c2

    def test_load_from_cache_key_lowercased(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        c1 = loader.load("NONE")
        c2 = loader.load("none")
        assert c1 is c2

    def test_load_fallback_to_none(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = loader.load("nonexistent_style")
        assert contract is not None

    def test_load_fallback_none_not_found(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=os.path.join(FIXTURES_DIR, "nonexistent"))
        with pytest.raises(FileNotFoundError):
            loader.load("anything")

    def test_load_yaml_read_error(self, tmp_path):
        from app.pipeline.contracts.loader import ContractLoader
        contract_dir = tmp_path / "bad"
        contract_dir.mkdir()
        (contract_dir / "contract.yaml").write_text("{bad: yaml: unclosed")
        loader = ContractLoader(contracts_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="Failed to load contract"):
            loader.load("bad")

    def test_normalize_contract_non_dict(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        result = loader._normalize_contract("not_a_dict", "/fake/path")
        assert result == {}

    def test_normalize_contract_adds_publisher(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = {"layout": {"spacing": 1.0}}
        result = loader._normalize_contract(contract, os.path.join(FIXTURES_DIR, "ieee", "contract.yaml"))
        assert result["publisher"] == "ieee"

    def test_normalize_contract_extracts_spacing(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader()
        contract = {"layout": {"spacing": 2.0}}
        result = loader._normalize_contract(contract, "/fake/path")
        assert result["spacing"] == 2.0

    def test_normalize_contract_preserves_existing_publisher(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        contract = {"publisher": "custom"}
        result = loader._normalize_contract(contract, "/fake/path")
        assert result["publisher"] == "custom"

    def test_normalize_contract_no_layout(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader()
        contract = {"spacing": 1.5}
        result = loader._normalize_contract(contract, "/fake/path")
        assert result.get("spacing") == 1.5

    def test_normalize_contract_layout_no_spacing(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader()
        contract = {"layout": {"font": "serif"}}
        result = loader._normalize_contract(contract, "/fake/path")
        assert "spacing" not in result
        assert result["layout"]["font"] == "serif"

    def test_get_canonical_name(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        name = loader.get_canonical_name("none", "intro")
        assert name == "introduction"

    def test_get_canonical_name_fallback(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        name = loader.get_canonical_name("none", "unknown_section")
        assert name == "unknown_section"

    def test_is_required_true(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        assert loader.is_required("none", "abstract") is True

    def test_is_required_false(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        assert loader.is_required("none", "acknowledgments") is False

    def test_is_required_case_insensitive(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        assert loader.is_required("none", "ABSTRACT") is True

    def test_load_contract_convenience(self):
        from app.pipeline.contracts.loader import _default_pipeline_loader, load_contract
        original_dir = _default_pipeline_loader.contracts_dir
        _default_pipeline_loader.contracts_dir = FIXTURES_DIR
        try:
            contract = load_contract("none")
            assert contract is not None
        finally:
            _default_pipeline_loader.contracts_dir = original_dir

    def test_load_contract_convenience_cache(self):
        from app.pipeline.contracts.loader import _default_pipeline_loader, load_contract
        original_dir = _default_pipeline_loader.contracts_dir
        _default_pipeline_loader.contracts_dir = FIXTURES_DIR
        try:
            c1 = load_contract("none")
            c2 = load_contract("none")
            assert c1 is c2
        finally:
            _default_pipeline_loader.contracts_dir = original_dir

    def test_load_contract_yaml_empty(self, tmp_path):
        from app.pipeline.contracts.loader import ContractLoader
        contract_dir = tmp_path / "empty"
        contract_dir.mkdir()
        (contract_dir / "contract.yaml").write_text("")
        loader = ContractLoader(contracts_dir=str(tmp_path))
        contract = loader.load("empty")
        assert isinstance(contract, dict)

    def test_get_canonical_name_uses_loaded_contract(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        with patch.object(loader, "load", return_value={"sections": {"canonical_names": {"intro": "introduction"}}}):
            name = loader.get_canonical_name("any", "intro")
            assert name == "introduction"

    def test_is_required_uses_loaded_contract(self):
        from app.pipeline.contracts.loader import ContractLoader
        loader = ContractLoader(contracts_dir=FIXTURES_DIR)
        with patch.object(loader, "load", return_value={"sections": {"required": ["abstract"]}}):
            assert loader.is_required("any", "abstract") is True
