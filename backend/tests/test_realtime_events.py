from datetime import UTC, datetime
from unittest.mock import patch


class TestRealtimeEvent:
    def test_default_construction(self):
        from app.realtime.events import RealtimeEvent

        event = RealtimeEvent(event_type="progress")
        assert event.event_type == "progress"
        assert event.job_id is None
        assert event.session_id is None
        assert event.request_id is None
        assert event.stage is None
        assert event.progress is None
        assert isinstance(event.timestamp, datetime)
        assert event.payload == {}

    def test_with_all_fields(self):
        from app.realtime.events import RealtimeEvent

        ts = datetime.now(UTC)
        event = RealtimeEvent(
            event_type="complete",
            job_id="job-1",
            session_id="sess-1",
            request_id="req-1",
            stage="export",
            progress=100,
            timestamp=ts,
            payload={"file": "output.docx"},
        )
        assert event.job_id == "job-1"
        assert event.progress == 100
        assert event.payload == {"file": "output.docx"}

    def test_timestamp_defaults_to_utc_now(self):
        from app.realtime.events import RealtimeEvent

        event = RealtimeEvent(event_type="test")
        assert event.timestamp.tzinfo == UTC


class TestMakeEvent:
    MODULE = "app.realtime.events"

    def test_basic_event(self):
        from app.realtime.events import make_event

        result = make_event("progress", job_id="job-1", progress=50)
        assert result["event_type"] == "progress"
        assert result["job_id"] == "job-1"
        assert result["progress"] == 50
        assert "timestamp" in result
        assert "request_id" in result

    def test_payload_as_kwarg(self):
        from app.realtime.events import make_event

        result = make_event("progress", payload={"key": "val"})
        assert result["payload"] == {"key": "val"}

    def test_custom_timestamp(self):
        from app.realtime.events import make_event

        ts = datetime(2026, 1, 1, tzinfo=UTC)
        result = make_event("test", timestamp=ts)
        assert result["timestamp"] == "2026-01-01T00:00:00+00:00"

    def test_request_id_from_context(self):
        with patch(f"{self.MODULE}.get_request_id_context", return_value="ctx-req-id"):
            from app.realtime.events import make_event

            result = make_event("test")
            assert result["request_id"] == "ctx-req-id"

    def test_request_id_from_kwargs_overrides_context(self):
        with patch(f"{self.MODULE}.get_request_id_context", return_value="ctx-req-id"):
            from app.realtime.events import make_event

            result = make_event("test", request_id="explicit-req-id")
            assert result["request_id"] == "explicit-req-id"

    def test_payload_none_becomes_empty_dict(self):
        from app.realtime.events import make_event

        result = make_event("test", payload=None)
        assert result["payload"] == {}

    def test_timestamp_isoformat(self):
        from app.realtime.events import make_event

        result = make_event("test")
        assert isinstance(result["timestamp"], str)
        assert "+" in result["timestamp"]
