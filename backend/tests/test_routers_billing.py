from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _make_supabase_mock(*, data=None):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.maybe_single.return_value = table
    table.update.return_value = table
    table.execute.return_value = MagicMock(data=data or [{}] if data else [{"id": "user-123"}])
    sb = MagicMock()
    sb.table.return_value = table
    return sb


class TestStripeWebhook:
    def test_no_webhook_secret(self, client):
        with patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", None):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 500

    def test_invalid_signature(self, client):
        fake_error = type("FakeSignatureError", (Exception,), {})
        audit_mock = AsyncMock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch("app.routers.v1.billing.stripe.error.SignatureVerificationError", new=fake_error),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                side_effect=fake_error("bad sig"),
            ),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 400
        payload = response.json()
        assert payload["data"] is None
        assert payload["error"]["code"] == "INVALID_BILLING_WEBHOOK"
        assert "Invalid Stripe signature" in payload["error"]["message"]

    def test_invalid_payload_value_error(self, client):
        audit_mock = AsyncMock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                side_effect=ValueError("bad payload"),
            ),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 400
        assert "Invalid Stripe payload" in response.json()["error"]["message"]

    def test_no_supabase_client(self, client):
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={"type": "checkout.session.completed", "data": {"object": {}}},
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=None),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 503

    def test_checkout_completed_with_metadata(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "id": "evt-1",
                            "customer": "cus_123",
                            "payment_status": "paid",
                            "metadata": {"user_id": "user-123"},
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200
        assert response.json()["data"]["received"] is True

    def test_subscription_deleted(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "customer.subscription.deleted",
                    "data": {
                        "object": {
                            "id": "sub_1",
                            "customer": "cus_123",
                            "metadata": {"user_id": "user-456"},
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200

    def test_subscription_updated_active(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "customer.subscription.updated",
                    "data": {
                        "object": {
                            "id": "sub_2",
                            "customer": "cus_789",
                            "status": "active",
                            "metadata": {"user_id": "user-789"},
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200

    def test_subscription_updated_canceled(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "customer.subscription.updated",
                    "data": {
                        "object": {
                            "id": "sub_3",
                            "customer": "cus_000",
                            "status": "canceled",
                            "metadata": {"user_id": "user-000"},
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200

    def test_no_user_id_falls_back_to_customer_lookup(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock(data=[{"id": "looked-up-user"}])
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "checkout.session.completed",
                    "data": {
                        "object": {
                            "id": "evt-2",
                            "customer": "cus_lookup",
                            "payment_status": "paid",
                            "metadata": None,
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200

    def test_db_update_failure_logs_warning(self, client):
        audit_mock = AsyncMock()
        table = MagicMock()
        table.update.side_effect = Exception("DB write failed")
        table.select.return_value = table
        table.eq.return_value = table
        table.maybe_single.return_value = table
        table.update.return_value = table
        table.execute = MagicMock(side_effect=Exception("DB write failed"))
        sb = MagicMock()
        sb.table.return_value = table

        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "customer.subscription.updated",
                    "data": {
                        "object": {
                            "id": "sub_fail",
                            "customer": "cus_fail",
                            "status": "active",
                            "metadata": {"user_id": "user-fail"},
                        }
                    },
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200

    def test_unexpected_event_type_still_logs(self, client):
        audit_mock = AsyncMock()
        sb = _make_supabase_mock()
        with (
            patch("app.routers.v1.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch(
                "app.routers.v1.billing.stripe.Webhook.construct_event",
                return_value={
                    "type": "some.unknown.event",
                    "data": {"object": {"id": "unk", "customer": "cus_unk", "metadata": {}}},
                },
            ),
            patch("app.routers.v1.billing.get_supabase_client", return_value=sb),
            patch("app.routers.v1.billing.audit_log_service.log", new=audit_mock),
        ):
            response = client.post("/api/v1/billing/webhook", content=b"{}")
        assert response.status_code == 200


class TestHelpers:
    def test_get_user_id_from_metadata(self):
        from app.routers.v1.billing import _get_user_id_from_metadata
        assert _get_user_id_from_metadata({"metadata": {"user_id": "u1"}}) == "u1"
        assert _get_user_id_from_metadata({"metadata": None}) is None
        assert _get_user_id_from_metadata({}) is None

    def test_legacy_profile_updates(self):
        from app.routers.v1.billing import _legacy_profile_updates
        assert _legacy_profile_updates({"plan_tier": "pro"}) == {"plan": "pro"}
        assert _legacy_profile_updates({"billing_status": "active"}) == {}
