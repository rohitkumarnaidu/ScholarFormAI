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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.config.settings import settings
from app.middleware.abuse_detector import abuse_detector
from app.middleware.request_id import get_request_id
from app.pipeline.export.pdf_exporter import PDFExporter
from app.pipeline.generation.agent import AgentPipeline
from app.pipeline.generation.document_generator import get_generator
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.synthesis.synthesizer import MultiDocSynthesizer
from app.realtime.events import make_event
from app.realtime.pubsub import RedisPubSub
from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS, _validate_magic_bytes
from app.schemas.generator_session import MessageRequest
from app.services.audit_log_service import audit_log_service
from app.services.document_service import DocumentService
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
_agent_pipeline = None
_synthesizer = None


def _get_orchestrator() -> PipelineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


def _get_agent_pipeline() -> AgentPipeline:
    global _agent_pipeline
    if _agent_pipeline is None:
        _agent_pipeline = AgentPipeline(
            session_service=_session_service,
            pipeline_orchestrator=_get_orchestrator(),
            pubsub=_pubsub,
        )
    return _agent_pipeline


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


async def _assert_generation_owner(job_id: str, user_id: str) -> None:
    generator = get_generator()
    session = generator.get_session(job_id)
    if session:
        owner = session.get("user_id")
        if owner and str(owner) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to access this generation job.")
        return

    record = await DocumentService.get_document(job_id)
    if not record:
        return
    owner = record.get("user_id")
    if owner and str(owner) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this generation job.")


async def _download_generated_artifact(job_id: str, requested_format: str, user: Any) -> FileResponse:
    if requested_format not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported format. Supported: docx, pdf")

    user_id = user.id if hasattr(user, "id") else str(user)
    await _assert_generation_owner(job_id, str(user_id))

    generator = get_generator()
    try:
        status = generator.get_status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Generation job '{job_id}' not found.") from exc

    if status["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not yet complete. Current status: {status['status']} ({status['progress']}%)",
        )

    output_path = generator.get_download_path(job_id)
    if not output_path or not output_path.exists():
        raise HTTPException(status_code=404, detail="Generated file not found on server.")

    path_to_serve = output_path
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = f"generated_{job_id[:8]}.docx"

    if requested_format == "pdf":
        pdf_path = output_path.with_suffix(".pdf")
        if not pdf_path.exists():
            try:
                exporter = PDFExporter()
                generated_pdf = exporter.convert_to_pdf(str(output_path), str(output_path.parent))
                if not generated_pdf:
                    raise HTTPException(status_code=500, detail="PDF conversion failed unexpectedly.")
                candidate = Path(generated_pdf)
                if not candidate.is_absolute():
                    candidate = output_path.parent / candidate
                if candidate.exists():
                    pdf_path = candidate
            except RuntimeError as exc:
                raise HTTPException(status_code=400, detail=f"PDF export unavailable: {exc}") from exc
            except HTTPException:
                raise
            except Exception as exc:
                logger.error("Unexpected PDF export error for job %s: %s", job_id, exc)
                raise HTTPException(
                    status_code=500,
                    detail="An internal error occurred during PDF export.",
                ) from exc

        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Generated PDF not found on server.")

        path_to_serve = pdf_path
        media_type = "application/pdf"
        filename = f"generated_{job_id[:8]}.pdf"

    return FileResponse(
        path=str(path_to_serve),
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    config = session.get("config_json") or {}
    return {
        "id": session.get("id"),
        "status": session.get("status"),
        "session_type": session.get("session_type"),
        "config": config,
        "outline": session.get("outline_json"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "prompt": config.get("user_prompt") or config.get("prompt") or config.get("content"),
        "template": config.get("template") or config.get("template_id"),
    }


def _dispatch_agent_task(background_tasks: BackgroundTasks, task_name: str, *args) -> None:
    estimated_seconds_map = {
        "pipeline": 15.0,
        "resume": 9.0,
        "rewrite": 6.0,
    }
    should_queue = enhancement_manager.should_queue_job(estimated_seconds_map.get(task_name))
    if should_queue:
        if task_name == "pipeline":
            from app.tasks.celery_tasks import process_agent_pipeline_task

            process_agent_pipeline_task.delay(*args)
        elif task_name == "resume":
            from app.tasks.celery_tasks import process_agent_resume_task

            process_agent_resume_task.delay(*args)
        elif task_name == "rewrite":
            from app.tasks.celery_tasks import process_agent_rewrite_task

            process_agent_rewrite_task.delay(*args)
    else:
        if task_name == "pipeline":
            background_tasks.add_task(_get_agent_pipeline().run, *args)
        elif task_name == "resume":
            background_tasks.add_task(_get_agent_pipeline().resume, *args)
        elif task_name == "rewrite":
            background_tasks.add_task(_get_agent_pipeline().rewrite_section, *args)


def _parse_config(raw_config: str) -> dict[str, Any]:
    if not raw_config:
        return {}
    try:
        return json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid config JSON: {exc}")


def _detect_section_rewrite(message: str, sections: list[str]) -> str | None:
    normalized = message.lower()
    triggers = ("rewrite", "re-write", "revise", "reword", "update", "expand")
    if not any(trigger in normalized for trigger in triggers):
        return None

    aliases = {
        "intro": "Introduction",
        "introduction": "Introduction",
        "background": "Introduction",
        "literature review": "Literature Review",
        "methods": "Methods",
        "methodology": "Methods",
        "results": "Results",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
        "abstract": "Abstract",
    }
    for alias, canonical in aliases.items():
        if alias in normalized:
            return canonical

    for section in sections:
        if section.lower() in normalized:
            return section
    return None


def _assert_session_owner(session: dict[str, Any], user: Any) -> None:
    session_user = session.get("user_id")
    current_user_id = getattr(user, "id", user)
    if session_user and str(session_user) != str(current_user_id):
        raise HTTPException(status_code=403, detail="Access denied.")


@router.post("/sessions", status_code=202)
async def start_generation(
    request: Request,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    async def operation():
        content_type = request.headers.get("content-type", "")
        ip_address = request.client.host if request.client else None
        await abuse_detector.record_generation_request(ip_address or "unknown")

        if "application/json" in content_type:
            try:
                payload = await request.json()
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail=f"Malformed JSON body: {exc.msg}")
            session_type = str(payload.get("session_type") or "multi_doc")
            if session_type != "agent":
                raise HTTPException(status_code=422, detail="JSON requests are only supported for agent sessions.")

            user_prompt = str(
                payload.get("prompt") or payload.get("user_prompt") or payload.get("content") or ""
            ).strip()
            if not user_prompt:
                raise HTTPException(status_code=422, detail="Prompt is required for agent sessions.")

            template = str(payload.get("template") or settings.DEFAULT_TEMPLATE)
            config_payload = payload.get("config") or {}
            if not isinstance(config_payload, dict):
                config_payload = {}
            config_payload.setdefault("template", template)
            config_payload.setdefault("user_prompt", user_prompt)

            user_id = user.id if hasattr(user, "id") else str(user)
            session_id = await _session_service.create_session(user_id, "agent", config_payload)
            await _session_service.add_message(session_id, "user", user_prompt, token_count=0)
            await audit_log_service.log(
                user_id=str(user_id),
                action="generation_start",
                resource_type="generator_session",
                resource_id=session_id,
                ip_address=ip_address,
                details={"session_type": "agent", "template": template},
            )

            _dispatch_agent_task(background_tasks, "pipeline", session_id, user_prompt)

            return {"session_id": session_id, "status": "started"}

        form = await request.form()
        session_type = str(form.get("session_type") or "multi_doc")
        if session_type == "agent":
            user_prompt = str(form.get("prompt") or form.get("user_prompt") or form.get("content") or "").strip()
            if not user_prompt:
                raise HTTPException(status_code=422, detail="Prompt is required for agent sessions.")

            template = str(form.get("template") or settings.DEFAULT_TEMPLATE)
            config_payload = _parse_config(str(form.get("config") or "{}"))
            config_payload.setdefault("template", template)
            config_payload.setdefault("user_prompt", user_prompt)

            user_id = user.id if hasattr(user, "id") else str(user)
            session_id = await _session_service.create_session(user_id, "agent", config_payload)
            await _session_service.add_message(session_id, "user", user_prompt, token_count=0)
            await audit_log_service.log(
                user_id=str(user_id),
                action="generation_start",
                resource_type="generator_session",
                resource_id=session_id,
                ip_address=ip_address,
                details={"session_type": "agent", "template": template},
            )

            _dispatch_agent_task(background_tasks, "pipeline", session_id, user_prompt)

            return {"session_id": session_id, "status": "started"}

        if session_type != "multi_doc":
            raise HTTPException(status_code=422, detail="Only multi_doc sessions are supported here.")

        files = list(form.getlist("files"))
        if not files or len(files) < 2 or len(files) > 6:
            raise HTTPException(status_code=422, detail="Upload between 2 and 6 files.")

        template = str(form.get("template") or settings.DEFAULT_TEMPLATE)
        config_payload = _parse_config(str(form.get("config") or "{}"))
        user_id = user.id if hasattr(user, "id") else str(user)
        session_id = await _session_service.create_session(user_id, session_type, config_payload)
        await audit_log_service.log(
            user_id=str(user_id),
            action="generation_start",
            resource_type="generator_session",
            resource_id=session_id,
            ip_address=ip_address,
            details={"session_type": session_type, "template": template},
        )

        upload_dir = Path("uploads") / "synthesis" / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_entries: list[dict[str, Any]] = []
        for idx, file in enumerate(files):
            filename = getattr(file, "filename", None) or f"upload_{idx}"
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

            safe_name = f"{uuid.uuid4().hex}{ext}"
            file_path = upload_dir / safe_name
            file_path.write_bytes(content)
            file_entries.append(
                {
                    "path": str(file_path),
                    "filename": filename,
                    "size": len(content),
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
        operation_name="generation session create",
    )


@router.get("/sessions")
async def list_sessions(
    request: Request,
    limit: int = 50,
    user=Depends(get_current_user),
):
    async def operation():
        sessions = await _session_service.list_sessions(user.id if hasattr(user, "id") else str(user), limit=limit)
        return {"sessions": [_serialize_session(s) for s in sessions]}

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="generation session list",
    )


@router.get("/sessions/{sessionId}")
async def get_generation_status(
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
        operation_name="generation session fetch",
    )


@router.get("/sessions/{sessionId}/messages")
async def get_generation_messages(
    request: Request,
    sessionId: str,
    limit: int = 100,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)

        messages = await _session_service.get_messages(sessionId, limit=limit)
        formatted = [
            {
                "role": msg.get("role"),
                "content": msg.get("content"),
                "created_at": msg.get("created_at"),
            }
            for msg in messages
            if msg.get("content")
        ]
        return {"messages": formatted}

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="generation session messages",
    )


@router.get("/sessions/{sessionId}/document")
async def get_latest_document(
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
        if not latest_doc:
            return {"content": None, "docx_path": None}
        return {
            "content": latest_doc.get("content_json"),
            "docx_path": latest_doc.get("docx_path"),
            "version_number": latest_doc.get("version_number"),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="generation session latest document",
    )


@router.get("/sessions/{sessionId}/download")
async def download_generated(
    request: Request,
    sessionId: str,
    format: str = "docx",
    user=Depends(get_current_user),
):
    async def operation():
        return await _download_generated_artifact(
            job_id=sessionId,
            requested_format=(format or "").strip().lower(),
            user=user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_EXPORT_FORMAT",
            403: "GENERATION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
            409: "SESSION_NOT_READY",
        },
        logger=logger,
        operation_name="generation session download",
    )


@router.get("/sessions/{sessionId}/events")
async def generation_events(
    request: Request,
    sessionId: str,
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
        operation_name="generation session events",
    )


@router.post("/sessions/{sessionId}/messages")
async def generation_messages(
    request: Request,
    sessionId: str,
    payload: MessageRequest,
    background_tasks: BackgroundTasks,
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
        session_type = session.get("session_type") or "multi_doc"
        if session_type == "agent" and session.get("status") == "completed":
            sections = session.get("config_json", {}).get("sections") or []
            if not sections:
                outline = session.get("outline_json") or {}
                if isinstance(outline, dict):
                    sections = [
                        s.get("title") for s in outline.get("sections", []) if isinstance(s, dict) and s.get("title")
                    ]
            rewrite_section = _detect_section_rewrite(question, sections)
            if rewrite_section:
                _dispatch_agent_task(background_tasks, "rewrite", sessionId, rewrite_section, question)

                await _session_service.add_message(
                    sessionId,
                    "assistant",
                    f"Rewrite started for section {rewrite_section}.",
                    token_count=0,
                )
                await audit_log_service.log(
                    user_id=str(getattr(user, "id", user)),
                    action="generation_message",
                    resource_type="generator_session",
                    resource_id=sessionId,
                    ip_address=request.client.host if request.client else None,
                    details={
                        "message_length": len(question),
                        "session_type": session_type,
                        "rewrite_section": rewrite_section,
                    },
                )
                return {
                    "role": "assistant",
                    "content": f"Rewrite started for section {rewrite_section}.",
                    "sources": [],
                    "created_at": datetime.now(UTC).isoformat(),
                }
        sources = _vector_store.query(sessionId, question, top_k=5)

        context = "\n\n".join(f"[{s.get('source_doc')} - {s.get('section')}] {s.get('text')}" for s in sources)
        system = "You are a scholarly assistant. Answer using the provided sources. Cite sources inline in parentheses."
        await _session_service.add_message(sessionId, "system", system, token_count=0)
        user_prompt = f"Question: {question}\n\nSources:\n{sanitize_for_llm(context)}"
        await abuse_detector.record_llm_call(str(getattr(user, "id", user)))
        selected_model = payload.model or None
        if selected_model:
            try:
                from app.services.llm_service import LLMUnavailableError, generate_with_model

                result = await asyncio.to_thread(
                    generate_with_model,
                    [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    model_name=selected_model,
                    temperature=0.3,
                    max_tokens=800,
                    user_id=str(getattr(user, "id", user)),
                )
            except (LLMUnavailableError, Exception) as exc:
                logger.warning("Model %s failed: %s - falling back to default", selected_model, exc)
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
        else:
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
        await audit_log_service.log(
            user_id=str(getattr(user, "id", user)),
            action="generation_message",
            resource_type="generator_session",
            resource_id=sessionId,
            ip_address=request.client.host if request.client else None,
            details={
                "message_length": len(question),
                "session_type": session_type,
                "sources_returned": len(sources),
            },
        )
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
        operation_name="generation session message",
    )


@router.post("/sessions/{sessionId}/outline/approve")
async def approve_outline(
    request: Request,
    sessionId: str,
    background_tasks: BackgroundTasks,
    payload: dict[str, Any] | None = None,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)

        outline = None
        if payload:
            outline = payload.get("outline") if isinstance(payload, dict) else None
            if outline is None and isinstance(payload, dict):
                outline = payload

        if outline is not None:
            await _session_service.update_session(sessionId, outline_json=outline)

        await _session_service.add_message(sessionId, "user", "Outline approved.", token_count=0)

        _dispatch_agent_task(background_tasks, "resume", sessionId)

        outline_sections = 0
        if isinstance(outline, dict):
            outline_sections = len(outline.get("sections") or [])
        await audit_log_service.log(
            user_id=str(getattr(user, "id", user)),
            action="generation_outline_approve",
            resource_type="generator_session",
            resource_id=sessionId,
            ip_address=request.client.host if request.client else None,
            details={"outline_sections": outline_sections},
        )

        return {"session_id": sessionId, "status": "resuming"}

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="generation outline approve",
    )


@router.post("/sessions/{sessionId}/stop")
async def stop_session(
    request: Request,
    sessionId: str,
    user=Depends(get_current_user),
):
    async def operation():
        session = await _session_service.get_session(sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        _assert_session_owner(session, user)

        config = session.get("config_json") or {}
        config["status"] = "canceled"
        config["message"] = "Task stopped by user."

        await _session_service.update_session(
            sessionId,
            status="canceled",
            config_json=config,
        )

        await _get_agent_pipeline()._emit_sse(
            sessionId,
            stage="stopped",
            progress=session.get("progress") or 0,
            message="Task stopped by user.",
            extra={"status": "canceled"},
        )

        await audit_log_service.log(
            user_id=str(getattr(user, "id", user)),
            action="generation_stop",
            resource_type="generator_session",
            resource_id=sessionId,
            ip_address=request.client.host if request.client else None,
            details={"previous_status": session.get("status")},
        )

        return {"status": "stopping", "session_id": sessionId}

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "SESSION_ACCESS_DENIED",
            404: "SESSION_NOT_FOUND",
        },
        logger=logger,
        operation_name="generation session stop",
    )
