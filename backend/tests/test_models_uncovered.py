import pytest
from sqlalchemy.orm import DeclarativeBase


class TestBase:
    def test_base_is_declarative_base(self):
        from app.db.base import Base
        assert issubclass(Base, DeclarativeBase)

    def test_base_can_be_instantiated(self):
        from app.db.base import Base
        instance = Base()
        assert isinstance(instance, Base)


class TestSuggestionModel:
    def test_tablename(self):
        from app.models.suggestion import Suggestion
        assert Suggestion.__tablename__ == "suggestions"

    def test_has_expected_columns(self):
        from app.models.suggestion import Suggestion
        assert hasattr(Suggestion, "id")
        assert hasattr(Suggestion, "user_id")
        assert hasattr(Suggestion, "document_id")
        assert hasattr(Suggestion, "session_id")
        assert hasattr(Suggestion, "original_text")
        assert hasattr(Suggestion, "suggested_text")
        assert hasattr(Suggestion, "suggestion_type")
        assert hasattr(Suggestion, "score")
        assert hasattr(Suggestion, "status")
        assert hasattr(Suggestion, "context")
        assert hasattr(Suggestion, "created_at")
        assert hasattr(Suggestion, "updated_at")
        assert hasattr(Suggestion, "accepted_at")

    def test_primary_key_is_id(self):
        from app.models.suggestion import Suggestion
        assert Suggestion.id.primary_key

    def test_user_id_not_nullable(self):
        from app.models.suggestion import Suggestion
        assert not Suggestion.user_id.nullable

    def test_score_default(self):
        from app.models.suggestion import Suggestion
        assert Suggestion.score.default.arg == 0.0

    def test_status_server_default(self):
        from app.models.suggestion import Suggestion
        assert str(Suggestion.status.server_default.arg) == "'pending'"


class TestWebhookSubscription:
    def test_tablename(self):
        from app.models.webhook import WebhookSubscription
        assert WebhookSubscription.__tablename__ == "webhook_subscriptions"

    def test_from_row_empty_dict(self):
        from app.models.webhook import WebhookSubscription
        result = WebhookSubscription.from_row({})
        assert result["id"] == ""
        assert result["user_id"] == ""
        assert result["name"] == ""
        assert result["url"] == ""
        assert result["events"] == []
        assert result["secret"] == ""
        assert result["is_active"] is True
        assert result["created_at"] == ""
        assert result["updated_at"] == ""

    def test_from_row_full_dict(self):
        from app.models.webhook import WebhookSubscription
        row = {
            "id": "sub-123",
            "user_id": "user-456",
            "name": "My Webhook",
            "url": "https://example.com/hook",
            "events": ["document.completed", "document.failed"],
            "secret": "s3cret!",
            "is_active": True,
            "created_at": "2026-01-15T10:00:00Z",
            "updated_at": "2026-01-15T12:00:00Z",
        }
        result = WebhookSubscription.from_row(row)
        assert result["id"] == "sub-123"
        assert result["user_id"] == "user-456"
        assert result["name"] == "My Webhook"
        assert result["url"] == "https://example.com/hook"
        assert result["events"] == ["document.completed", "document.failed"]
        assert result["secret"] == "s3cret!"
        assert result["is_active"] is True
        assert result["created_at"] == "2026-01-15T10:00:00Z"
        assert result["updated_at"] == "2026-01-15T12:00:00Z"

    def test_from_row_partial_dict(self):
        from app.models.webhook import WebhookSubscription
        row = {"id": "sub-789", "name": "Partial", "is_active": False}
        result = WebhookSubscription.from_row(row)
        assert result["id"] == "sub-789"
        assert result["user_id"] == ""
        assert result["name"] == "Partial"
        assert result["url"] == ""
        assert result["events"] == []
        assert result["secret"] == ""
        assert result["is_active"] is False
        assert result["created_at"] == ""
        assert result["updated_at"] == ""

    def test_from_row_boolean_coercion(self):
        from app.models.webhook import WebhookSubscription
        row_false = {"is_active": 0}
        assert WebhookSubscription.from_row(row_false)["is_active"] is False
        row_true = {"is_active": 1}
        assert WebhookSubscription.from_row(row_true)["is_active"] is True
        row_string = {"is_active": "false"}
        assert WebhookSubscription.from_row(row_string)["is_active"] is True

    def test_from_row_id_coerced_to_string(self):
        from app.models.webhook import WebhookSubscription
        row = {"id": 42, "user_id": 99}
        result = WebhookSubscription.from_row(row)
        assert result["id"] == "42"
        assert result["user_id"] == "99"


class TestWebhookDeliveryLog:
    def test_tablename(self):
        from app.models.webhook import WebhookDeliveryLog
        assert WebhookDeliveryLog.__tablename__ == "webhook_delivery_logs"

    def test_from_row_empty_dict(self):
        from app.models.webhook import WebhookDeliveryLog
        result = WebhookDeliveryLog.from_row({})
        assert result["id"] == ""
        assert result["subscription_id"] == ""
        assert result["event_type"] == ""
        assert result["payload"] == ""
        assert result["status"] == ""
        assert result["response_code"] == 0
        assert result["response_body"] == ""
        assert result["attempted_at"] == ""
        assert result["next_retry_at"] is None

    def test_from_row_full_dict(self):
        from app.models.webhook import WebhookDeliveryLog
        row = {
            "id": "log-001",
            "subscription_id": "sub-123",
            "event_type": "document.completed",
            "payload": '{"doc_id": "doc-1"}',
            "status": "delivered",
            "response_code": 200,
            "response_body": "OK",
            "attempted_at": "2026-01-15T10:00:00Z",
            "next_retry_at": "2026-01-15T11:00:00Z",
        }
        result = WebhookDeliveryLog.from_row(row)
        assert result["id"] == "log-001"
        assert result["subscription_id"] == "sub-123"
        assert result["event_type"] == "document.completed"
        assert result["payload"] == '{"doc_id": "doc-1"}'
        assert result["status"] == "delivered"
        assert result["response_code"] == 200
        assert result["response_body"] == "OK"
        assert result["attempted_at"] == "2026-01-15T10:00:00Z"
        assert result["next_retry_at"] == "2026-01-15T11:00:00Z"

    def test_from_row_partial_dict(self):
        from app.models.webhook import WebhookDeliveryLog
        row = {"id": "log-789", "status": "failed", "response_code": 500}
        result = WebhookDeliveryLog.from_row(row)
        assert result["id"] == "log-789"
        assert result["subscription_id"] == ""
        assert result["event_type"] == ""
        assert result["payload"] == ""
        assert result["status"] == "failed"
        assert result["response_code"] == 500
        assert result["response_body"] == ""
        assert result["attempted_at"] == ""
        assert result["next_retry_at"] is None

    def test_from_row_response_code_coercion(self):
        from app.models.webhook import WebhookDeliveryLog
        row = {"response_code": "404"}
        result = WebhookDeliveryLog.from_row(row)
        assert result["response_code"] == 404

    def test_from_row_missing_response_code_defaults_zero(self):
        from app.models.webhook import WebhookDeliveryLog
        result = WebhookDeliveryLog.from_row({})
        assert result["response_code"] == 0
