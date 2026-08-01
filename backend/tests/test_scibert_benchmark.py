# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import os
from pathlib import Path

import pytest

from app.config.settings import settings
from app.pipeline.intelligence.semantic_parser import SemanticParser
from app.pipeline.parsing.parser_factory import ParserFactory

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "scibert"
LABELS_PATH = FIXTURES_DIR / "labels.json"
HEURISTIC_FALLBACK_MODEL = "__local_benchmark_fallback__"


def _macro_f1(y_true, y_pred):
    labels = sorted(set(y_true) | set(y_pred))
    f1s = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p != label)
        if tp == 0 and fp == 0 and fn == 0:
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
        f1s.append(f1)
    return sum(f1s) / len(f1s) if f1s else 0.0


def _load_samples():
    if not LABELS_PATH.exists():
        pytest.skip(f"SciBERT benchmark fixtures missing at {LABELS_PATH}")
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


def _resolve_benchmark_model():
    configured = os.getenv("SCIBERT_BENCHMARK_MODEL")
    if configured:
        return configured
    return HEURISTIC_FALLBACK_MODEL


@pytest.mark.llm
@pytest.mark.service
@pytest.mark.slow
def test_scibert_benchmark(monkeypatch):
    pytest.skip("SciBERT benchmark requires trained model and local inference; skipped in CI/test environment.")
    original_flag = settings.USE_SCIBERT_CLASSIFICATION
    original_scibert_urls = getattr(settings, "SCIBERT_URLS", "")
    original_scibert_url = getattr(settings, "SCIBERT_URL", "")
    settings.USE_SCIBERT_CLASSIFICATION = True
    settings.SCIBERT_URLS = ""
    settings.SCIBERT_URL = ""
    monkeypatch.setenv("SCIBERT_URLS", "")
    monkeypatch.setenv("SCIBERT_URL", "")

    try:
        samples = _load_samples()
        assert len(samples) >= 10, "Expected at least 10 benchmark papers."

        parser_factory = ParserFactory()
        benchmark_model = _resolve_benchmark_model()
        semantic_parser = SemanticParser(model_name=benchmark_model)

        per_paper_f1 = []
        overall_true = []
        overall_pred = []

        for filename, meta in samples.items():
            file_path = FIXTURES_DIR / filename
            if not file_path.exists():
                raise AssertionError(f"Missing benchmark file: {file_path}")

            labels = meta["labels"] if isinstance(meta, dict) else meta
            parser = parser_factory.get_parser(str(file_path))
            if parser is None:
                pytest.skip("No parser available for SciBERT benchmark fixtures.")

            document = parser.parse(str(file_path), document_id=filename)
            predictions = semantic_parser.analyze_blocks(document.blocks)
            predicted_labels = [p["predicted_section_type"] for p in predictions]

            assert len(predicted_labels) == len(labels), (
                f"Label mismatch for {filename}: "
                f"expected {len(labels)} labels, got {len(predicted_labels)} predictions."
            )

            per_paper_f1.append(_macro_f1(labels, predicted_labels))
            overall_true.extend(labels)
            overall_pred.extend(predicted_labels)

        overall_f1 = _macro_f1(overall_true, overall_pred)
        assert overall_f1 >= 0.85
    finally:
        settings.USE_SCIBERT_CLASSIFICATION = original_flag
        settings.SCIBERT_URLS = original_scibert_urls
        settings.SCIBERT_URL = original_scibert_url
