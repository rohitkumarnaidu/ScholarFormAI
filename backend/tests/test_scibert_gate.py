# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from app.services import scibert_gate


def test_scibert_gate_auto_enable_from_benchmark_state(tmp_path, monkeypatch):
    state_path = tmp_path / "scibert_state.json"
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_BENCHMARK_STATE_PATH", str(state_path), raising=False)
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85, raising=False)
    monkeypatch.setattr(scibert_gate.settings, "USE_SCIBERT_CLASSIFICATION", False, raising=False)
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK", True, raising=False)

    payload = scibert_gate.persist_scibert_benchmark_result(0.87, source="unit-test")
    gate_state = scibert_gate.get_scibert_gate_state()

    assert payload["passed"] is True
    assert gate_state["enabled"] is True
    assert scibert_gate.should_enable_scibert() is True


def test_scibert_gate_stays_disabled_below_threshold(tmp_path, monkeypatch):
    state_path = tmp_path / "scibert_state.json"
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_BENCHMARK_STATE_PATH", str(state_path), raising=False)
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_MIN_BENCHMARK_F1", 0.9, raising=False)
    monkeypatch.setattr(scibert_gate.settings, "USE_SCIBERT_CLASSIFICATION", False, raising=False)
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK", True, raising=False)

    scibert_gate.persist_scibert_benchmark_result(0.88, source="unit-test")
    gate_state = scibert_gate.get_scibert_gate_state()

    assert gate_state["enabled"] is False
    assert scibert_gate.should_enable_scibert() is False


def test_scibert_gate_honors_manual_override(monkeypatch):
    monkeypatch.setattr(scibert_gate.settings, "USE_SCIBERT_CLASSIFICATION", True, raising=False)
    monkeypatch.setattr(scibert_gate.settings, "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK", False, raising=False)
    assert scibert_gate.should_enable_scibert() is True
