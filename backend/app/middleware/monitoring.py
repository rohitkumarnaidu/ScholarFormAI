# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
General monitoring middleware for logging and tracing.
"""
import time
import logging
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging, timing, and unique ID generation.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request start
        logger.info(f"Request started: {request.method} {request.url.path} [ID: {request_id}]")
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"Status: {response.status_code} Duration: {duration:.3f}s [ID: {request_id}]"
            )
            
            # Add custom headers
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Processing-Time"] = str(duration)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"Error: {str(e)} Duration: {duration:.3f}s [ID: {request_id}]"
            )
            raise e
