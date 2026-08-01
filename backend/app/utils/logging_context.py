# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from uuid import uuid4

from starlette.requests import HTTPConnection

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_job_id_ctx: ContextVar[str | None] = ContextVar("job_id", default=None)
_session_id_ctx: ContextVar[str | None] = ContextVar("session_id", default=None)
_user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def extract_user_id(user: object | None) -> str | None:
    if user is None:
        return None
    if isinstance(user, str):
        return user
    if isinstance(user, dict):
        uid = user.get("id") or user.get("user_id")
        return str(uid) if uid is not None else None

    try:
        is_auth = getattr(user, "is_authenticated", True)
        if is_auth is False or (callable(is_auth) and not is_auth()):
            return None
    except (AttributeError, AssertionError, Exception):
        pass  # intentionally ignored

    try:
        user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
        if user_id is not None:
            return str(user_id)
    except (AttributeError, AssertionError, Exception):
        pass  # intentionally ignored

    return None


def bind_context(
    *,
    request_id: str | None = None,
    job_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    user: object | None = None,
) -> dict[str, object]:
    tokens: dict[str, object] = {}
    if request_id is not None:
        tokens["request_id"] = _request_id_ctx.set(request_id)
    if job_id is not None:
        tokens["job_id"] = _job_id_ctx.set(job_id)
    if session_id is not None:
        tokens["session_id"] = _session_id_ctx.set(session_id)
    resolved_user_id = user_id or extract_user_id(user)
    if resolved_user_id is not None:
        tokens["user_id"] = _user_id_ctx.set(resolved_user_id)
    return tokens


def reset_context(tokens: dict[str, object]) -> None:
    token = tokens.get("request_id")
    if token is not None:
        _request_id_ctx.reset(token)  # type: ignore[arg-type]
    token = tokens.get("job_id")
    if token is not None:
        _job_id_ctx.reset(token)  # type: ignore[arg-type]
    token = tokens.get("session_id")
    if token is not None:
        _session_id_ctx.reset(token)  # type: ignore[arg-type]
    token = tokens.get("user_id")
    if token is not None:
        _user_id_ctx.reset(token)  # type: ignore[arg-type]


@contextmanager
def log_context(
    *,
    request_id: str | None = None,
    job_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    user: object | None = None,
):
    tokens = bind_context(
        request_id=request_id,
        job_id=job_id,
        session_id=session_id,
        user_id=user_id,
        user=user,
    )
    try:
        yield
    finally:
        reset_context(tokens)


def get_request_id_context() -> str | None:
    return _request_id_ctx.get()


def get_job_id_context() -> str | None:
    return _job_id_ctx.get()


def get_session_id_context() -> str | None:
    return _session_id_ctx.get()


def get_user_id_context() -> str | None:
    return _user_id_ctx.get()


def log_extra(
    *,
    job_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    user: object | None = None,
) -> dict[str, str | None]:
    resolved_user_id = user_id or extract_user_id(user)
    return {
        "request_id": _request_id_ctx.get(),
        "job_id": job_id if job_id is not None else _job_id_ctx.get(),
        "session_id": session_id if session_id is not None else _session_id_ctx.get(),
        "user_id": resolved_user_id if resolved_user_id is not None else _user_id_ctx.get(),
    }


class LogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get()
        if not hasattr(record, "job_id"):
            record.job_id = _job_id_ctx.get()
        if not hasattr(record, "session_id"):
            record.session_id = _session_id_ctx.get()
        if not hasattr(record, "user_id"):
            record.user_id = _user_id_ctx.get()
        return True


async def bind_request_context(
    connection: HTTPConnection,
    job_id: str | None = None,
    jobId: str | None = None,
    document_id: str | None = None,
    doc_id: str | None = None,
    session_id: str | None = None,
    sessionId: str | None = None,
    user_id: str | None = None,
    user: object | None = None,
):
    resolved_job_id = job_id or jobId or document_id or doc_id
    resolved_session_id = session_id or sessionId
    state_obj = None
    with suppress(AttributeError, AssertionError, Exception):
        state_obj = getattr(connection, "state", None)

    request_id = None
    if state_obj:
        with suppress(AttributeError, AssertionError, Exception):
            request_id = getattr(state_obj, "request_id", None)

    if not request_id and hasattr(connection, "headers"):
        try:
            request_id = connection.headers.get("x-request-id") or str(uuid4())
            if state_obj:
                connection.state.request_id = request_id
        except (AttributeError, AssertionError, Exception):
            if not request_id:
                request_id = str(uuid4())

    conn_user = user
    if conn_user is None and state_obj is not None:
        try:
            conn_user = getattr(state_obj, "user", None)
        except (AttributeError, AssertionError, Exception):
            conn_user = None

    if conn_user is None and connection is not None:
        try:
            conn_user = getattr(connection, "user", None)
        except (AttributeError, AssertionError, Exception):
            conn_user = None

    resolved_user_id = user_id or extract_user_id(conn_user)
    with log_context(
        request_id=request_id,
        job_id=resolved_job_id,
        session_id=resolved_session_id,
        user_id=resolved_user_id,
    ):
        yield
