import pytest
from pydantic import ValidationError


class TestCreateSessionRequest:
    def test_defaults(self):
        from app.schemas.generator_session import CreateSessionRequest
        req = CreateSessionRequest()
        assert req.session_type == "multi_doc"
        assert req.config == {}
        assert req.template == "none"

    def test_agent_session_type(self):
        from app.schemas.generator_session import CreateSessionRequest
        req = CreateSessionRequest(session_type="agent")
        assert req.session_type == "agent"

    def test_with_config_and_template(self):
        from app.schemas.generator_session import CreateSessionRequest
        req = CreateSessionRequest(
            session_type="multi_doc",
            config={"model": "gpt-4", "temperature": 0.7},
            template="ieee",
        )
        assert req.config == {"model": "gpt-4", "temperature": 0.7}
        assert req.template == "ieee"

    def test_invalid_session_type(self):
        from app.schemas.generator_session import CreateSessionRequest
        with pytest.raises(ValidationError):
            CreateSessionRequest(session_type="invalid_type")

    def test_invalid_config_type(self):
        from app.schemas.generator_session import CreateSessionRequest
        with pytest.raises(ValidationError):
            CreateSessionRequest(config="not-a-dict")


class TestSessionResponse:
    def test_required_fields(self):
        from app.schemas.generator_session import SessionResponse
        resp = SessionResponse(id="sess-1", status="active", session_type="multi_doc")
        assert resp.id == "sess-1"
        assert resp.status == "active"
        assert resp.session_type == "multi_doc"

    def test_defaults(self):
        from app.schemas.generator_session import SessionResponse
        resp = SessionResponse(id="sess-1", status="active", session_type="multi_doc")
        assert resp.config == {}
        assert resp.outline is None
        assert resp.created_at is None
        assert resp.updated_at is None

    def test_with_all_fields(self):
        from datetime import datetime
        from app.schemas.generator_session import SessionResponse
        now = datetime.now()
        resp = SessionResponse(
            id="sess-1",
            status="completed",
            session_type="agent",
            config={"key": "val"},
            outline={"sections": ["intro"]},
            created_at=now,
            updated_at=now,
        )
        assert resp.config == {"key": "val"}
        assert resp.outline == {"sections": ["intro"]}
        assert resp.created_at == now
        assert resp.updated_at == now

    def test_outline_as_list(self):
        from app.schemas.generator_session import SessionResponse
        resp = SessionResponse(
            id="sess-1", status="active", session_type="multi_doc",
            outline=["section1", "section2"],
        )
        assert resp.outline == ["section1", "section2"]

    def test_missing_id_fails(self):
        from app.schemas.generator_session import SessionResponse
        with pytest.raises(ValidationError):
            SessionResponse(status="active", session_type="multi_doc")

    def test_missing_status_fails(self):
        from app.schemas.generator_session import SessionResponse
        with pytest.raises(ValidationError):
            SessionResponse(id="sess-1", session_type="multi_doc")


class TestMessageRequest:
    def test_required_fields(self):
        from app.schemas.generator_session import MessageRequest
        req = MessageRequest(content="Hello")
        assert req.content == "Hello"

    def test_default_model(self):
        from app.schemas.generator_session import MessageRequest
        req = MessageRequest(content="Hello")
        assert req.model is None

    def test_with_model(self):
        from app.schemas.generator_session import MessageRequest
        req = MessageRequest(content="Summarize", model="gpt-4")
        assert req.model == "gpt-4"

    def test_empty_content(self):
        from app.schemas.generator_session import MessageRequest
        req = MessageRequest(content="")
        assert req.content == ""

    def test_missing_content_fails(self):
        from app.schemas.generator_session import MessageRequest
        with pytest.raises(ValidationError):
            MessageRequest()

    def test_non_string_content_fails(self):
        from app.schemas.generator_session import MessageRequest
        with pytest.raises(ValidationError):
            MessageRequest(content=123)


class TestMessageResponse:
    def test_required_fields(self):
        from app.schemas.generator_session import MessageResponse
        resp = MessageResponse(role="assistant", content="Here is the result")
        assert resp.role == "assistant"
        assert resp.content == "Here is the result"

    def test_defaults(self):
        from app.schemas.generator_session import MessageResponse
        resp = MessageResponse(role="user", content="Hi")
        assert resp.sources == []
        assert resp.created_at is None

    def test_with_sources(self):
        from app.schemas.generator_session import MessageResponse
        sources = [{"doc_id": "123", "page": 5}]
        resp = MessageResponse(role="assistant", content="Answer", sources=sources)
        assert resp.sources == sources

    def test_with_created_at(self):
        from datetime import datetime
        from app.schemas.generator_session import MessageResponse
        now = datetime.now()
        resp = MessageResponse(role="assistant", content="Answer", created_at=now)
        assert resp.created_at == now

    def test_missing_role_fails(self):
        from app.schemas.generator_session import MessageResponse
        with pytest.raises(ValidationError):
            MessageResponse(content="Answer")

    def test_missing_content_fails(self):
        from app.schemas.generator_session import MessageResponse
        with pytest.raises(ValidationError):
            MessageResponse(role="assistant")

    def test_invalid_sources_type(self):
        from app.schemas.generator_session import MessageResponse
        with pytest.raises(ValidationError):
            MessageResponse(role="assistant", content="text", sources="not-a-list")


class TestStageEvent:
    def test_required_fields(self):
        from datetime import datetime
        from app.schemas.generator_session import StageEvent
        now = datetime.now()
        event = StageEvent(stage="writing", progress=50, message="Writing section 2", timestamp=now)
        assert event.stage == "writing"
        assert event.progress == 50
        assert event.message == "Writing section 2"
        assert event.timestamp == now

    def test_progress_zero(self):
        from datetime import datetime
        from app.schemas.generator_session import StageEvent
        event = StageEvent(stage="planning", progress=0, message="Starting", timestamp=datetime.now())
        assert event.progress == 0

    def test_progress_hundred(self):
        from datetime import datetime
        from app.schemas.generator_session import StageEvent
        event = StageEvent(stage="complete", progress=100, message="Done", timestamp=datetime.now())
        assert event.progress == 100

    def test_missing_stage_fails(self):
        from datetime import datetime
        from app.schemas.generator_session import StageEvent
        with pytest.raises(ValidationError):
            StageEvent(progress=50, message="test", timestamp=datetime.now())

    def test_missing_timestamp_fails(self):
        from app.schemas.generator_session import StageEvent
        with pytest.raises(ValidationError):
            StageEvent(stage="writing", progress=50, message="test")

    def test_non_integer_progress_fails(self):
        from datetime import datetime
        from app.schemas.generator_session import StageEvent
        with pytest.raises(ValidationError):
            StageEvent(stage="writing", progress="fifty", message="test", timestamp=datetime.now())
