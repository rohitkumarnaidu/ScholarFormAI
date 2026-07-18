# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Webhook service for managing outgoing webhook subscriptions and dispatching events.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class WebhookService:

    def __init__(self):
        self._client = None

    def _get_client(self):
        from app.db.supabase_client import get_supabase_client
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def _utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _encrypt_secret(self, plaintext: str) -> str:
        from app.services.encryption_service import get_encryption_service
        svc = get_encryption_service()
        if svc is None:
            raise RuntimeError("Encryption service not available")
        return svc.encrypt(plaintext)

    def _decrypt_secret(self, ciphertext: str) -> str:
        from app.services.encryption_service import get_encryption_service
        svc = get_encryption_service()
        if svc is None:
            raise RuntimeError("Encryption service not available")
        return svc.decrypt(ciphertext)

    def _run_query(self, table_method):
        client = self._get_client()
        if client is None:
            raise RuntimeError("Supabase client not available.")
        return table_method(client).execute()

    def create_subscription(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = self._utc_now_iso()
        secret_encrypted = self._encrypt_secret(data.get("secret", "")) if data.get("secret") else ""

        payload = {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": data["name"],
            "url": data["url"],
            "events": json.dumps(data["events"]) if isinstance(data["events"], list) else data["events"],
            "secret": secret_encrypted,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        try:
            result = self._run_query(
                lambda c: c.table("webhook_subscriptions").insert(payload)
            )
            row = result.data[0] if result.data else payload
            from app.models.webhook import WebhookSubscription
            return WebhookSubscription.from_row(row)
        except Exception as exc:
            logger.error("Failed to create webhook subscription: %s", exc)
            raise

    def get_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            result = self._run_query(
                lambda c: c.table("webhook_subscriptions")
                .select("*").eq("user_id", user_id).order("created_at", desc=True)
            )
            rows = result.data if result.data else []
            from app.models.webhook import WebhookSubscription
            return [WebhookSubscription.from_row(r) for r in rows]
        except Exception as exc:
            logger.error("Failed to list webhook subscriptions: %s", exc)
            return []

    def get_subscription(self, user_id: str, sub_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self._run_query(
                lambda c: c.table("webhook_subscriptions")
                .select("*").eq("id", sub_id).maybe_single()
            )
            if not result or not result.data:
                return None
            row = result.data
            if str(row.get("user_id", "")) != user_id:
                return None
            from app.models.webhook import WebhookSubscription
            return WebhookSubscription.from_row(row)
        except Exception as exc:
            logger.error("Failed to get webhook subscription: %s", exc)
            return None

    def update_subscription(self, user_id: str, sub_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = self.get_subscription(user_id, sub_id)
        if existing is None:
            return None

        updates = {}
        if "name" in data:
            updates["name"] = data["name"]
        if "url" in data:
            updates["url"] = data["url"]
        if "events" in data:
            updates["events"] = json.dumps(data["events"]) if isinstance(data["events"], list) else data["events"]
        if "is_active" in data:
            updates["is_active"] = bool(data["is_active"])
        if "secret" in data and data["secret"]:
            updates["secret"] = self._encrypt_secret(data["secret"])

        updates["updated_at"] = self._utc_now_iso()

        if not updates:
            return existing

        try:
            result = self._run_query(
                lambda c: c.table("webhook_subscriptions")
                .update(updates).eq("id", sub_id)
            )
            row = result.data[0] if result.data else {**existing, **updates}
            from app.models.webhook import WebhookSubscription
            return WebhookSubscription.from_row(row)
        except Exception as exc:
            logger.error("Failed to update webhook subscription: %s", exc)
            raise

    def delete_subscription(self, user_id: str, sub_id: str) -> bool:
        existing = self.get_subscription(user_id, sub_id)
        if existing is None:
            return False

        updates = {"is_active": False, "updated_at": self._utc_now_iso()}

        try:
            self._run_query(
                lambda c: c.table("webhook_subscriptions")
                .update(updates).eq("id", sub_id)
            )
            return True
        except Exception as exc:
            logger.error("Failed to delete webhook subscription: %s", exc)
            return False

    def get_deliveries(self, user_id: str, sub_id: str) -> List[Dict[str, Any]]:
        sub = self.get_subscription(user_id, sub_id)
        if sub is None:
            return []

        try:
            result = self._run_query(
                lambda c: c.table("webhook_delivery_logs")
                .select("*").eq("subscription_id", sub_id).order("attempted_at", desc=True).limit(50)
            )
            rows = result.data if result.data else []
            from app.models.webhook import WebhookDeliveryLog
            return [WebhookDeliveryLog.from_row(r) for r in rows]
        except Exception as exc:
            logger.error("Failed to list delivery logs: %s", exc)
            return []

    def _sign_payload(self, payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def _deliver(self, url: str, payload: str, signature: str) -> Tuple[int, str]:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "User-Agent": "ScholarForm-Webhook/1.0",
                },
            )
            body = response.text
            return response.status_code, body

    def _calculate_retry_delay(self, attempt: int) -> int:
        return min(2 ** attempt * 60, 3600)

    async def dispatch_event(self, event_type: str, payload: Dict[str, Any], user_id: Optional[str] = None) -> int:
        import httpx

        def find_subs():
            client = self._get_client()
            if client is None:
                return []
            query = client.table("webhook_subscriptions").select("*").eq("is_active", True).contains("events", event_type)
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.execute()
            return result.data if result.data else []

        subs = await asyncio.to_thread(find_subs)
        if not subs:
            return 0

        payload_str = json.dumps(payload)
        delivered = 0

        for sub in subs:
            sub_id = str(sub.get("id", ""))
            encrypted_secret = str(sub.get("secret", ""))
            url = str(sub.get("url", ""))

            secret = ""
            if encrypted_secret:
                try:
                    secret = self._decrypt_secret(encrypted_secret)
                except Exception:
                    logger.warning("Failed to decrypt secret for subscription %s", sub_id)
                    continue

            signature = self._sign_payload(payload_str, secret) if secret else ""
            status_code = 0
            response_body = ""
            status = "failed"
            next_retry = None

            for attempt in range(3):
                try:
                    status_code, response_body = await self._deliver(url, payload_str, signature)
                    if 200 <= status_code < 300:
                        status = "success"
                        break
                    else:
                        delay = self._calculate_retry_delay(attempt + 1)
                        next_retry = datetime.now(timezone.utc).timestamp() + delay
                        if attempt < 2:
                            await asyncio.sleep(delay)
                except httpx.RequestError as exc:
                    response_body = str(exc)
                    delay = self._calculate_retry_delay(attempt + 1)
                    next_retry = datetime.now(timezone.utc).timestamp() + delay
                    if attempt < 2:
                        await asyncio.sleep(delay)

            log_entry = {
                "id": str(uuid4()),
                "subscription_id": sub_id,
                "event_type": event_type,
                "payload": payload_str,
                "status": status,
                "response_code": status_code,
                "response_body": response_body[:2000],
                "attempted_at": self._utc_now_iso(),
                "next_retry_at": next_retry,
            }

            def insert_log():
                client = self._get_client()
                if client is None:
                    raise RuntimeError("Supabase client not available.")
                return client.table("webhook_delivery_logs").insert(log_entry).execute()

            try:
                await asyncio.to_thread(insert_log)
            except Exception as exc:
                logger.error("Failed to persist delivery log: %s", exc)

            delivered += 1

        return delivered

webhook_service = WebhookService()
