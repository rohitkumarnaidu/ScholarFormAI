# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class APIError(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured error details.",
    )


class APIResponse(BaseModel):
    data: Any = Field(default=None, description="Response payload for successful requests.")
    error: APIError | None = Field(
        default=None,
        description="Error payload for unsuccessful requests.",
    )
    request_id: str = Field(..., description="Request identifier for tracing.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the response envelope was created.",
    )


def success_response(data: Any, request_id: str) -> APIResponse:
    return APIResponse(data=data, request_id=request_id)


def error_response(
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> APIResponse:
    return APIResponse(
        data=None,
        error=APIError(code=code, message=message, details=details),
        request_id=request_id,
    )
