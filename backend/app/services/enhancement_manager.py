# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enhancement capability manager.

All enhancements are optional. This module centralizes:
1) Capability discovery (installed backends)
2) Feature-flag resolution
3) Fallback-safe task dispatching
"""

from __future__ import annotations

import importlib.util
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.config.settings import settings
from app.utils import background_tasks as background_task_utils

logger = logging.getLogger(__name__)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _split_csv(raw_value: str, default: list[str]) -> list[str]:
    if not raw_value:
        return list(default)
    parts = [part.strip().lower() for part in str(raw_value).split(",")]
    cleaned = [part for part in parts if part]
    return cleaned or list(default)


@dataclass(frozen=True)
class EnhancementProfile:
    enabled: bool
    queue_enabled: bool
    queue_provider: str
    queue_available: bool
    ocr_enabled: bool
    ocr_backends: list[str]
    keyword_enabled: bool
    keyword_backends: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "queue_enabled": self.queue_enabled,
            "queue_provider": self.queue_provider,
            "queue_available": self.queue_available,
            "ocr_enabled": self.ocr_enabled,
            "ocr_backends": list(self.ocr_backends),
            "keyword_enabled": self.keyword_enabled,
            "keyword_backends": list(self.keyword_backends),
        }


class EnhancementManager:
    """Fallback-first enhancement registry and dispatcher."""

    def __init__(self) -> None:
        self._profile: EnhancementProfile | None = None

    def refresh(self) -> EnhancementProfile:
        self._profile = self._build_profile()
        return self._profile

    @property
    def profile(self) -> EnhancementProfile:
        if self._profile is None:
            self._profile = self._build_profile()
        return self._profile

    def is_celery_queue_active(self) -> bool:
        profile = self.profile
        return (
            profile.enabled and profile.queue_enabled and profile.queue_provider == "celery" and profile.queue_available
        )

    @staticmethod
    def _queue_threshold_seconds() -> float:
        raw = getattr(settings, "ENHANCEMENT_QUEUE_MIN_SECONDS", 5.0)
        try:
            threshold = float(raw)
        except (TypeError, ValueError):
            threshold = 5.0
        return max(0.0, threshold)

    def should_queue_job(self, estimated_duration_seconds: float | None = None) -> bool:
        if not self.is_celery_queue_active():
            return False
        if estimated_duration_seconds is None:
            return True
        return float(estimated_duration_seconds) >= self._queue_threshold_seconds()

    def get_ocr_backends(self) -> list[str]:
        return list(self.profile.ocr_backends)

    def get_keyword_backends(self) -> list[str]:
        return list(self.profile.keyword_backends)

    def dispatch_document_pipeline(
        self,
        *,
        background_tasks: Any,
        orchestrator: Any,
        input_path: str,
        job_id: str,
        template_name: str,
        formatting_options: dict[str, Any] | None = None,
        queue_name: str | None = None,
        estimated_duration_seconds: float | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch upload pipeline job with graceful fallback.

        Preferred path:
        - Celery task (if explicitly enabled and available)
        Fallback path:
        - FastAPI BackgroundTasks + run_pipeline_with_timeout
        """
        if self.should_queue_job(estimated_duration_seconds):
            try:
                from app.tasks.celery_tasks import process_document_task

                queue = queue_name or "interactive"
                async_result = process_document_task.apply_async(args=[str(job_id)], queue=queue)
                logger.info("Job %s queued via Celery task_id=%s", job_id, async_result.id)
                return {"mode": "celery", "task_id": async_result.id}
            except Exception as exc:
                logger.warning(
                    "Celery dispatch failed for job %s (%s). Falling back to FastAPI background task.",
                    job_id,
                    exc,
                )

        background_tasks.add_task(
            background_task_utils.run_pipeline_with_timeout,
            orchestrator=orchestrator,
            input_path=input_path,
            job_id=job_id,
            template_name=template_name,
            formatting_options=formatting_options,
        )
        return {"mode": "background", "task_id": None}

    def dispatch_generation_pipeline(
        self,
        *,
        background_tasks: Any,
        run_pipeline: Callable[[str], Any],
        job_id: str,
        queue_name: str | None = None,
        estimated_duration_seconds: float | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch generation pipeline job with graceful fallback.
        """
        if self.should_queue_job(estimated_duration_seconds):
            try:
                from app.tasks.celery_tasks import process_generation_task

                queue = queue_name or "interactive"
                async_result = process_generation_task.apply_async(args=[str(job_id)], queue=queue)
                logger.info("Generation job %s queued via Celery task_id=%s", job_id, async_result.id)
                return {"mode": "celery", "task_id": async_result.id}
            except Exception as exc:
                logger.warning(
                    "Celery generation dispatch failed for job %s (%s). Falling back to BackgroundTasks.",
                    job_id,
                    exc,
                )

        background_tasks.add_task(run_pipeline, job_id)
        return {"mode": "background", "task_id": None}

    def dispatch_edit_flow(
        self,
        *,
        background_tasks: Any,
        orchestrator: Any,
        job_id: str,
        edited_structured_data: dict[str, Any],
        template_name: str,
        queue_name: str | None = None,
        estimated_duration_seconds: float | None = None,
    ) -> dict[str, Any]:
        """
        Dispatch edit/reformat flow with graceful fallback.
        """
        if self.should_queue_job(estimated_duration_seconds):
            try:
                from app.tasks.celery_tasks import process_edit_document_task

                queue = queue_name or "interactive"
                async_result = process_edit_document_task.apply_async(
                    args=[str(job_id), edited_structured_data, str(template_name)],
                    queue=queue,
                )
                logger.info("Edit job %s queued via Celery task_id=%s", job_id, async_result.id)
                return {"mode": "celery", "task_id": async_result.id}
            except Exception as exc:
                logger.warning(
                    "Celery edit dispatch failed for job %s (%s). Falling back to BackgroundTasks.",
                    job_id,
                    exc,
                )

        background_tasks.add_task(
            orchestrator.run_edit_flow,
            job_id=job_id,
            edited_structured_data=edited_structured_data,
            template_name=template_name,
        )
        return {"mode": "background", "task_id": None}

    def dispatch_synthesis_pipeline(
        self,
        *,
        background_tasks: Any,
        run_pipeline: Callable[[str, list[str], str], Any],
        session_id: str,
        file_paths: list[str],
        template: str,
        queue_name: str | None = None,
        estimated_duration_seconds: float | None = None,
    ) -> dict[str, Any]:
        if self.should_queue_job(estimated_duration_seconds):
            try:
                from app.tasks.celery_tasks import process_synthesis_task

                queue = queue_name or "interactive"
                async_result = process_synthesis_task.apply_async(
                    args=[str(session_id), list(file_paths or []), str(template)],
                    queue=queue,
                )
                logger.info(
                    "Synthesis session %s queued via Celery task_id=%s",
                    session_id,
                    async_result.id,
                )
                return {"mode": "celery", "task_id": async_result.id}
            except Exception as exc:
                logger.warning(
                    "Celery synthesis dispatch failed for session %s (%s). Falling back to BackgroundTasks.",
                    session_id,
                    exc,
                )

        background_tasks.add_task(
            run_pipeline,
            session_id,
            list(file_paths or []),
            template,
        )
        return {"mode": "background", "task_id": None}

    def _build_profile(self) -> EnhancementProfile:
        enhancements_enabled = _coerce_bool(
            getattr(settings, "ENHANCEMENTS_ENABLED", True),
            True,
        )

        queue_enabled = _coerce_bool(
            getattr(settings, "ENHANCEMENT_QUEUE_ENABLED", False),
            False,
        )
        queue_provider_raw = str(getattr(settings, "ENHANCEMENT_QUEUE_PROVIDER", "auto")).strip().lower()
        queue_provider = queue_provider_raw if queue_provider_raw in {"auto", "local", "celery"} else "auto"
        celery_available = _module_available("celery")
        redis_available = _module_available("redis")
        queue_backend_available = celery_available and redis_available

        resolved_queue_provider = "local"
        if queue_provider == "celery" and queue_backend_available or queue_provider == "auto" and queue_enabled and queue_backend_available:
            resolved_queue_provider = "celery"

        ocr_enabled = _coerce_bool(
            getattr(settings, "ENHANCEMENT_OCR_ENABLED", True),
            True,
        )
        ocr_preferred = _split_csv(
            getattr(settings, "ENHANCEMENT_OCR_BACKENDS", "tesseract,paddle,surya"),
            ["tesseract", "paddle", "surya"],
        )
        detected_ocr = {
            "tesseract": _module_available("pytesseract") and _module_available("pdf2image"),
            "paddle": _module_available("paddleocr"),
            "surya": _module_available("surya"),
        }
        ocr_backends = [name for name in ocr_preferred if detected_ocr.get(name)]
        if not ocr_backends:
            ocr_backends = ["builtin"]

        keyword_enabled = _coerce_bool(
            getattr(settings, "ENHANCEMENT_KEYWORD_ENABLED", True),
            True,
        )
        keyword_preferred = _split_csv(
            getattr(settings, "ENHANCEMENT_KEYWORD_BACKENDS", "keyllm,keybert,yake,basic"),
            ["keyllm", "keybert", "yake", "basic"],
        )
        keyllm_available = any(
            bool(value)
            for value in (
                getattr(settings, "NVIDIA_API_KEY", None),
                getattr(settings, "GROQ_API_KEY", None),
                getattr(settings, "OPENROUTER_API_KEY", None),
                getattr(settings, "OPENAI_API_KEY", None),
            )
        )
        detected_keywords = {
            "keyllm": keyllm_available,
            "keybert": _module_available("keybert"),
            "yake": _module_available("yake"),
            "basic": True,
        }
        keyword_backends = [name for name in keyword_preferred if detected_keywords.get(name)]
        if not keyword_backends:
            keyword_backends = ["basic"]

        profile = EnhancementProfile(
            enabled=enhancements_enabled,
            queue_enabled=queue_enabled,
            queue_provider=resolved_queue_provider,
            queue_available=queue_backend_available,
            ocr_enabled=ocr_enabled,
            ocr_backends=ocr_backends,
            keyword_enabled=keyword_enabled,
            keyword_backends=keyword_backends,
        )
        logger.info("Enhancement profile: %s", profile.to_dict())
        return profile


enhancement_manager = EnhancementManager()
