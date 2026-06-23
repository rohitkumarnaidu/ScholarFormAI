# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from app.pipeline.nlp import analyzer
from app.services.enhancement_manager import EnhancementProfile, enhancement_manager


def _profile(keyword_backends):
    return EnhancementProfile(
        enabled=True,
        queue_enabled=False,
        queue_provider="local",
        queue_available=False,
        ocr_enabled=False,
        ocr_backends=["builtin"],
        keyword_enabled=True,
        keyword_backends=list(keyword_backends),
    )


def test_keyllm_backend_extracts_keywords(monkeypatch):
    monkeypatch.setattr(enhancement_manager, "_profile", _profile(["keyllm", "basic"]), raising=False)
    monkeypatch.setattr(
        analyzer,
        "generate_with_fallback",
        lambda *args, **kwargs: {"text": '["quantum optics", "phase noise", "decoherence"]'},
    )

    keywords = analyzer.extract_keywords("Quantum optics discusses phase noise and decoherence.", top_k=3)
    assert keywords == ["quantum optics", "phase noise", "decoherence"]


def test_keyllm_backend_falls_back_to_basic_when_invalid_response(monkeypatch):
    monkeypatch.setattr(enhancement_manager, "_profile", _profile(["keyllm", "basic"]), raising=False)
    monkeypatch.setattr(
        analyzer,
        "generate_with_fallback",
        lambda *args, **kwargs: {"text": "not-json"},
    )

    keywords = analyzer.extract_keywords("Alpha beta alpha gamma beta alpha delta", top_k=2)
    assert keywords == ["alpha", "beta"]
