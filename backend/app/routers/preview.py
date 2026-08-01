# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import re
import time
from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config.settings import settings
from app.middleware.request_id import get_request_id
from app.realtime.events import make_event
from app.realtime.pubsub import RedisPubSub
from app.services.llm_service import LLMUnavailableError, generate_with_fallback, sanitize_for_llm
from app.services.preview_renderer import preview_renderer
from app.utils.logging_context import bind_request_context, log_extra

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Preview"], dependencies=[Depends(bind_request_context)])

_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
_preview_pubsub = RedisPubSub()


class PreviewRequest(BaseModel):
    content: str
    templateId: str


def _valid_session_id(session_id: str) -> bool:
    return bool(_SESSION_PATTERN.match(session_id or ""))


def _hash_html(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _chunk_text(text: str, chunk_size: int = 320) -> Iterable[str]:
    if not text:
        return []
    return (text[i : i + chunk_size] for i in range(0, len(text), chunk_size))


@router.post("/api/v1/preview/live")
async def preview_live(payload: PreviewRequest):
    result = preview_renderer.render_preview(payload.content or "", payload.templateId or settings.DEFAULT_TEMPLATE)
    return {
        "html": result["html"],
        "latencyMs": result["latency_ms"],
        "warnings": result["warnings"],
    }


async def _heartbeat(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(20)
        await websocket.send_json({"type": "ping", "timestamp": time.time()})


async def _forward_updates(websocket: WebSocket, channel: str) -> None:
    async for event in _preview_pubsub.subscribe(channel):
        payload = event.get("payload") or event
        try:
            await websocket.send_json(payload)
        except WebSocketDisconnect:
            break
        except Exception:
            break


@router.websocket("/api/v1/ws/preview/{sessionId}")
async def preview_ws(websocket: WebSocket, sessionId: str):
    if not _valid_session_id(sessionId):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        from app.middleware.prometheus_metrics import MetricsManager
    except Exception:
        MetricsManager = None
    if MetricsManager:
        MetricsManager.ws_connection_open()
    channel = f"preview:{sessionId}"
    forward_task = asyncio.create_task(_forward_updates(websocket, channel))
    heartbeat_task = asyncio.create_task(_heartbeat(websocket))
    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue
            content = payload.get("content", "")
            template_id = payload.get("templateId") or payload.get("template_id") or settings.DEFAULT_TEMPLATE
            seq = payload.get("seq")
            checksum = payload.get("checksum")
            result = preview_renderer.render_preview(content, template_id)
            version = checksum or _hash_html(result["html"])
            response_payload = {
                "html": result["html"],
                "latencyMs": result["latency_ms"],
                "warnings": result["warnings"],
                "version": version,
                "seq": seq,
            }
            event = make_event("preview_update", session_id=sessionId, payload=response_payload)
            await _preview_pubsub.publish(channel, event)
    except WebSocketDisconnect:
        logger.info("Preview websocket disconnected: %s", sessionId, extra=log_extra(session_id=sessionId))
    except asyncio.CancelledError:
        logger.info("Preview websocket cancelled: %s", sessionId, extra=log_extra(session_id=sessionId))
    finally:
        for task in (forward_task, heartbeat_task):
            if not task.done():
                task.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(forward_task, heartbeat_task, return_exceptions=True)
        if MetricsManager:
            MetricsManager.ws_connection_closed()


def _build_ai_messages(content: str, template_id: str) -> list[dict[str, str]]:
    sanitized = sanitize_for_llm(content)
    system_prompt = (
        "You are a helpful academic writing assistant. Provide concise, actionable "
        "suggestions to improve clarity and formatting without changing meaning."
    )
    user_prompt = (
        f"Template: {template_id}\n"
        "Return 3-6 short bullet suggestions, then a brief improved paragraph if needed.\n\n"
        f"{sanitized}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


@router.get("/api/v1/preview/{sessionId}/ai-suggest")
async def ai_suggest(
    request: Request,
    sessionId: str,
    content: str = Query(...),
    templateId: str = Query(settings.DEFAULT_TEMPLATE),
):
    if not _valid_session_id(sessionId):
        raise HTTPException(status_code=400, detail="Invalid sessionId.")

    request_id = get_request_id(request)

    async def event_generator():
        try:
            from app.middleware.prometheus_metrics import MetricsManager
        except Exception:
            MetricsManager = None
        if MetricsManager:
            MetricsManager.sse_connection_open()
        start = time.perf_counter()
        yield {
            "event": "status",
            "data": json.dumps({"state": "started", "sessionId": sessionId, "request_id": request_id}),
        }
        try:
            messages = _build_ai_messages(content, templateId)
            result = await asyncio.to_thread(generate_with_fallback, messages, temperature=0.3, max_tokens=600)
            text = (result.get("text") or "").strip()
            for chunk in _chunk_text(text):
                yield {"event": "suggestion", "data": json.dumps({"content": chunk, "request_id": request_id})}
                await asyncio.sleep(0)
            latency_ms = (time.perf_counter() - start) * 1000.0
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "done": True,
                        "latencyMs": latency_ms,
                        "model": result.get("model"),
                        "tier": result.get("tier"),
                        "request_id": request_id,
                    }
                ),
            }
        except LLMUnavailableError as exc:
            yield {"event": "error", "data": json.dumps({"error": str(exc), "request_id": request_id})}
        except Exception as exc:
            logger.warning("AI suggest failed for %s: %s", sessionId, exc, extra=log_extra(session_id=sessionId))
            yield {"event": "error", "data": json.dumps({"error": "AI suggestion failed", "request_id": request_id})}
        finally:
            if MetricsManager:
                MetricsManager.sse_connection_closed()

    return EventSourceResponse(event_generator())
