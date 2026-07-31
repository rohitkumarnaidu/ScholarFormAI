# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Stage metrics collection for pipeline orchestrator."""

import time
from typing import Optional


class StageMetrics:
    """Collects timing and result metrics for each pipeline stage."""

    def __init__(self):
        self._start_times: dict[str, float] = {}
        self._results: dict[str, dict] = {}

    def record_stage_start(self, stage_name: str) -> None:
        self._start_times[stage_name] = time.perf_counter()

    def record_stage_end(self, stage_name: str, success: bool, error: str = None) -> None:
        started = self._start_times.pop(stage_name, None)
        if started is None:
            return
        duration = time.perf_counter() - started
        self._results[stage_name] = {
            "duration_seconds": round(duration, 4),
            "success": success,
            "error": error,
        }
        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_pipeline_stage_duration(stage_name, duration)
        except Exception:
            pass

    def get_summary(self) -> dict:
        total_duration = sum(r["duration_seconds"] for r in self._results.values() if r.get("duration_seconds"))
        failures = [k for k, v in self._results.items() if not v.get("success", True)]
        return {
            "stages": dict(self._results),
            "total_duration_seconds": round(total_duration, 4),
            "stage_count": len(self._results),
            "failure_count": len(failures),
            "failed_stages": failures,
        }
