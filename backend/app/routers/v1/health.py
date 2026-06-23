# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.services.health_checks import get_readiness_payload
from app.schemas.user import User
from app.utils.dependencies import require_admin_user
from app.utils.logging_context import bind_request_context

from ._helpers import build_error_response, build_success_response

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("")
async def health(request: Request):
    """Compatibility health endpoint for /api/v1/health."""
    return build_success_response(request, {"status": "alive"})


@router.get("/live")
async def live(request: Request):
    return build_success_response(request, {"status": "alive"})


@router.get("/ready")
async def ready(request: Request):
    try:
        payload, status_code = await get_readiness_payload()
    except Exception:
        logger.exception("Failed to build readiness payload")
        return build_error_response(
            request,
            status_code=500,
            code="READINESS_CHECK_FAILED",
            message="Failed to evaluate readiness state",
        )

    return build_success_response(request, payload, status_code=status_code)


@router.get("/admin")
async def admin_health(
    request: Request,
    _admin_user: User = Depends(require_admin_user),
):
    return build_success_response(request, {"status": "alive", "scope": "admin"})
