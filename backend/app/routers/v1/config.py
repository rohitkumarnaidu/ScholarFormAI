# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.core.config import settings
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("")
async def get_public_config(request: Request) -> Dict[str, Any]:
    """Return public application configuration and settings."""

    async def operation():
        return {
            "environment": getattr(settings, "ENVIRONMENT", "production"),
            "version": getattr(settings, "VERSION", "1.0.0"),
            "api_prefix": getattr(settings, "API_PREFIX", "/api/v1"),
            "default_style": getattr(settings, "DEFAULT_STYLE", "apa"),
            "max_upload_size": getattr(settings, "MAX_UPLOAD_SIZE", 10485760),
            "allowed_origins": getattr(settings, "ALLOWED_ORIGINS", []),
            "rate_limit_default": getattr(settings, "RATE_LIMIT_DEFAULT", 60),
            "temp_file_ttl": getattr(settings, "TEMP_FILE_TTL", 3600),
            "prometheus_enabled": getattr(settings, "PROMETHEUS_ENABLED", True),
        }

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="config get",
    )
