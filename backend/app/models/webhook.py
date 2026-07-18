# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Webhook models for managing outgoing webhook subscriptions and delivery logs.
"""


class WebhookSubscription:
    __tablename__ = "webhook_subscriptions"

    @classmethod
    def from_row(cls, row: dict) -> dict:
        return {
            "id": str(row.get("id", "")),
            "user_id": str(row.get("user_id", "")),
            "name": row.get("name", ""),
            "url": row.get("url", ""),
            "events": row.get("events", []),
            "secret": row.get("secret", ""),
            "is_active": bool(row.get("is_active", True)),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }


class WebhookDeliveryLog:
    __tablename__ = "webhook_delivery_logs"

    @classmethod
    def from_row(cls, row: dict) -> dict:
        return {
            "id": str(row.get("id", "")),
            "subscription_id": str(row.get("subscription_id", "")),
            "event_type": row.get("event_type", ""),
            "payload": row.get("payload", ""),
            "status": row.get("status", ""),
            "response_code": int(row.get("response_code", 0)),
            "response_body": row.get("response_body", ""),
            "attempted_at": row.get("attempted_at", ""),
            "next_retry_at": row.get("next_retry_at"),
        }
