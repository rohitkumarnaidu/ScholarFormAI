# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app.config.settings import BACKEND_ROOT, settings

logger = logging.getLogger(__name__)


def _state_path() -> Path:
    configured = str(getattr(settings, "SCIBERT_BENCHMARK_STATE_PATH", "") or "").strip()
    if not configured:
        configured = ".metrics/scibert_benchmark_state.json"
    path = Path(configured)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


def get_scibert_gate_state() -> Dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {
            "enabled": False,
            "reason": "benchmark_state_missing",
            "overall_f1": 0.0,
            "threshold": float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85)),
            "validated_at": None,
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse SciBERT gate state at %s: %s", path, exc)
        return {
            "enabled": False,
            "reason": "benchmark_state_invalid",
            "overall_f1": 0.0,
            "threshold": float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85)),
            "validated_at": None,
        }

    threshold = float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85))
    overall_f1 = float(payload.get("overall_f1") or 0.0)
    passed = bool(payload.get("passed")) and overall_f1 >= threshold
    return {
        "enabled": passed,
        "reason": "benchmark_passed" if passed else "benchmark_below_threshold",
        "overall_f1": overall_f1,
        "threshold": threshold,
        "validated_at": payload.get("validated_at"),
    }


def should_enable_scibert() -> bool:
    # Explicit runtime override remains supported for dev/test.
    if bool(getattr(settings, "USE_SCIBERT_CLASSIFICATION", False)):
        return True

    if not bool(getattr(settings, "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK", True)):
        return False

    return bool(get_scibert_gate_state().get("enabled"))


def persist_scibert_benchmark_result(overall_f1: float, *, source: str = "manual") -> Dict[str, Any]:
    threshold = float(getattr(settings, "SCIBERT_MIN_BENCHMARK_F1", 0.85))
    payload = {
        "overall_f1": float(overall_f1),
        "passed": float(overall_f1) >= threshold,
        "threshold": threshold,
        "source": source,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }

    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload
