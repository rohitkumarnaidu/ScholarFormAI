# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    session_type: Literal["multi_doc", "agent"] = Field("multi_doc")
    config: dict[str, Any] = Field(default_factory=dict)
    template: str = Field("none")


class SessionResponse(BaseModel):
    id: str
    status: str
    session_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    outline: dict[str, Any] | list[Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageRequest(BaseModel):
    content: str
    model: str | None = None


class MessageResponse(BaseModel):
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None


class StageEvent(BaseModel):
    stage: str
    progress: int
    message: str
    timestamp: datetime
