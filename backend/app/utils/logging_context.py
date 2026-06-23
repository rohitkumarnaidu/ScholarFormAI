# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Optional
from uuid import uuid4

from starlette.requests import HTTPConnection


_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
_session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def bind_context(
    *,
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, object]:
    tokens: Dict[str, object] = {}
    if request_id is not None:
        tokens["request_id"] = _request_id_ctx.set(request_id)
    if job_id is not None:
        tokens["job_id"] = _job_id_ctx.set(job_id)
    if session_id is not None:
        tokens["session_id"] = _session_id_ctx.set(session_id)
    return tokens


def reset_context(tokens: Dict[str, object]) -> None:
    token = tokens.get("request_id")
    if token is not None:
        _request_id_ctx.reset(token)  # type: ignore[arg-type]
    token = tokens.get("job_id")
    if token is not None:
        _job_id_ctx.reset(token)  # type: ignore[arg-type]
    token = tokens.get("session_id")
    if token is not None:
        _session_id_ctx.reset(token)  # type: ignore[arg-type]


@contextmanager
def log_context(
    *,
    request_id: Optional[str] = None,
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    tokens = bind_context(request_id=request_id, job_id=job_id, session_id=session_id)
    try:
        yield
    finally:
        reset_context(tokens)


def get_request_id_context() -> Optional[str]:
    return _request_id_ctx.get()


def get_job_id_context() -> Optional[str]:
    return _job_id_ctx.get()


def get_session_id_context() -> Optional[str]:
    return _session_id_ctx.get()


def log_extra(
    *,
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    return {
        "request_id": _request_id_ctx.get(),
        "job_id": job_id if job_id is not None else _job_id_ctx.get(),
        "session_id": session_id if session_id is not None else _session_id_ctx.get(),
    }


class LogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get()
        if not hasattr(record, "job_id"):
            record.job_id = _job_id_ctx.get()
        if not hasattr(record, "session_id"):
            record.session_id = _session_id_ctx.get()
        return True


async def bind_request_context(
    connection: HTTPConnection,
    job_id: Optional[str] = None,
    jobId: Optional[str] = None,
    document_id: Optional[str] = None,
    doc_id: Optional[str] = None,
    session_id: Optional[str] = None,
    sessionId: Optional[str] = None,
):
    resolved_job_id = job_id or jobId or document_id or doc_id
    resolved_session_id = session_id or sessionId
    request_id = getattr(connection.state, "request_id", None)
    if not request_id:
        request_id = connection.headers.get("x-request-id") or str(uuid4())
        connection.state.request_id = request_id
    with log_context(
        request_id=request_id,
        job_id=resolved_job_id,
        session_id=resolved_session_id,
    ):
        yield
