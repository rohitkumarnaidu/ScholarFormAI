# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import hashlib
import hmac
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.user import User
from app.utils.dependencies import get_current_user


@pytest.fixture(autouse=True)
def bypass_csrf():
    with patch("app.middleware.csrf._is_exempt_path", return_value=True):
        yield

@pytest.fixture(autouse=True)
def mock_dns():
    with patch("socket.gethostbyname", return_value="8.8.8.8"):
        yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_user():
    user = User(id="user-123", email="user@example.com", role="authenticated")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def _mock_table_chain() -> MagicMock:
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    table.maybe_single.return_value = table
    table.contains.return_value = table
    table.limit = MagicMock(return_value=table)
    return table


# ─── Service Tests ────────────────────────────────────────────────────────────


class TestWebhookService:

    def test_create_subscription(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[{
            "id": "wh-1",
            "user_id": "user-123",
            "name": "My Webhook",
            "url": "https://example.com/hook",
            "events": ["document.completed", "document.failed"],
            "secret": "encrypted-secret",
            "is_active": True,
            "created_at": "2026-07-08T00:00:00Z",
            "updated_at": "2026-07-08T00:00:00Z",
        }])
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            with patch.object(svc, "_encrypt_secret", return_value="encrypted-secret"):
                result = svc.create_subscription(
                    user_id="user-123",
                    data={
                        "name": "My Webhook",
                        "url": "https://example.com/hook",
                        "events": ["document.completed", "document.failed"],
                        "secret": "my-secret",
                    },
                )

        assert result["id"] == "wh-1"
        assert result["name"] == "My Webhook"
        assert result["events"] == ["document.completed", "document.failed"]
        assert result["is_active"] is True

    def test_create_subscription_encrypts_secret(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[{
            "id": "wh-2",
            "user_id": "user-123",
            "name": "Secured Webhook",
            "url": "https://example.com/hook",
            "events": ["test.event"],
            "secret": "encrypted-abc123",
            "is_active": True,
            "created_at": "2026-07-08T00:00:00Z",
            "updated_at": "2026-07-08T00:00:00Z",
        }])
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        encrypt_mock = MagicMock(return_value="encrypted-abc123")
        with patch.object(svc, "_get_client", return_value=mock_sb):
            with patch.object(svc, "_encrypt_secret", encrypt_mock):
                svc.create_subscription(
                    user_id="user-123",
                    data={
                        "name": "Secured Webhook",
                        "url": "https://example.com/hook",
                        "events": ["test.event"],
                        "secret": "raw-secret",
                    },
                )

        encrypt_mock.assert_called_once_with("raw-secret")

    def test_get_subscriptions_empty(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[])
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.get_subscriptions(user_id="user-999")

        assert result == []

    def test_get_subscriptions_multiple(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[
            {"id": "wh-1", "user_id": "user-123", "name": "Webhook A", "url": "https://a.com", "events": ["e1"], "secret": "", "is_active": True, "created_at": "t1", "updated_at": "t1"},
            {"id": "wh-2", "user_id": "user-123", "name": "Webhook B", "url": "https://b.com", "events": ["e2"], "secret": "", "is_active": True, "created_at": "t2", "updated_at": "t2"},
        ])
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.get_subscriptions(user_id="user-123")

        assert len(result) == 2
        assert result[0]["name"] == "Webhook A"
        assert result[1]["name"] == "Webhook B"

    def test_get_subscription_ownership(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data={
            "id": "wh-1",
            "user_id": "user-other",
            "name": "Other's Webhook",
            "url": "https://other.com",
            "events": ["e1"],
            "secret": "",
            "is_active": True,
            "created_at": "t1",
            "updated_at": "t1",
        })
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.get_subscription(user_id="user-123", sub_id="wh-1")

        assert result is None

    def test_update_subscription_partial(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        existing = {"id": "wh-1", "user_id": "user-123", "name": "Old Name", "url": "https://old.com", "events": ["e1"], "secret": "", "is_active": True, "created_at": "t1", "updated_at": "t1"}

        mock_get_table = _mock_table_chain()
        mock_get_table.execute.return_value = SimpleNamespace(data=existing)

        mock_upd_table = _mock_table_chain()
        mock_upd_table.execute.return_value = SimpleNamespace(data=[{"id": "wh-1", "user_id": "user-123", "name": "New Name", "url": "https://old.com", "events": ["e1"], "secret": "", "is_active": True, "created_at": "t1", "updated_at": "t2"}])

        mock_sb = MagicMock()
        mock_sb.table = MagicMock(side_effect=[mock_get_table, mock_upd_table])

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.update_subscription(user_id="user-123", sub_id="wh-1", data={"name": "New Name"})

        assert result is not None
        assert result["name"] == "New Name"

    def test_update_subscription_not_found(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=None)
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.update_subscription(user_id="user-123", sub_id="wh-nonexistent", data={"name": "New"})

        assert result is None

    def test_delete_subscription_soft(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        existing = {"id": "wh-1", "user_id": "user-123", "name": "To Delete", "url": "https://del.com", "events": ["e1"], "secret": "", "is_active": True, "created_at": "t1", "updated_at": "t1"}

        mock_get_table = _mock_table_chain()
        mock_get_table.execute.return_value = SimpleNamespace(data=existing)

        mock_del_table = _mock_table_chain()
        mock_del_table.execute.return_value = SimpleNamespace(data=[{**existing, "is_active": False}])

        mock_sb = MagicMock()
        mock_sb.table = MagicMock(side_effect=[mock_get_table, mock_del_table])

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.delete_subscription(user_id="user-123", sub_id="wh-1")

        assert result is True

    def test_delete_subscription_not_found(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=None)
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.delete_subscription(user_id="user-123", sub_id="wh-nonexistent")

        assert result is False

    def test_sign_payload(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        payload = '{"event": "test"}'
        secret = "my-secret-key"

        signature = svc._sign_payload(payload, secret)

        expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        assert signature == expected

    def test_deliver_success(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            MockClient.return_value.__aenter__.return_value = mock_client

            status_code, body = asyncio.run(svc._deliver("https://example.com", '{"ok":true}', "sig123"))

        assert status_code == 200
        assert body == "OK"

    def test_dispatch_event_retries_on_failure(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        sub = {
            "id": "wh-1",
            "user_id": "user-123",
            "name": "Hook",
            "url": "https://example.com/hook",
            "events": ["test.event"],
            "secret": "",
            "is_active": True,
            "created_at": "t1",
            "updated_at": "t1",
        }

        find_table = _mock_table_chain()
        find_table.execute.return_value = SimpleNamespace(data=[sub])
        find_sb = MagicMock()
        find_sb.table.return_value = find_table

        log_table = _mock_table_chain()
        log_table.execute.return_value = SimpleNamespace(data=[{"id": "log-1"}])
        log_sb = MagicMock()
        log_sb.table.return_value = log_table


        with patch.object(svc, "_get_client") as mock_get:
            mock_get.side_effect = [find_sb, log_sb]
            with patch.object(svc, "_decrypt_secret", return_value="secret"):
                with patch.object(svc, "_deliver", new_callable=AsyncMock) as mock_deliver:
                    mock_deliver.side_effect = [
                        (500, "Server Error"),
                        (200, "OK"),
                    ]
                    with patch.object(svc, "_calculate_retry_delay", return_value=0):
                        result = asyncio.run(svc.dispatch_event("test.event", {"k": "v"}, user_id="user-123"))

        assert result == 1
        assert mock_deliver.call_count == 2

    def test_calculate_retry_delay(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        assert svc._calculate_retry_delay(0) == 60
        assert svc._calculate_retry_delay(1) == 120
        assert svc._calculate_retry_delay(2) == 240
        assert svc._calculate_retry_delay(5) == 1920
        assert svc._calculate_retry_delay(6) == 3600
        assert svc._calculate_retry_delay(10) == 3600

    def test_dispatch_event_matches_events(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        sub = {
            "id": "wh-1",
            "user_id": "user-123",
            "name": "Doc Hook",
            "url": "https://example.com/hook",
            "events": ["document.completed", "document.failed"],
            "secret": "",
            "is_active": True,
            "created_at": "t1",
            "updated_at": "t1",
        }

        find_table = _mock_table_chain()
        find_table.execute.return_value = SimpleNamespace(data=[sub])
        find_sb = MagicMock()
        find_sb.table.return_value = find_table

        log_table = _mock_table_chain()
        log_table.execute.return_value = SimpleNamespace(data=[{"id": "log-1"}])
        log_sb = MagicMock()
        log_sb.table.return_value = log_table

        with patch.object(svc, "_get_client") as mock_get:
            mock_get.side_effect = [find_sb, log_sb]
            with patch.object(svc, "_decrypt_secret", return_value="secret"):
                with patch.object(svc, "_deliver", new_callable=AsyncMock) as mock_deliver:
                    mock_deliver.return_value = (200, "OK")
                    result = asyncio.run(svc.dispatch_event("document.completed", {"doc_id": "123"}, user_id="user-123"))

        assert result == 1
        mock_deliver.assert_called_once()

    def test_dispatch_event_no_matching_subs(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        find_table = _mock_table_chain()
        find_table.execute.return_value = SimpleNamespace(data=[])
        find_sb = MagicMock()
        find_sb.table.return_value = find_table

        with patch.object(svc, "_get_client", return_value=find_sb):
            result = asyncio.run(svc.dispatch_event("some.event", {"key": "val"}, user_id="user-123"))

        assert result == 0

    def test_get_deliveries(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[
            {"id": "log-1", "subscription_id": "wh-1", "event_type": "e1", "payload": "{}", "status": "success", "response_code": 200, "response_body": "OK", "attempted_at": "t1", "next_retry_at": None},
        ])

        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            with patch.object(svc, "get_subscription", return_value={"id": "wh-1", "user_id": "user-123"}):
                result = svc.get_deliveries(user_id="user-123", sub_id="wh-1")

        assert len(result) == 1
        assert result[0]["status"] == "success"

    def test_get_deliveries_no_sub(self):
        from app.services.webhook_service import WebhookService
        svc = WebhookService()

        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=None)
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch.object(svc, "_get_client", return_value=mock_sb):
            result = svc.get_deliveries(user_id="user-123", sub_id="wh-nonexistent")

        assert result == []


# ─── Router Tests ─────────────────────────────────────────────────────────────


class TestWebhookRouter:

    def test_create_webhook_endpoint(self, client, authenticated_user):
        mock_table = _mock_table_chain()
        mock_table.execute.return_value = SimpleNamespace(data=[{
            "id": "wh-1",
            "user_id": str(authenticated_user.id),
            "name": "My Hook",
            "url": "https://example.com/hook",
            "events": ["doc.completed"],
            "secret": "encrypted",
            "is_active": True,
            "created_at": "2026-07-08T00:00:00Z",
            "updated_at": "2026-07-08T00:00:00Z",
        }])
        mock_sb = MagicMock()
        mock_sb.table = MagicMock(return_value=mock_table)

        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.create_subscription.return_value = {
                "id": "wh-1",
                "user_id": str(authenticated_user.id),
                "name": "My Hook",
                "url": "https://example.com/hook",
                "events": ["doc.completed"],
                "is_active": True,
                "created_at": "t1",
                "updated_at": "t1",
            }
            response = client.post(
                "/api/v1/webhooks",
                json={
                    "name": "My Hook",
                    "url": "https://example.com/hook",
                    "events": ["doc.completed"],
                },
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["name"] == "My Hook"

    def test_create_webhook_unauthenticated(self, client):
        response = client.post(
            "/api/v1/webhooks",
            json={"name": "Hook", "url": "https://ex.com/hook", "events": ["e1"]},
        )
        assert response.status_code == 401

    def test_create_webhook_invalid_url(self, client, authenticated_user):
        response = client.post(
            "/api/v1/webhooks",
            json={"name": "Hook", "url": "not-a-url", "events": ["e1"]},
        )
        assert response.status_code == 422

    def test_create_webhook_empty_events(self, client, authenticated_user):
        response = client.post(
            "/api/v1/webhooks",
            json={"name": "Hook", "url": "https://ex.com/hook", "events": []},
        )
        assert response.status_code == 422

    def test_list_webhooks_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.get_subscriptions.return_value = []
            response = client.get("/api/v1/webhooks")

        assert response.status_code == 200
        payload = response.json()
        assert payload["data"]["subscriptions"] == []

    def test_list_webhooks_unauthenticated(self, client):
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 401

    def test_get_webhook_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.get_subscription.return_value = {
                "id": "wh-1",
                "user_id": str(authenticated_user.id),
                "name": "My Hook",
                "url": "https://ex.com/hook",
                "events": ["e1"],
                "is_active": True,
                "created_at": "t1",
                "updated_at": "t1",
            }
            response = client.get("/api/v1/webhooks/wh-1")

        assert response.status_code == 200
        assert response.json()["data"]["id"] == "wh-1"

    def test_get_webhook_not_found(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.get_subscription.return_value = None
            response = client.get("/api/v1/webhooks/wh-nonexistent")

        assert response.status_code == 404

    def test_update_webhook_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.update_subscription.return_value = {
                "id": "wh-1",
                "user_id": str(authenticated_user.id),
                "name": "Updated Hook",
                "url": "https://ex.com/hook",
                "events": ["e1"],
                "is_active": True,
                "created_at": "t1",
                "updated_at": "t2",
            }
            response = client.put(
                "/api/v1/webhooks/wh-1",
                json={"name": "Updated Hook"},
            )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Hook"

    def test_update_webhook_not_found(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.update_subscription.return_value = None
            response = client.put(
                "/api/v1/webhooks/wh-nonexistent",
                json={"name": "Nope"},
            )

        assert response.status_code == 404

    def test_update_webhook_empty_body(self, client, authenticated_user):
        response = client.put(
            "/api/v1/webhooks/wh-1",
            json={},
        )
        assert response.status_code == 422

    def test_delete_webhook_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.delete_subscription.return_value = True
            response = client.delete("/api/v1/webhooks/wh-1")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "deleted"

    def test_delete_webhook_not_found(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.delete_subscription.return_value = False
            response = client.delete("/api/v1/webhooks/wh-nonexistent")

        assert response.status_code == 404

    def test_test_dispatch_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.dispatch_event = AsyncMock(return_value=2)
            response = client.post(
                "/api/v1/webhooks/test",
                json={"event_type": "test.ping", "payload": {"msg": "hello"}},
            )

        assert response.status_code == 200
        assert response.json()["data"]["delivered_to"] == 2

    def test_list_deliveries_endpoint(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.get_deliveries.return_value = [
                {"id": "log-1", "subscription_id": "wh-1", "event_type": "e1", "status": "success", "response_code": 200, "attempted_at": "t1"},
            ]
            response = client.get("/api/v1/webhooks/wh-1/deliveries")

        assert response.status_code == 200
        assert len(response.json()["data"]["deliveries"]) == 1

    def test_list_deliveries_empty(self, client, authenticated_user):
        with patch("app.routers.v1.webhooks.webhook_service") as mock_svc:
            mock_svc.get_deliveries.return_value = []
            response = client.get("/api/v1/webhooks/wh-1/deliveries")

        assert response.status_code == 200
        assert response.json()["data"]["total"] == 0

    def test_get_webhook_unauthenticated(self, client):
        response = client.get("/api/v1/webhooks/wh-1")
        assert response.status_code == 401

    def test_update_webhook_unauthenticated(self, client):
        response = client.put("/api/v1/webhooks/wh-1", json={"name": "X"})
        assert response.status_code == 401

    def test_delete_webhook_unauthenticated(self, client):
        response = client.delete("/api/v1/webhooks/wh-1")
        assert response.status_code == 401

    def test_test_dispatch_unauthenticated(self, client):
        response = client.post("/api/v1/webhooks/test", json={"event_type": "ping", "payload": {}})
        assert response.status_code == 401

    def test_list_deliveries_unauthenticated(self, client):
        response = client.get("/api/v1/webhooks/wh-1/deliveries")
        assert response.status_code == 401

    def test_create_webhook_long_name(self, client, authenticated_user):
        response = client.post(
            "/api/v1/webhooks",
            json={"name": "x" * 201, "url": "https://ex.com/hook", "events": ["e1"]},
        )
        assert response.status_code == 422
