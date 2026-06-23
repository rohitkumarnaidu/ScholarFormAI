# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
import re
from time import monotonic
from collections.abc import Awaitable, Callable
from typing import Any, Mapping, Optional

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.middleware.request_id import get_request_id
from app.schemas.api_envelope import error_response, success_response

DEFAULT_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_SERVER_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}

_PERSONA_PATH_MAP = {
    "/api/v1/documents": "formatter",
    "/api/v1/generator": "authoring",
    "/api/v1/synthesis": "synthesis",
    "/api/v1/billing": "billing",
    "/api/v1/templates": "templates",
}


def _resolve_persona(path: str) -> str:
    normalized = str(path or "").lower()
    for prefix, persona in _PERSONA_PATH_MAP.items():
        if normalized.startswith(prefix):
            return persona
    return "platform"


def _metric_safe_label(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value or "").strip().lower())
    return sanitized.strip("_") or "unknown"


def _record_persona_kpis(request: Request, operation_name: str, success: bool, duration_seconds: float) -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        persona = _resolve_persona(request.url.path)
        operation = _metric_safe_label(operation_name)
        outcome = "success" if success else "error"
        MetricsManager.record_persona_event(persona=persona, event=operation, outcome=outcome)
        MetricsManager.record_persona_latency(
            persona=persona,
            operation=operation,
            duration_seconds=max(duration_seconds, 0.0),
        )
    except Exception:
        pass  # Metrics recording is non-critical; silent failure is acceptable.


def build_success_response(
    request: Request,
    data: Any,
    *,
    status_code: int = 200,
) -> JSONResponse:
    payload = success_response(jsonable_encoder(data), get_request_id(request))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Optional[Mapping[str, Any]] = None,
) -> JSONResponse:
    payload = error_response(
        code=code,
        message=message,
        request_id=get_request_id(request),
        details=jsonable_encoder(details) if details is not None else None,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def http_exception_to_response(
    request: Request,
    exc: HTTPException,
    *,
    code_map: Optional[Mapping[int, str]] = None,
) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        message = detail
        details = None
    else:
        message = "Request failed"
        details = {"detail": jsonable_encoder(detail)}

    code = (code_map or {}).get(exc.status_code) or DEFAULT_ERROR_CODES.get(
        exc.status_code,
        "API_ERROR",
    )
    return build_error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )


async def run_enveloped(
    request: Request,
    operation: Callable[[], Awaitable[Any]],
    *,
    success_status_code: int = 200,
    code_map: Optional[Mapping[int, str]] = None,
    logger: Optional[logging.Logger] = None,
    operation_name: str = "request",
):
    started_at = monotonic()
    try:
        result = await operation()
    except HTTPException as exc:
        _record_persona_kpis(
            request,
            operation_name=operation_name,
            success=False,
            duration_seconds=monotonic() - started_at,
        )
        return http_exception_to_response(request, exc, code_map=code_map)
    except Exception:
        _record_persona_kpis(
            request,
            operation_name=operation_name,
            success=False,
            duration_seconds=monotonic() - started_at,
        )
        if logger is not None:
            logger.exception("Unhandled error while processing %s", operation_name)
        return build_error_response(
            request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
        )

    if isinstance(result, Response):
        _record_persona_kpis(
            request,
            operation_name=operation_name,
            success=True,
            duration_seconds=monotonic() - started_at,
        )
        return result

    _record_persona_kpis(
        request,
        operation_name=operation_name,
        success=True,
        duration_seconds=monotonic() - started_at,
    )
    return build_success_response(
        request,
        result,
        status_code=success_status_code,
    )
