# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.config.settings import settings


def _counter_total(counter: Any, *, metric_name_suffix: str = "_total") -> float:
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith(metric_name_suffix):
                total += float(sample.value)
    return total


def get_llm_requests_total() -> float:
    from app.middleware.prometheus_metrics import LLM_REQUESTS_TOTAL

    return _counter_total(LLM_REQUESTS_TOTAL)


def get_llm_tokens_total() -> float:
    from app.middleware.prometheus_metrics import AGENT_LLM_TOKENS_TOTAL

    return _counter_total(AGENT_LLM_TOKENS_TOTAL)


def build_vllm_adoption_report() -> Dict[str, Any]:
    requests_total = get_llm_requests_total()
    tokens_total = get_llm_tokens_total()

    request_threshold = int(getattr(settings, "VLLM_REQUESTS_PER_HOUR_THRESHOLD", 2000))
    token_threshold = int(getattr(settings, "VLLM_DAILY_TOKENS_THRESHOLD", 5_000_000))

    requests_ready = requests_total >= request_threshold
    tokens_ready = tokens_total >= token_threshold
    traffic_ready = requests_ready or tokens_ready

    return {
        "enabled": bool(getattr(settings, "VLLM_ADOPTION_ENABLED", True)),
        "target": {
            "model": getattr(settings, "VLLM_TARGET_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
            "gpu": getattr(settings, "VLLM_TARGET_GPU", "L4 24GB"),
        },
        "traffic": {
            "llm_requests_total_since_start": requests_total,
            "llm_tokens_total_since_start": tokens_total,
            "thresholds": {
                "requests_per_hour": request_threshold,
                "daily_tokens": token_threshold,
            },
            "thresholds_met": {
                "requests_per_hour": requests_ready,
                "daily_tokens": tokens_ready,
            },
            "traffic_justifies_phase4": traffic_ready,
        },
        "phase4_plan": {
            "status": "ready" if traffic_ready else "hold",
            "next_steps": [
                "Provision GPU runtime with vLLM and autoscaling.",
                "Shadow 5% traffic with prompt+response parity checks.",
                "Promote to primary only after latency/cost SLO validation.",
            ],
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
