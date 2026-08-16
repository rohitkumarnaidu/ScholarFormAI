from unittest.mock import mock_open, patch

import pytest


class TestContractLoader:
    def test_load_caches_contract(self):
        with patch("app.pipeline.contracts.loader.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="key: value")):
                from app.pipeline.contracts.loader import ContractLoader

                cl = ContractLoader(contracts_dir="/fake")
                result = cl.load("ieee")
                assert result["key"] == "value"
                result2 = cl.load("ieee")
                assert result2 is result

    def test_load_falls_back_to_none(self):
        def exists_side(path):
            return "none" in path

        with patch("app.pipeline.contracts.loader.os.path.exists", side_effect=exists_side):
            with patch("builtins.open", mock_open(read_data="fallback: ok")):
                from app.pipeline.contracts.loader import ContractLoader

                cl = ContractLoader(contracts_dir="/fake")
                result = cl.load("unknown")
                assert result["fallback"] == "ok"

    def test_load_raises_when_no_fallback(self):
        with patch("app.pipeline.contracts.loader.os.path.exists", return_value=False):
            from app.pipeline.contracts.loader import ContractLoader

            cl = ContractLoader(contracts_dir="/fake")
            with pytest.raises(FileNotFoundError):
                cl.load("unknown")

    def test_load_with_empty_yaml(self):
        with patch("app.pipeline.contracts.loader.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="")):
                from app.pipeline.contracts.loader import ContractLoader

                cl = ContractLoader(contracts_dir="/fake")
                result = cl.load("ieee")
                assert "publisher" in result
                assert result.get("publisher") == "ieee"

    def test_load_yaml_error_raises_runtime_error(self):
        with patch("app.pipeline.contracts.loader.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=":")):
                from app.pipeline.contracts.loader import ContractLoader

                cl = ContractLoader(contracts_dir="/fake")
                with pytest.raises(RuntimeError):
                    cl.load("ieee")

    def test_load_lowercases_name(self):
        with patch("app.pipeline.contracts.loader.os.path.exists", return_value=True) as m_exists:
            with patch("builtins.open", mock_open(read_data="key: val")):
                from app.pipeline.contracts.loader import ContractLoader

                cl = ContractLoader(contracts_dir="/fake")
                cl.load("IEEE")
                call_path = m_exists.call_args[0][0]
                assert "ieee" in call_path.lower()

    def test_normalize_adds_spacing_from_layout(self):
        from app.pipeline.contracts.loader import ContractLoader

        cl = ContractLoader(contracts_dir="/fake")
        contract = {"layout": {"spacing": 2.0}}
        result = cl._normalize_contract(contract, "/fake/ieee/contract.yaml")
        assert result["spacing"] == 2.0

    def test_normalize_adds_publisher(self):
        from app.pipeline.contracts.loader import ContractLoader

        cl = ContractLoader(contracts_dir="/fake")
        result = cl._normalize_contract({}, "/fake/ieee/contract.yaml")
        assert result["publisher"] == "ieee"

    def test_get_canonical_name(self):
        with patch("app.pipeline.contracts.loader.ContractLoader.load") as mock_load:
            mock_load.return_value = {"sections": {"canonical_names": {"intro": "introduction"}}}
            from app.pipeline.contracts.loader import ContractLoader

            cl = ContractLoader(contracts_dir="/fake")
            assert cl.get_canonical_name("ieee", "Intro") == "introduction"

    def test_is_required(self):
        with patch("app.pipeline.contracts.loader.ContractLoader.load") as mock_load:
            mock_load.return_value = {"sections": {"required": ["abstract", "references"]}}
            from app.pipeline.contracts.loader import ContractLoader

            cl = ContractLoader(contracts_dir="/fake")
            assert cl.is_required("ieee", "Abstract") is True
            assert cl.is_required("ieee", "Acknowledgments") is False


class TestLoadContract:
    def test_convenience_loader(self):
        with patch("app.pipeline.contracts.loader._default_pipeline_loader.load") as mock_load:
            mock_load.return_value = {"key": "val"}
            from app.pipeline.contracts.loader import load_contract

            result = load_contract("ieee")
            assert result["key"] == "val"
