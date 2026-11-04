# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _state_path() -> Path:
    raw = getattr(settings, "SCIBERT_BENCHMARK_STATE_PATH", None)
    if raw and str(raw).strip():
        return Path(str(raw).strip())
    return Path("scibert_benchmark_state.json")


def get_scibert_gate_state() -> dict[str, Any]:
    min_f1 = float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85))
    path = _state_path()
    if not path.exists():
        return {"enabled": False, "reason": "benchmark_state_missing"}
    try:
        content = path.read_text()
        data = json.loads(content)
        if not isinstance(data, dict):
            return {"enabled": False, "reason": "benchmark_state_invalid"}
    except Exception:
        return {"enabled": False, "reason": "benchmark_state_invalid"}

    overall_f1 = float(data.get("overall_f1", 0.0))
    passed = bool(data.get("passed", False))
    result = dict(data)
    if overall_f1 >= min_f1 and passed:
        result["enabled"] = True
        result["reason"] = "benchmark_passed"
    else:
        result["enabled"] = False
        result["reason"] = "benchmark_below_threshold"
    return result


def should_enable_scibert() -> bool:
    if bool(getattr(settings, "USE_SCIBERT_CLASSIFICATION", False)):
        return True
    if not bool(getattr(settings, "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK", False)):
        return False
    state = get_scibert_gate_state()
    return bool(state.get("enabled", False))


def persist_scibert_benchmark_result(
    overall_f1: float,
    metrics: dict[str, Any] | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    min_f1 = float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85))
    passed = float(overall_f1) >= min_f1
    payload: dict[str, Any] = {
        "overall_f1": float(overall_f1),
        "passed": passed,
        "source": source,
        "metrics": metrics or {},
        "validated_at": datetime.now(UTC).isoformat(),
    }
    path = _state_path()
    path.write_text(json.dumps(payload, indent=2))
    return payload


__all__ = [
    "_state_path",
    "get_scibert_gate_state",
    "persist_scibert_benchmark_result",
    "should_enable_scibert",
]
