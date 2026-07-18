# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    events: List[str] = Field(..., min_length=1)
    secret: Optional[str] = Field(default=None, max_length=512)


class WebhookSubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    url: Optional[HttpUrl] = Field(default=None)
    events: Optional[List[str]] = Field(default=None, min_length=1)
    is_active: Optional[bool] = Field(default=None)


class WebhookSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    url: str
    events: List[str]
    is_active: bool
    created_at: str
    updated_at: str


class WebhookSubscriptionListResponse(BaseModel):
    subscriptions: List[WebhookSubscriptionResponse]
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
    payload: Dict[str, Any] = Field(default_factory=lambda: {"message": "test"})
