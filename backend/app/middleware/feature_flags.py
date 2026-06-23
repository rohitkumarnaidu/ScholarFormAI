# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Feature Flag Middleware — Injects feature flags into request state.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.feature_flags import get_feature_flag_service

logger = logging.getLogger(__name__)


class FeatureFlagMiddleware(BaseHTTPMiddleware):
    """
    Middleware that resolves feature flags for each request.

    Adds `request.state.feature_flags` dict with all resolved flags.
    Also adds `X-Feature-Flags` response header for debugging.
    """

    async def dispatch(self, request: Request, call_next):
        user_id = None
        try:
            # Extract user_id from auth if available
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # User is authenticated — could extract user_id from JWT
                pass
        except Exception:
            pass

        # Resolve all feature flags
        service = get_feature_flag_service()
        flags = service.get_all_flags(user_id)
        request.state.feature_flags = flags

        response = await call_next(request)

        # Add feature flags to response headers for debugging (dev only)
        if getattr(request.app, "debug", False):
            import json
            response.headers["X-Feature-Flags"] = json.dumps(flags)

        return response
