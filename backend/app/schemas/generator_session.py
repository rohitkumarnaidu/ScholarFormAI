# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    session_type: Literal["multi_doc", "agent"] = Field("multi_doc")
    config: Dict[str, Any] = Field(default_factory=dict)
    template: str = Field("none")


class SessionResponse(BaseModel):
    id: str
    status: str
    session_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    outline: Optional[Union[Dict[str, Any], List[Any]]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MessageRequest(BaseModel):
    content: str
    model: Optional[str] = None


class MessageResponse(BaseModel):
    role: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class StageEvent(BaseModel):
    stage: str
    progress: int
    message: str
    timestamp: datetime
