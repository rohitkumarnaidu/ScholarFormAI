import pytest
from unittest.mock import MagicMock, patch, mock_open


class TestStatePath:
    def test_uses_configured_path(self):
        from app.services.scibert_gate import _state_path
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_BENCHMARK_STATE_PATH = "scibert_state.json"
            path = _state_path()
        assert str(path).endswith("scibert_state.json")

    def test_default_path(self):
        from app.services.scibert_gate import _state_path, BACKEND_ROOT
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_BENCHMARK_STATE_PATH = ""
            path = _state_path()
            assert "scibert_benchmark_state.json" in str(path)


class TestGetScibertGateState:
    def test_missing_file_disabled(self):
        from app.services.scibert_gate import get_scibert_gate_state
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_MIN_BENCHMARK_F1 = 0.85
            with patch("pathlib.Path.exists", return_value=False):
                state = get_scibert_gate_state()
        assert state["enabled"] is False
        assert state["reason"] == "benchmark_state_missing"

    def test_invalid_json_disabled(self):
        from app.services.scibert_gate import get_scibert_gate_state
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_MIN_BENCHMARK_F1 = 0.85
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value="invalid json"):
                    state = get_scibert_gate_state()
        assert state["enabled"] is False
        assert state["reason"] == "benchmark_state_invalid"

    def test_passed_gate_enabled(self):
        from app.services.scibert_gate import get_scibert_gate_state
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_MIN_BENCHMARK_F1 = 0.85
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value='{"overall_f1": 0.92, "passed": true, "validated_at": "2026-01-01"}'):
                    state = get_scibert_gate_state()
        assert state["enabled"] is True
        assert state["reason"] == "benchmark_passed"
        assert state["overall_f1"] == 0.92

    def test_below_threshold_disabled(self):
        from app.services.scibert_gate import get_scibert_gate_state
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_MIN_BENCHMARK_F1 = 0.85
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value='{"overall_f1": 0.50, "passed": true, "validated_at": "2026-01-01"}'):
                    state = get_scibert_gate_state()
        assert state["enabled"] is False
        assert state["reason"] == "benchmark_below_threshold"


class TestShouldEnableScibert:
    def test_explicit_override_enables(self):
        from app.services.scibert_gate import should_enable_scibert
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.USE_SCIBERT_CLASSIFICATION = True
            mock_s.SCIBERT_AUTO_ENABLE_FROM_BENCHMARK = True
            assert should_enable_scibert() is True

    def test_auto_enable_disabled_returns_false(self):
        from app.services.scibert_gate import should_enable_scibert
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.USE_SCIBERT_CLASSIFICATION = False
            mock_s.SCIBERT_AUTO_ENABLE_FROM_BENCHMARK = False
            assert should_enable_scibert() is False

    def test_delegates_to_gate_state(self):
        from app.services.scibert_gate import should_enable_scibert
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.USE_SCIBERT_CLASSIFICATION = False
            mock_s.SCIBERT_AUTO_ENABLE_FROM_BENCHMARK = True
            with patch("app.services.scibert_gate.get_scibert_gate_state", return_value={"enabled": True}):
                assert should_enable_scibert() is True


class TestPersistScibertBenchmark:
    def test_saves_payload(self):
        from app.services.scibert_gate import persist_scibert_benchmark_result
        with patch("app.services.scibert_gate.settings") as mock_s:
            mock_s.SCIBERT_MIN_BENCHMARK_F1 = 0.85
            with patch("pathlib.Path.write_text") as mock_write:
                result = persist_scibert_benchmark_result(0.92)
        assert result["passed"] is True
        assert result["overall_f1"] == 0.92
        assert result["source"] == "manual"
        mock_write.assert_called_once()
