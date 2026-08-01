# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.utils.logging_context import get_request_id_context


@dataclass
class RealtimeEvent:
    event_type: str
    job_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    stage: str | None = None
    progress: int | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)


def make_event(event_type: str, **kwargs: Any) -> dict[str, Any]:
    timestamp = kwargs.pop("timestamp", None)
    payload = kwargs.pop("payload", None)
    if "request_id" not in kwargs:
        request_id = get_request_id_context()
        if request_id:
            kwargs["request_id"] = request_id
    event = RealtimeEvent(event_type=event_type, payload=payload or {}, **kwargs)
    if timestamp is not None:
        event.timestamp = timestamp
    data = asdict(event)
    data["timestamp"] = event.timestamp.isoformat()
    return data
