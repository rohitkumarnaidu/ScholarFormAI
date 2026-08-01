# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Background Task Utilities with Timeout Support.
Prevents infinite loops and resource exhaustion in background tasks.
"""

import asyncio
import logging
from typing import Callable
from functools import wraps

# ── Old ORM imports (kept for reference, replaced by DocumentService) ──────────
# from app.db.session import SessionLocal
# from app.models import Document

from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


def with_timeout(timeout_seconds: int = 300):
    """
    Decorator to add timeout to background tasks.

    Args:
        timeout_seconds: Maximum execution time (default: 5 minutes)

    Usage:
        @with_timeout(timeout_seconds=300)
        def my_background_task(arg1, arg2):
            # Task code here
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error("Task %s timed out after %s seconds", func.__name__, timeout_seconds)
                job_id = kwargs.get("job_id") or (args[1] if len(args) > 1 else None)
                if job_id:
                    _mark_job_as_failed(job_id, f"Processing timeout ({timeout_seconds}s exceeded)")
                raise
            except Exception as e:
                logger.error("Task %s failed: %s", func.__name__, e, exc_info=True)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, run in executor with timeout
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def run_with_timeout():
                try:
                    return await asyncio.wait_for(
                        loop.run_in_executor(None, func, *args, **kwargs), timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.error("Task %s timed out after %s seconds", func.__name__, timeout_seconds)
                    job_id = kwargs.get("job_id") or (args[1] if len(args) > 1 else None)
                    if job_id:
                        _mark_job_as_failed(job_id, f"Processing timeout ({timeout_seconds}s exceeded)")
                    raise

            return loop.run_until_complete(run_with_timeout())

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _mark_job_as_failed(job_id: str, error_message: str) -> None:
    """
    Mark a job as failed in the database via DocumentService.

    Old ORM equivalent:
        with SessionLocal() as db:
            doc = db.query(Document).filter_by(id=job_id).first()
            if doc:
                doc.status = "FAILED"; doc.error_message = error_message
                db.commit()
    """
    try:
        DocumentService.mark_document_failed(str(job_id), error_message)
        logger.info("Marked job %s as FAILED: %s", job_id, error_message)
    except Exception as e:
        logger.error("Failed to mark job %s as failed: %s", job_id, e, exc_info=True)


async def run_pipeline_with_timeout(
    orchestrator,
    input_path: str,
    job_id: str,
    template_name: str,
    formatting_options: dict = None,
) -> None:
    """
    Run pipeline with timeout protection.

    Args:
        orchestrator: PipelineOrchestrator instance
        input_path: Path to input file
        job_id: Job ID
        template_name: Template name
        formatting_options: Formatting options dict
    """
    try:
        await asyncio.wait_for(
            asyncio.to_thread(
                orchestrator.run_pipeline,
                input_path=input_path,
                job_id=job_id,
                template_name=template_name,
                formatting_options=formatting_options,
            ),
            timeout=900.0,  # 15 minutes max
        )
        logger.info("Pipeline completed successfully for job %s", job_id)
    except asyncio.TimeoutError:
        logger.error("Pipeline timeout for job %s", job_id)
        _mark_job_as_failed(str(job_id), "Processing timeout (15 minutes exceeded)")
    except Exception as e:
        logger.error("Pipeline failed for job %s: %s", job_id, e, exc_info=True)
        _mark_job_as_failed(str(job_id), f"Processing failed: {str(e)}")
