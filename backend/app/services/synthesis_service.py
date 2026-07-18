# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Synthesis Service Facade — routes multi-document synthesis requests through the service layer.

Routers MUST use this facade instead of importing MultiDocSynthesizer directly.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from app.exceptions import PipelineError, NotFoundError, ValidationError
from app.services.generator_session_service import GeneratorSessionService
from app.services.session_vector_store import SessionVectorStore

logger = logging.getLogger(__name__)


class SynthesisService:
    """
    Facade for multi-document synthesis pipeline operations.

    Encapsulates all direct MultiDocSynthesizer imports behind a stable service interface.
    """

    def __init__(
        self,
        session_service: Optional[GeneratorSessionService] = None,
        vector_store: Optional[SessionVectorStore] = None,
    ) -> None:
        self._session_service = session_service or GeneratorSessionService()
        self._vector_store = vector_store or SessionVectorStore()
        self._synthesizer: Any = None
        self._orchestrator: Any = None
        self._pubsub: Any = None

    # ── Lazy initializers ────────────────────────────────────────────────

    def _get_pubsub(self) -> Any:
        if self._pubsub is None:
            from app.realtime.pubsub import RedisPubSub
            self._pubsub = RedisPubSub()
        return self._pubsub

    def _get_orchestrator(self) -> Any:
        if self._orchestrator is None:
            from app.pipeline.orchestrator import PipelineOrchestrator
            self._orchestrator = PipelineOrchestrator()
        return self._orchestrator

    def _get_synthesizer(self) -> Any:
        if self._synthesizer is None:
            from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
            self._synthesizer = MultiDocSynthesizer(
                session_service=self._session_service,
                vector_store=self._vector_store,
                llm_service=None,
                pipeline_orchestrator=self._get_orchestrator(),
                pubsub=self._get_pubsub(),
            )
        return self._synthesizer

    # ── Public API ───────────────────────────────────────────────────────

    async def run_synthesis(
        self,
        session_id: str,
        file_paths: list[str],
        template: str = "default",
        background_tasks: Any = None,
    ) -> dict[str, Any]:
        """
        Start a multi-document synthesis job.

        Args:
            session_id: The synthesis session ID.
            file_paths: List of file paths to synthesize.
            template: The formatting template name.
            background_tasks: FastAPI BackgroundTasks (optional).

        Returns:
            A dict with session_id and status.

        Raises:
            ValidationError: If no file paths are provided.
            PipelineError: If synthesis dispatch fails.
        """
        if not file_paths:
            raise ValidationError(
                message="At least one file path is required for synthesis.",
                details={"session_id": session_id},
            )

        try:
            from app.services.enhancement_manager import enhancement_manager

            dispatch_info = enhancement_manager.dispatch_synthesis_pipeline(
                background_tasks=background_tasks,
                run_pipeline=self._get_synthesizer().run,
                session_id=session_id,
                file_paths=file_paths,
                template=template,
                estimated_duration_seconds=max(8.0, float(len(file_paths) * 4)),
            )
            logger.info(
                "Synthesis dispatch mode for session %s: %s",
                session_id,
                dispatch_info.get("mode"),
            )
        except Exception as exc:
            logger.error("Synthesis dispatch failed for %s: %s", session_id, exc)
            raise PipelineError(
                message="Failed to start synthesis.",
                stage="dispatch",
                details={"session_id": session_id, "error": str(exc)},
            ) from exc

        return {"session_id": session_id, "status": "started"}

    async def get_synthesis_status(self, session_id: str) -> dict[str, Any]:
        """
        Get the status of a running or completed synthesis job.

        Args:
            session_id: The synthesis session ID.

        Returns:
            Status dict with session details.

        Raises:
            NotFoundError: If the session does not exist.
        """
        session = await self._session_service.get_session(session_id)
        if not session:
            raise NotFoundError(
                message=f"Synthesis session '{session_id}' not found.",
                details={"session_id": session_id},
            )

        latest_doc = await self._session_service.get_latest_document(session_id)
        return {
            "id": session.get("id"),
            "status": session.get("status"),
            "session_type": session.get("session_type"),
            "config": session.get("config_json") or {},
            "outline": session.get("outline_json"),
            "docx_path": (latest_doc or {}).get("docx_path"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
        }

    async def verify_session_ownership(
        self, session_id: str, user_id: str
    ) -> dict[str, Any]:
        """
        Verify that a user owns a synthesis session.

        Args:
            session_id: The session to check.
            user_id: The user ID to verify against.

        Returns:
            The session dict if ownership is confirmed.

        Raises:
            NotFoundError: If the session does not exist or is not owned by user.
        """
        session = await self._session_service.get_session(session_id)
        if not session:
            raise NotFoundError(
                message="Session not found.",
                details={"session_id": session_id},
            )
        if str(session.get("user_id")) != str(user_id):
            raise NotFoundError(
                message="Session not found.",
                details={"session_id": session_id},
            )
        return session


# Singleton for dependency injection
synthesis_service = SynthesisService()
