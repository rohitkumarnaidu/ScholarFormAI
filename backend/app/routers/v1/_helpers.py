# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from time import monotonic
from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.common.constants import ERROR_CODES as DEFAULT_ERROR_CODES
from app.common.constants import PERSONA_PATH_MAP
from app.middleware.request_id import get_request_id
from app.schemas.api_envelope import error_response, success_response


def _resolve_persona(path: str) -> str:
    normalized = str(path or "").lower()
    for prefix, persona in PERSONA_PATH_MAP.items():
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
    details: Mapping[str, Any] | None = None,
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
    code_map: Mapping[int, str] | None = None,
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
    code_map: Mapping[int, str] | None = None,
    logger: logging.Logger | None = None,
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
    except Exception as exc:
        _record_persona_kpis(
            request,
            operation_name=operation_name,
            success=False,
            duration_seconds=monotonic() - started_at,
        )
        import traceback
        err_msg = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if logger is not None:
            logger.exception("Unhandled error while processing %s: %s", operation_name, err_msg)
        return build_error_response(
            request,
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message=err_msg,
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
