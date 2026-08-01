# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request

from app.schemas.user import User
from app.services.activity_service import activity_service
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("/recent")
async def get_recent_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        activities = await activity_service.get_recent_activities(
            user_id=str(current_user.id),
            limit=limit,
        )
        return {
            "activities": activities,
            "total": len(activities),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="activity recent",
    )


@router.get("/summary")
async def get_activity_summary(
    request: Request,
    period: str = Query("7d", pattern="^(7d|30d|90d|all)$"),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        summary = await activity_service.get_activity_summary(
            user_id=str(current_user.id),
            period=period,
        )
        return summary

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="activity summary",
    )
