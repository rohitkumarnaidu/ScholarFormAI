from datetime import UTC


class TestRealtimeEvent:
    def test_creates_event_with_required(self):
        from app.realtime.events import RealtimeEvent

        e = RealtimeEvent(event_type="test")
        assert e.event_type == "test"
        assert e.timestamp is not None

    def test_creates_event_with_all_fields(self):
        from app.realtime.events import RealtimeEvent

        e = RealtimeEvent(
            event_type="progress",
            job_id="j1",
            session_id="s1",
            stage="parsing",
            progress=50,
        )
        assert e.job_id == "j1"
        assert e.progress == 50

    def test_serializes_to_dict(self):
        from app.realtime.events import make_event

        event = make_event("progress", job_id="j1", progress=42)
        assert event["event_type"] == "progress"
        assert event["job_id"] == "j1"
        assert isinstance(event["timestamp"], str)

    def test_includes_request_id_when_available(self):
        from unittest.mock import patch

        from app.realtime.events import make_event

        with patch("app.realtime.events.get_request_id_context", return_value="req-123"):
            event = make_event("test")
        assert event["request_id"] == "req-123"

    def test_no_request_id_when_none(self):
        from unittest.mock import patch

        from app.realtime.events import make_event

        with patch("app.realtime.events.get_request_id_context", return_value=None):
            event = make_event("test", job_id="j1")
        assert event.get("request_id") is None

    def test_explicit_request_id_overrides(self):
        from app.realtime.events import make_event

        event = make_event("test", request_id="explicit-rid")
        assert event["request_id"] == "explicit-rid"

    def test_timestamp_can_be_overridden(self):
        from datetime import datetime

        from app.realtime.events import make_event

        ts = datetime(2026, 1, 1, tzinfo=UTC)
        event = make_event("test", timestamp=ts)
        assert event["timestamp"] == ts.isoformat()

    def test_empty_payload_defaults(self):
        from app.realtime.events import make_event

        event = make_event("test")
        assert event["payload"] == {}

    def test_payload_is_preserved(self):
        from app.realtime.events import make_event

        event = make_event("test", payload={"key": "value"})
        assert event["payload"] == {"key": "value"}
