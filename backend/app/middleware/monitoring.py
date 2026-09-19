# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
General monitoring middleware for logging and tracing.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request timing and structured logging.
    Request ID is handled by RequestIdMiddleware — this only logs and measures.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
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
