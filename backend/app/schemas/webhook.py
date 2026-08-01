# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    events: list[str] = Field(..., min_length=1)
    secret: str | None = Field(default=None, max_length=512)


class WebhookSubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: HttpUrl | None = Field(default=None)
    events: list[str] | None = Field(default=None, min_length=1)
    is_active: bool | None = Field(default=None)


class WebhookSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str
    updated_at: str


class WebhookSubscriptionListResponse(BaseModel):
    subscriptions: list[WebhookSubscriptionResponse]
    total: int


class WebhookDeliveryResponse(BaseModel):
    id: str
    subscription_id: str
    event_type: str
    status: str
    response_code: int
    attempted_at: str


class WebhookTestPayload(BaseModel):
    event_type: str = Field(default="test.ping")
    payload: dict[str, Any] = Field(default_factory=lambda: {"message": "test"})
