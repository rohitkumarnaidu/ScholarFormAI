# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Generation Service Facade — routes document generation requests through the service layer.

Routers MUST use this facade instead of importing PipelineOrchestrator, AgentPipeline,
or DocumentGenerator directly. This decouples the HTTP layer from pipeline internals.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.exceptions import NotFoundError, PipelineError, ValidationError
from app.services.generator_session_service import GeneratorSessionService
from app.services.session_vector_store import SessionVectorStore

logger = logging.getLogger(__name__)


class GenerationService:
    """
    Facade for AI document generation pipeline operations.

    Encapsulates all direct pipeline imports behind a stable service interface.
    """

    def __init__(
        self,
        session_service: GeneratorSessionService | None = None,
        vector_store: SessionVectorStore | None = None,
    ) -> None:
        self._session_service = session_service or GeneratorSessionService()
        self._vector_store = vector_store or SessionVectorStore()
        self._orchestrator: Any = None
        self._agent_pipeline: Any = None
        self._generator: Any = None

    # ── Lazy pipeline initializers (cached after first load) ──────────────

    def _get_orchestrator(self) -> Any:
        if self._orchestrator is None:
            from app.pipeline.orchestrator import PipelineOrchestrator

            self._orchestrator = PipelineOrchestrator()
        return self._orchestrator

    def _get_agent_pipeline(self) -> Any:
        if self._agent_pipeline is None:
            from app.pipeline.generation.agent import AgentPipeline

            self._agent_pipeline = AgentPipeline(
                session_service=self._session_service,
                pipeline_orchestrator=self._get_orchestrator(),
            )
        return self._agent_pipeline

    def _get_generator(self) -> Any:
        if self._generator is None:
            from app.pipeline.generation.document_generator import get_generator

            self._generator = get_generator()
        return self._generator

    # ── Public API ───────────────────────────────────────────────────────

    async def generate_document(
        self,
        session_id: str,
        user_prompt: str,
        background_tasks: Any = None,
    ) -> dict[str, Any]:
        """
        Start an AI document generation job.

        Args:
            session_id: The generator session ID.
            user_prompt: The user's prompt describing the document.
            background_tasks: FastAPI BackgroundTasks to run the pipeline.

        Returns:
            A dict with session_id and status.

        Raises:
            ValidationError: If the prompt is empty.
            PipelineError: If pipeline dispatch fails.
        """
        if not user_prompt or not user_prompt.strip():
            raise ValidationError("Prompt is required for document generation.")

        try:
            if background_tasks is not None:
                background_tasks.add_task(self._get_agent_pipeline().run, session_id, user_prompt)
            else:
                await asyncio.to_thread(self._get_agent_pipeline().run, session_id, user_prompt)
        except Exception as exc:
            logger.error("Generation dispatch failed for %s: %s", session_id, exc)
            raise PipelineError(
                message="Failed to start document generation.",
                stage="dispatch",
                details={"session_id": session_id, "error": str(exc)},
            ) from exc

        return {"session_id": session_id, "status": "started"}

    async def get_generation_status(self, session_id: str) -> dict[str, Any]:
        """
        Get the status of a running or completed generation job.

        Args:
            session_id: The generator session ID.

        Returns:
            Status dict with id, status, session_type, config, outline, etc.

        Raises:
            NotFoundError: If the session does not exist.
        """
        session = await self._session_service.get_session(session_id)
        if not session:
            raise NotFoundError(
                message=f"Generation session '{session_id}' not found.",
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

    async def cancel_generation(self, session_id: str) -> dict[str, Any]:
        """
        Cancel a running generation job.

        Args:
            session_id: The generator session ID.

        Returns:
            A dict confirming the cancellation.

        Raises:
            NotFoundError: If the session does not exist.
        """
        session = await self._session_service.get_session(session_id)
        if not session:
            raise NotFoundError(
                message=f"Generation session '{session_id}' not found.",
                details={"session_id": session_id},
            )

        config = session.get("config_json") or {}
        config["status"] = "canceled"
        config["message"] = "Task stopped by user."

        await self._session_service.update_session(
            session_id,
            status="canceled",
            config_json=config,
        )

        try:
            pipeline = self._get_agent_pipeline()
            await pipeline._emit_sse(
                session_id,
                stage="stopped",
                progress=session.get("progress") or 0,
                message="Task stopped by user.",
                extra={"status": "canceled"},
            )
        except Exception as exc:
            logger.warning("Cancel SSE emission failed for %s: %s", session_id, exc)

        return {"status": "stopping", "session_id": session_id}

    async def verify_session_ownership(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Verify that a user owns a generation session.

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
generation_service = GenerationService()
