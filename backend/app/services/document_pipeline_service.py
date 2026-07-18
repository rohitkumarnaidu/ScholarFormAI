# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document pipeline service — orchestration glue between the HTTP/router
layer and the :class:`PipelineOrchestrator`.

Extracted from the fat `document_service.py` so pipeline dispatch is a
single, well-scoped unit. It reuses the CRUD service for status/result
reads so behaviour stays consistent with the rest of the document layer.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.document_crud_service import DocumentCrudService
from app.exceptions import DocumentNotFoundError

logger = logging.getLogger(__name__)


class DocumentPipelineService:
    """Thin orchestration layer over the formatting pipeline."""

    def __init__(self, crud: Optional[DocumentCrudService] = None) -> None:
        self._crud = crud or DocumentCrudService()

    async def start_processing(
        self, doc_id: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dispatch a document to the PipelineOrchestrator for formatting.

        Returns a status dict describing the dispatched job. The orchestrator
        import is lazy to avoid pulling heavy pipeline deps at import time.
        """
        from app.pipeline.orchestrator import PipelineOrchestrator

        doc = await self._crud.get_document(doc_id)
        if doc is None:
            raise DocumentNotFoundError(doc_id)

        orchestrator = PipelineOrchestrator()
        job = await orchestrator.dispatch(
            document_id=str(doc_id),
            options=options or {},
        )
        return {
            "document_id": str(doc_id),
            "status": "PROCESSING",
            "job": job,
        }

    async def get_processing_status(self, doc_id: str) -> List[Dict[str, Any]]:
        """Return per-phase processing statuses for a document."""
        return await self._crud.get_processing_statuses(doc_id)

    async def cancel_processing(self, doc_id: str) -> Dict[str, Any]:
        """
        Cancel an in-flight processing job for a document.

        Best-effort: marks the document FAILED with a cancellation message.
        """
        from app.pipeline.orchestrator import PipelineOrchestrator

        doc_id = str(doc_id)
        orchestrator = PipelineOrchestrator()
        try:
            await orchestrator.cancel(document_id=doc_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Pipeline cancel failed for %s: %s",
                doc_id,
                exc,
                extra={"job_id": doc_id},
            )
        await self._crud.mark_document_failed(doc_id, "Processing cancelled by user.")
        return {"document_id": doc_id, "status": "CANCELLED"}

    async def get_result(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Return the stored processing result for a document."""
        result = await self._crud.get_document_result(doc_id)
        if result is None:
            raise DocumentNotFoundError(doc_id)
        return result
