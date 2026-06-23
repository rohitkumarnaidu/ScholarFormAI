# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders

from app.utils.logging_context import bind_context, log_extra, reset_context

logger = logging.getLogger(__name__)

_IDEMPOTENT_PATH_SUFFIXES = (
    "/upload",
    "/generator/sessions",
    "/synthesis/sessions",
)


class RequestIdMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or str(uuid4())
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        tokens = bind_context(request_id=request_id)

        method = scope.get("method", "").upper()
        path = scope.get("path", "")
        idempotency_key = headers.get("idempotency-key")
        if method == "POST" and idempotency_key and _should_log_idempotency(path):
            state["idempotency_key"] = idempotency_key
            logger.info(
                "Idempotency-Key observed for %s %s [request_id=%s]: %s",
                method,
                path,
                request_id,
                idempotency_key,
                extra=log_extra(),
            )

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-Id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_context(tokens)


def _should_log_idempotency(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in _IDEMPOTENT_PATH_SUFFIXES)


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id

    request_id = str(uuid4())
    request.state.request_id = request_id
    return request_id
