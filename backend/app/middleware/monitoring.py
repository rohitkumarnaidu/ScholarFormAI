# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
General monitoring middleware for logging and tracing.
"""

import time
import logging
from typing import Callable
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

        logger.info(f"Request started: {request.method} {request.url.path} [ID: {request_id}]")

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Duration: {duration:.3f}s [ID: {request_id}]"
            )

            response.headers["X-Processing-Time"] = str(duration)
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"Error: {str(e)} Duration: {duration:.3f}s [ID: {request_id}]"
            )
            raise e
