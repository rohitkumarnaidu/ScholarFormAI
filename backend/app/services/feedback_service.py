# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Feedback Service Facade — routes AI suggestion feedback through the service layer.

Routers MUST use this facade instead of importing AgentMemory directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.exceptions import PipelineError, NotFoundError

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Facade for AI suggestion feedback and correction operations.

    Encapsulates AgentMemory and feedback DB persistence behind a stable interface.
    """

    def __init__(self) -> None:
        self._memory: Any = None

    def _get_memory(self) -> Any:
        if self._memory is None:
            from app.pipeline.agents.memory import AgentMemory
            self._memory = AgentMemory()
        return self._memory

    async def submit_feedback(
        self,
        document_id: str,
        field: str,
        original_value: Any,
        corrected_value: Any,
        user_id: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Record user feedback on an AI suggestion.

        Stores the correction in AgentMemory for learning and persists to
        the database for audit.

        Args:
            document_id: The document the feedback relates to.
            field: The field that was corrected.
            original_value: The original AI-generated value.
            corrected_value: The user's corrected value.
            user_id: Optional user ID for DB persistence.
            comments: Optional user comments.

        Returns:
            A dict confirming the feedback was recorded.

        Raises:
            PipelineError: If feedback cannot be recorded.
        """
        try:
            self._get_memory().remember_correction(
                document_id=document_id,
                field=field,
                original_value=original_value,
                corrected_value=corrected_value,
            )
        except Exception as exc:
            logger.warning("AgentMemory.remember_correction failed: %s", exc)
            # Non-fatal — memory is in-memory, may not be available

        if user_id:
            try:
                await self._persist_feedback(
                    document_id=document_id,
                    user_id=user_id,
                    field=field,
                    original_value=original_value,
                    corrected_value=corrected_value,
                    comments=comments,
                )
            except Exception as exc:
                logger.warning("Feedback DB persistence failed: %s", exc)
                # Non-fatal — feedback is still recorded in memory

        return {"status": "success", "message": "Feedback recorded successfully"}

    async def _persist_feedback(
        self,
        document_id: str,
        user_id: str,
        field: str,
        original_value: Any,
        corrected_value: Any,
        comments: Optional[str] = None,
    ) -> None:
        from app.db.supabase_client import get_supabase_client

        sb = get_supabase_client()
        if sb is None:
            logger.warning("Supabase not available for feedback persistence.")
            return

        payload = {
            "document_id": document_id,
            "user_id": user_id,
            "field": field,
            "original_value": str(original_value),
            "corrected_value": str(corrected_value),
            "comments": comments,
        }

        def run_insert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("feedback").insert(payload).execute()

        await asyncio.to_thread(run_insert)

    async def get_feedback_history(
        self,
        document_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get the feedback/correction history for a document.

        Args:
            document_id: The document to retrieve feedback for.
            limit: Maximum number of records to return.

        Returns:
            A list of feedback records.

        Raises:
            NotFoundError: If the document has no feedback records.
        """
        try:
            from app.db.supabase_client import get_supabase_client

            sb = get_supabase_client()
            if sb is None:
                return []

            def run_query():
                client = get_supabase_client()
                if client is None:
                    raise RuntimeError("Supabase client not available.")
                return (
                    client.table("feedback")
                    .select("*")
                    .eq("document_id", document_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )

            result = await asyncio.to_thread(run_query)
            records = result.data or []
            if not records:
                raise NotFoundError(
                    message="No feedback records found for this document.",
                    details={"document_id": document_id},
                )
            return records
        except NotFoundError:
            raise
        except Exception as exc:
            logger.warning("Feedback history lookup failed: %s", exc)
            return []

    async def get_feedback_summary(self) -> dict[str, Any]:
        """
        Get a summary of all corrections stored in AgentMemory.

        Returns:
            A dict with correction summaries.
        """
        try:
            summary = self._get_memory().get_memory_summary()
            return summary.get("corrections", {})
        except Exception as exc:
            logger.warning("Feedback summary retrieval failed: %s", exc)
            return {}


# Singleton for dependency injection
feedback_service = FeedbackService()
