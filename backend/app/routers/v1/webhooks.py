# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.schemas.user import User
from app.schemas.webhook import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    WebhookTestPayload,
)
from app.services.webhook_service import webhook_service
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.post("", status_code=201)
async def create_webhook(
    request: Request,
    data: WebhookSubscriptionCreate,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        result = webhook_service.create_subscription(
            user_id=str(current_user.id),
            data=data.model_dump(),
        )
        return result

    return await run_enveloped(
        request,
        operation,
        success_status_code=201,
        code_map={401: "UNAUTHORIZED", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="create webhook",
    )


@router.get("")
async def list_webhooks(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        subscriptions = webhook_service.get_subscriptions(user_id=str(current_user.id))
        return {
            "subscriptions": subscriptions,
            "total": len(subscriptions),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="list webhooks",
    )


@router.get("/{sub_id}")
async def get_webhook(
    request: Request,
    sub_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        sub = webhook_service.get_subscription(
            user_id=str(current_user.id),
            sub_id=sub_id,
        )
        if sub is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return sub

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 404: "NOT_FOUND", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="get webhook",
    )


@router.put("/{sub_id}")
async def update_webhook(
    request: Request,
    sub_id: str,
    data: WebhookSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=422, detail="No fields to update")

        result = webhook_service.update_subscription(
            user_id=str(current_user.id),
            sub_id=sub_id,
            data=updates,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return result

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 404: "NOT_FOUND", 422: "VALIDATION_ERROR", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="update webhook",
    )


@router.delete("/{sub_id}")
async def delete_webhook(
    request: Request,
    sub_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        deleted = webhook_service.delete_subscription(
            user_id=str(current_user.id),
            sub_id=sub_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return {"status": "deleted"}

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 404: "NOT_FOUND", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="delete webhook",
    )


@router.post("/test")
async def test_webhook(
    request: Request,
    data: WebhookTestPayload,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        delivered = await webhook_service.dispatch_event(
            event_type=data.event_type,
            payload=data.payload,
            user_id=str(current_user.id),
        )
        return {
            "event_type": data.event_type,
            "delivered_to": delivered,
            "message": f"Event dispatched to {delivered} subscription(s)",
        }

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="test webhook",
    )


@router.get("/{sub_id}/deliveries")
async def list_deliveries(
    request: Request,
    sub_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        deliveries = webhook_service.get_deliveries(
            user_id=str(current_user.id),
            sub_id=sub_id,
        )
        return {
            "deliveries": deliveries,
            "total": len(deliveries),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED", 404: "NOT_FOUND", 503: "DATABASE_UNAVAILABLE"},
        logger=logger,
        operation_name="list deliveries",
    )
