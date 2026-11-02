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
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            headers = getattr(request, "headers", None)
            if headers is not None:
                request_id = headers.get("x-request-id") or headers.get("X-Request-Id") or str(uuid4())
                try:
                    request.state.request_id = request_id
                except Exception:
                    pass
            else:
                request_id = "unknown"
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
