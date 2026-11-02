# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
General monitoring middleware for logging and tracing.
"""

import logging
import time
from collections.abc import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request timing and structured logging.
    Request ID is handled by RequestIdMiddleware — this only logs and measures.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_headers = getattr(request, "headers", None)
        header_id = None
        if req_headers is not None and hasattr(req_headers, "get"):
            val = req_headers.get("x-request-id") or req_headers.get("X-Request-Id")
            if isinstance(val, str) and val:
                header_id = val

        state = getattr(request, "state", None)
        state_id = None
        if state is not None:
            raw_state_id = getattr(state, "request_id", None)
            if isinstance(raw_state_id, str) and raw_state_id:
                state_id = raw_state_id

        if header_id:
            request_id = header_id
        elif state_id:
            request_id = state_id
        elif req_headers is not None:
            request_id = str(uuid4())
        else:
            request_id = "unknown"

        if state is not None and request_id != "unknown":
            try:
                state.request_id = request_id
            except Exception:
                pass

        start_time = time.time()

        logger.info("Request started: %s %s [ID: %s]", request.method, request.url.path, request_id)

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(
                "Request completed: %s %s Status: %s Duration: %.3fs [ID: %s]",
                request.method,
                request.url.path,
                response.status_code,
                duration,
                request_id,
            )

            response.headers["X-Processing-Time"] = str(duration)
            if (
                request_id != "unknown"
                and "x-request-id" not in response.headers
                and "X-Request-Id" not in response.headers
            ):
                response.headers["X-Request-Id"] = request_id
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed: %s %s Error: %s Duration: %.3fs [ID: %s]",
                request.method,
                request.url.path,
                str(e),
                duration,
                request_id,
            )
            raise e
