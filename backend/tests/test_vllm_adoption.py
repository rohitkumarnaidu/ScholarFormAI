# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from app.services import vllm_adoption


def test_vllm_adoption_report_marks_ready_when_threshold_met(monkeypatch):
    monkeypatch.setattr(vllm_adoption.settings, "VLLM_ADOPTION_ENABLED", True, raising=False)
    monkeypatch.setattr(vllm_adoption.settings, "VLLM_REQUESTS_PER_HOUR_THRESHOLD", 1000, raising=False)
    monkeypatch.setattr(vllm_adoption.settings, "VLLM_DAILY_TOKENS_THRESHOLD", 1_000_000, raising=False)
    monkeypatch.setattr(vllm_adoption, "get_llm_requests_total", lambda: 1500.0)
    monkeypatch.setattr(vllm_adoption, "get_llm_tokens_total", lambda: 500_000.0)

    report = vllm_adoption.build_vllm_adoption_report()
    assert report["traffic"]["traffic_justifies_phase4"] is True
    assert report["phase4_plan"]["status"] == "ready"


def test_vllm_adoption_report_holds_when_threshold_not_met(monkeypatch):
    monkeypatch.setattr(vllm_adoption.settings, "VLLM_REQUESTS_PER_HOUR_THRESHOLD", 2000, raising=False)
    monkeypatch.setattr(vllm_adoption.settings, "VLLM_DAILY_TOKENS_THRESHOLD", 5_000_000, raising=False)
    monkeypatch.setattr(vllm_adoption, "get_llm_requests_total", lambda: 1200.0)
    monkeypatch.setattr(vllm_adoption, "get_llm_tokens_total", lambda: 2_000_000.0)

    report = vllm_adoption.build_vllm_adoption_report()
    assert report["traffic"]["traffic_justifies_phase4"] is False
    assert report["phase4_plan"]["status"] == "hold"
