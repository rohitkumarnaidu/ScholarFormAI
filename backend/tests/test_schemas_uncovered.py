import pytest
from pydantic import ValidationError


class TestPaginationSchemas:
    def test_cursor_page_defaults(self):
        from app.schemas.pagination import CursorPage
        page = CursorPage()
        assert page.items == []
        assert page.next_cursor is None
        assert page.has_more is False
        assert page.total is None

    def test_cursor_page_with_items(self):
        from app.schemas.pagination import CursorPage
        page = CursorPage(items=["a", "b"], has_more=True, total=10)
        assert page.items == ["a", "b"]
        assert page.has_more is True
        assert page.total == 10

    def test_cursor_page_with_cursor(self):
        from app.schemas.pagination import CursorPage
        page = CursorPage(next_cursor="abc123")
        assert page.next_cursor == "abc123"

    def test_cursor_page_with_integer_items(self):
        from app.schemas.pagination import CursorPage
        page = CursorPage(items=[1, 2, 3])
        assert page.items == [1, 2, 3]

    def test_cursor_page_zero_total(self):
        from app.schemas.pagination import CursorPage
        page = CursorPage(total=0)
        assert page.total == 0

    def test_pagination_params_defaults(self):
        from app.schemas.pagination import PaginationParams
        params = PaginationParams()
        assert params.cursor is None
        assert params.limit == 50
        assert params.order_by == "created_at"
        assert params.order_dir == "desc"

    def test_pagination_params_custom(self):
        from app.schemas.pagination import PaginationParams
        params = PaginationParams(cursor="cursor123", limit=25, order_by="name", order_dir="asc")
        assert params.cursor == "cursor123"
        assert params.limit == 25
        assert params.order_by == "name"
        assert params.order_dir == "asc"

    def test_pagination_params_limit_min(self):
        from app.schemas.pagination import PaginationParams
        params = PaginationParams(limit=1)
        assert params.limit == 1

    def test_pagination_params_limit_max(self):
        from app.schemas.pagination import PaginationParams
        params = PaginationParams(limit=100)
        assert params.limit == 100

    def test_pagination_params_limit_too_low(self):
        from app.schemas.pagination import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

    def test_pagination_params_limit_too_high(self):
        from app.schemas.pagination import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)

    def test_pagination_params_limit_negative(self):
        from app.schemas.pagination import PaginationParams
        with pytest.raises(ValidationError):
            PaginationParams(limit=-5)


class TestWebhookSchemas:
    def test_webhook_subscription_create_valid(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        sub = WebhookSubscriptionCreate(
            name="My Webhook",
            url="https://example.com/hook",
            events=["document.created"],
        )
        assert sub.name == "My Webhook"
        assert str(sub.url) == "https://example.com/hook"
        assert sub.events == ["document.created"]
        assert sub.secret is None

    def test_webhook_subscription_create_with_secret(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        sub = WebhookSubscriptionCreate(
            name="My Webhook",
            url="https://example.com/hook",
            events=["document.created"],
            secret="my-secret-key",
        )
        assert sub.secret == "my-secret-key"

    def test_webhook_subscription_create_multiple_events(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        sub = WebhookSubscriptionCreate(
            name="Multi Event",
            url="https://example.com/hook",
            events=["document.created", "document.updated", "document.deleted"],
        )
        assert len(sub.events) == 3

    def test_webhook_subscription_create_empty_name(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(name="", url="https://example.com/hook", events=["doc.created"])

    def test_webhook_subscription_create_name_too_long(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(name="x" * 201, url="https://example.com/hook", events=["doc.created"])

    def test_webhook_subscription_create_name_max_length(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        sub = WebhookSubscriptionCreate(name="x" * 200, url="https://example.com/hook", events=["doc.created"])
        assert len(sub.name) == 200

    def test_webhook_subscription_create_invalid_url(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(name="Hook", url="not-a-url", events=["doc.created"])

    def test_webhook_subscription_create_empty_events(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(name="Hook", url="https://example.com/hook", events=[])

    def test_webhook_subscription_create_secret_too_long(self):
        from app.schemas.webhook import WebhookSubscriptionCreate
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(
                name="Hook",
                url="https://example.com/hook",
                events=["doc.created"],
                secret="x" * 513,
            )

    def test_webhook_subscription_update_empty(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        update = WebhookSubscriptionUpdate()
        assert update.name is None
        assert update.url is None
        assert update.events is None
        assert update.is_active is None

    def test_webhook_subscription_update_all_fields(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        update = WebhookSubscriptionUpdate(
            name="Updated Hook",
            url="https://example.com/updated",
            events=["document.updated"],
            is_active=False,
        )
        assert update.name == "Updated Hook"
        assert str(update.url) == "https://example.com/updated"
        assert update.events == ["document.updated"]
        assert update.is_active is False

    def test_webhook_subscription_update_partial_name(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        update = WebhookSubscriptionUpdate(name="Just Name")
        assert update.name == "Just Name"
        assert update.url is None

    def test_webhook_subscription_update_empty_name(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        with pytest.raises(ValidationError):
            WebhookSubscriptionUpdate(name="")

    def test_webhook_subscription_update_name_too_long(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        with pytest.raises(ValidationError):
            WebhookSubscriptionUpdate(name="x" * 201)

    def test_webhook_subscription_update_empty_events(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        with pytest.raises(ValidationError):
            WebhookSubscriptionUpdate(events=[])

    def test_webhook_subscription_update_invalid_url(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        with pytest.raises(ValidationError):
            WebhookSubscriptionUpdate(url="bad-url")

    def test_webhook_subscription_update_toggle_active(self):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        update = WebhookSubscriptionUpdate(is_active=True)
        assert update.is_active is True

    def test_webhook_subscription_response_valid(self):
        from app.schemas.webhook import WebhookSubscriptionResponse
        resp = WebhookSubscriptionResponse(
            id="sub-1",
            user_id="user-1",
            name="My Hook",
            url="https://example.com/hook",
            events=["doc.created"],
            is_active=True,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
        )
        assert resp.id == "sub-1"
        assert resp.is_active is True
        assert resp.events == ["doc.created"]

    def test_webhook_subscription_response_inactive(self):
        from app.schemas.webhook import WebhookSubscriptionResponse
        resp = WebhookSubscriptionResponse(
            id="sub-2",
            user_id="user-2",
            name="Inactive Hook",
            url="https://example.com/hook",
            events=["doc.deleted"],
            is_active=False,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
        )
        assert resp.is_active is False

    def test_webhook_subscription_list_response_empty(self):
        from app.schemas.webhook import WebhookSubscriptionListResponse
        resp = WebhookSubscriptionListResponse(subscriptions=[], total=0)
        assert resp.subscriptions == []
        assert resp.total == 0

    def test_webhook_subscription_list_response_with_items(self):
        from app.schemas.webhook import WebhookSubscriptionListResponse, WebhookSubscriptionResponse
        sub = WebhookSubscriptionResponse(
            id="sub-1",
            user_id="user-1",
            name="Hook",
            url="https://example.com/hook",
            events=["doc.created"],
            is_active=True,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
        )
        resp = WebhookSubscriptionListResponse(subscriptions=[sub], total=1)
        assert len(resp.subscriptions) == 1
        assert resp.total == 1

    def test_webhook_delivery_response_valid(self):
        from app.schemas.webhook import WebhookDeliveryResponse
        resp = WebhookDeliveryResponse(
            id="del-1",
            subscription_id="sub-1",
            event_type="document.created",
            status="delivered",
            response_code=200,
            attempted_at="2026-01-01T00:00:00Z",
        )
        assert resp.id == "del-1"
        assert resp.status == "delivered"
        assert resp.response_code == 200

    def test_webhook_delivery_response_error_status(self):
        from app.schemas.webhook import WebhookDeliveryResponse
        resp = WebhookDeliveryResponse(
            id="del-2",
            subscription_id="sub-1",
            event_type="document.created",
            status="failed",
            response_code=500,
            attempted_at="2026-01-01T00:00:00Z",
        )
        assert resp.status == "failed"
        assert resp.response_code == 500

    def test_webhook_test_payload_defaults(self):
        from app.schemas.webhook import WebhookTestPayload
        payload = WebhookTestPayload()
        assert payload.event_type == "test.ping"
        assert payload.payload == {"message": "test"}

    def test_webhook_test_payload_custom(self):
        from app.schemas.webhook import WebhookTestPayload
        custom_data = {"foo": "bar", "count": 42}
        payload = WebhookTestPayload(event_type="custom.event", payload=custom_data)
        assert payload.event_type == "custom.event"
        assert payload.payload == {"foo": "bar", "count": 42}

    def test_webhook_test_payload_custom_default_unchanged(self):
        from app.schemas.webhook import WebhookTestPayload
        payload = WebhookTestPayload(event_type="custom.event")
        assert payload.event_type == "custom.event"
        assert payload.payload == {"message": "test"}
