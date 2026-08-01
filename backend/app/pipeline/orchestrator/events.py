# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Stage event emission for real-time pipeline progress."""

import logging

logger = logging.getLogger(__name__)


class StageEventEmitter:
    """Emits SSE events for pipeline stage progress."""

    async def emit_stage_start(self, stage_name: str, job_id: str = None) -> None:
        logger.debug("Stage started: %s (job=%s)", stage_name, job_id)
        try:
            from app.routers.v1.stream import emit_event

            emit_event(job_id, "stage_start", {"stage": stage_name})
        except Exception:
            pass  # intentionally ignored

    async def emit_stage_progress(self, stage_name: str, percent: int, job_id: str = None) -> None:
        logger.debug("Stage progress: %s %d%% (job=%s)", stage_name, percent, job_id)
        try:
            from app.routers.v1.stream import emit_event

            emit_event(job_id, "stage_progress", {"stage": stage_name, "percent": percent})
        except Exception:
            pass  # intentionally ignored

    async def emit_stage_complete(self, stage_name: str, job_id: str = None) -> None:
        logger.debug("Stage completed: %s (job=%s)", stage_name, job_id)
        try:
            from app.routers.v1.stream import emit_event

            emit_event(job_id, "stage_complete", {"stage": stage_name})
        except Exception:
            pass  # intentionally ignored

    async def emit_stage_error(self, stage_name: str, error: str, job_id: str = None) -> None:
        logger.error("Stage error: %s (job=%s): %s", stage_name, job_id, error)
        try:
            from app.routers.v1.stream import emit_event

            emit_event(job_id, "stage_error", {"stage": stage_name, "error": error})
        except Exception:
            pass  # intentionally ignored
