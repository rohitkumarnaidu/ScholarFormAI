# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from sse_starlette.sse import EventSourceResponse

from app.config.settings import settings
from app.middleware.request_id import get_request_id
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
from app.realtime.events import make_event
from app.realtime.pubsub import RedisPubSub
from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS, _validate_magic_bytes
from app.schemas.generator_session import MessageRequest
from app.services.enhancement_manager import enhancement_manager
from app.services.generator_session_service import GeneratorSessionService
from app.services.llm_service import generate_with_fallback, sanitize_for_llm
from app.services.session_vector_store import SessionVectorStore
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])
_pubsub = RedisPubSub()

_session_service = GeneratorSessionService()
_vector_store = SessionVectorStore()
_orchestrator = None
_synthesizer = None


def _get_orchestrator() -> PipelineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


def _get_synthesizer() -> MultiDocSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = MultiDocSynthesizer(
            session_service=_session_service,
            vector_store=_vector_store,
            llm_service=None,
            pipeline_orchestrator=_get_orchestrator(),
            pubsub=_pubsub,
        )
    return _synthesizer


def _parse_config(raw_config: str) -> dict[str, Any]:
    if not raw_config:
        return {}
    try:
        return json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid config JSON: {exc}")


def _assert_session_owner(session: dict[str, Any], user: Any) -> None:
    session_user = session.get("user_id")
    current_user_id = getattr(user, "id", user)
    if session_user and str(session_user) != str(current_user_id):
        raise HTTPException(status_code=403, detail="Access denied.")


@router.post("/sessions", status_code=202)
async def create_session(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    session_type: str = Form("multi_doc"),
    template: str = Form(settings.DEFAULT_TEMPLATE),
    config: str = Form("{}"),
    user=Depends(get_current_user),
):
    async def operation():
        if session_type != "multi_doc":
            raise HTTPException(status_code=422, detail="Only multi_doc sessions are supported here.")
        if not files or len(files) < 2 or len(files) > 6:
            raise HTTPException(status_code=422, detail="Upload between 2 and 6 files.")

        config_payload = _parse_config(config)
        validated_files: list[dict[str, Any]] = []
        for idx, file in enumerate(files):
            filename = file.filename or f"upload_{idx}"
            ext = Path(filename).suffix.lower()
            if ext not in ACCEPTED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'.")
            content = await file.read()
            if len(content) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit.",
                )
            await _validate_magic_bytes(file, content=content, file_ext=ext)
            validated_files.append(
                {
                    "filename": filename,
                    "ext": ext,
                    "content": content,
                }
            )

        user_id = user.id if hasattr(user, "id") else str(user)
        session_id = await _session_service.create_session(user_id, session_type, config_payload)

        upload_dir = Path("uploads") / "synthesis" / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_entries: list[dict[str, Any]] = []
        for item in validated_files:
            safe_name = f"{uuid.uuid4().hex}{item['ext']}"
            file_path = upload_dir / safe_name
            file_path.write_bytes(item["content"])
            file_entries.append(
                {
                    "path": str(file_path),
                    "filename": item["filename"],
                    "size": len(item["content"]),
                }
            )

        config_payload.update({"template": template, "uploaded_files": file_entries})
        await _session_service.update_session(session_id, config_json=config_payload)

        dispatch_info = enhancement_manager.dispatch_synthesis_pipeline(
            background_tasks=background_tasks,
            run_pipeline=_get_synthesizer().run,
            session_id=session_id,
            file_paths=[f["path"] for f in file_entries],
            template=template,
            estimated_duration_seconds=max(8.0, float(len(file_entries) * 4)),
        )
        logger.info(
            "Synthesis dispatch mode for session %s: %s",
            session_id,
            dispatch_info.get("mode"),
        )
        return {"session_id": session_id, "status": "started"}

    return await run_enveloped(
        request,
        operation,
        success_status_code=202,
        code_map={
            400: "INVALID_UPLOAD_REQUEST",
            413: "DOCUMENT_TOO_LARGE",
            422: "INVALID_SESSION_REQUEST",
        },
        logger=logger,
        operation_name="synthesis session create",
    )


@router.get("/sessions/{sessionId}")
async def get_session(
    request: Request,
    sessionId: str,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)
        latest_doc = await _session_service.get_latest_document(sessionId)
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

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="synthesis session fetch",
    )


@router.get("/sessions/{sessionId}/events")
async def session_events(
    sessionId: str,
    request: Request,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)
        return EventSourceResponse(event_generator())

    async def event_generator():
        channel = f"session:{sessionId}"
        request_id = get_request_id(request)
        try:
            from app.middleware.prometheus_metrics import MetricsManager
        except Exception:
            MetricsManager = None
        if MetricsManager:
            MetricsManager.sse_connection_open()
        connected_event = make_event(
            "connected",
            session_id=sessionId,
            request_id=request_id,
            payload={"message": f"Connected to session {sessionId}"},
        )
        yield {"event": "connected", "data": json.dumps(connected_event)}
        try:
            async for event in _pubsub.subscribe(channel):
                if await request.is_disconnected():
                    break
                event_type = event.get("event_type") or "message"
                yield {"event": event_type, "data": json.dumps(event)}
        finally:
            if MetricsManager:
                MetricsManager.sse_connection_closed()

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="synthesis session events",
    )


@router.post("/sessions/{sessionId}/messages")
async def session_messages(
    request: Request,
    sessionId: str,
    payload: MessageRequest,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)

        question = (payload.content or "").strip()
        if not question:
            raise HTTPException(status_code=422, detail="Message content cannot be empty.")

        await _session_service.add_message(sessionId, "user", question, token_count=0)
        sources = _vector_store.query(sessionId, question, top_k=5)

        context = "\n\n".join(f"[{s.get('source_doc')} - {s.get('section')}] {s.get('text')}" for s in sources)
        system = "You are a scholarly assistant. Answer using the provided sources. Cite sources inline in parentheses."
        user_prompt = f"Question: {question}\n\nSources:\n{sanitize_for_llm(context)}"
        result = await asyncio.to_thread(
            generate_with_fallback,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=800,
            user_id=str(getattr(user, "id", user)),
        )
        answer = (result.get("text") or "").strip()

        await _session_service.add_message(sessionId, "assistant", answer, token_count=0)
        return {
            "role": "assistant",
            "content": answer,
            "sources": [{"source_doc": s.get("source_doc"), "section": s.get("section")} for s in sources],
            "created_at": datetime.now(UTC).isoformat(),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
            422: "INVALID_MESSAGE",
        },
        logger=logger,
        operation_name="synthesis session message",
    )
