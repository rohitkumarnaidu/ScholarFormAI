from __future__ import annotations
import pytest
import logging


class TestLoggingContext:
    def test_bind_and_get_request_id(self):
        from app.utils.logging_context import bind_context, reset_context, get_request_id_context
        tokens = bind_context(request_id="req_123")
        assert get_request_id_context() == "req_123"
        reset_context(tokens)
        assert get_request_id_context() is None

    def test_bind_and_get_job_id(self):
        from app.utils.logging_context import bind_context, reset_context, get_job_id_context
        tokens = bind_context(job_id="job_456")
        assert get_job_id_context() == "job_456"
        reset_context(tokens)
        assert get_job_id_context() is None

    def test_bind_and_get_session_id(self):
        from app.utils.logging_context import bind_context, reset_context, get_session_id_context
        tokens = bind_context(session_id="sess_789")
        assert get_session_id_context() == "sess_789"
        reset_context(tokens)
        assert get_session_id_context() is None

    def test_log_context_manager(self):
        from app.utils.logging_context import log_context, get_request_id_context
        with log_context(request_id="ctx_req"):
            assert get_request_id_context() == "ctx_req"
        assert get_request_id_context() is None

    def test_log_extra(self):
        from app.utils.logging_context import log_extra, bind_context, reset_context
        tokens = bind_context(request_id="r1", job_id="j1")
        extra = log_extra()
        assert extra["request_id"] == "r1"
        assert extra["job_id"] == "j1"
        reset_context(tokens)

    def test_log_extra_with_overrides(self):
        from app.utils.logging_context import log_extra
        extra = log_extra(job_id="override_job")
        assert extra["job_id"] == "override_job"

    def test_log_context_filter_adds_fields(self):
        from app.utils.logging_context import LogContextFilter, bind_context, reset_context
        tokens = bind_context(request_id="req_filter", job_id="job_filter")
        filt = LogContextFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", (), None)
        assert filt.filter(record) is True
        assert record.request_id == "req_filter"
        assert record.job_id == "job_filter"
        reset_context(tokens)

    def test_log_context_filter_preserves_existing(self):
        from app.utils.logging_context import LogContextFilter
        filt = LogContextFilter()
        record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", (), None)
        record.request_id = "already_set"
        filt.filter(record)
        assert record.request_id == "already_set"

    def test_bind_with_no_args(self):
        from app.utils.logging_context import bind_context, reset_context
        tokens = bind_context()
        assert tokens == {}
        reset_context(tokens)  # should not raise

    def test_reset_with_empty_dict(self):
        from app.utils.logging_context import reset_context
        reset_context({})  # should not raise

    def test_log_context_no_args(self):
        from app.utils.logging_context import log_context
        with log_context():
            pass  # should not raise

    @pytest.mark.asyncio
    async def test_bind_request_context_generates_id(self):
        from app.utils.logging_context import bind_request_context
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.state.request_id = None
        conn.headers = {}
        agen = bind_request_context(conn)
        try:
            await anext(agen)
        except StopAsyncIteration:
            pass
        assert conn.state.request_id is not None

    @pytest.mark.asyncio
    async def test_bind_request_context_with_x_request_id(self):
        from app.utils.logging_context import bind_request_context
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.state.request_id = None
        conn.headers = {"x-request-id": "from-header"}
        agen = bind_request_context(conn)
        try:
            await anext(agen)
        except StopAsyncIteration:
            pass
        assert conn.state.request_id == "from-header"

    @pytest.mark.asyncio
    async def test_bind_request_context_existing_state_id(self):
        from app.utils.logging_context import bind_request_context
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.state.request_id = "state-id"
        conn.headers = {}
        agen = bind_request_context(conn)
        try:
            await anext(agen)
        except StopAsyncIteration:
            pass
        assert conn.state.request_id == "state-id"

    @pytest.mark.asyncio
    async def test_bind_request_context_with_aliases(self):
        from app.utils.logging_context import bind_request_context
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.state.request_id = None
        conn.headers = {}
        agen = bind_request_context(conn, jobId="alias_job")
        try:
            await anext(agen)
        except StopAsyncIteration:
            pass

    @pytest.mark.asyncio
    async def test_bind_request_context_with_doc_id(self):
        from app.utils.logging_context import bind_request_context
        from unittest.mock import MagicMock
        conn = MagicMock()
        conn.state.request_id = None
        conn.headers = {}
        agen = bind_request_context(conn, doc_id="doc_001")
        try:
            await anext(agen)
        except StopAsyncIteration:
            pass

    def test_extract_user_id_various_types(self):
        from app.utils.logging_context import extract_user_id
        class ObjWithId:
            id = "user_obj_123"
        class ObjWithoutId:
            name = "no_id"

        assert extract_user_id(None) is None
        assert extract_user_id("user_str_999") == "user_str_999"
        assert extract_user_id({"id": "dict_id_1"}) == "dict_id_1"
        assert extract_user_id(ObjWithId()) == "user_obj_123"
        assert extract_user_id(ObjWithoutId()) is None

    def test_user_id_context_binding(self):
        from app.utils.logging_context import log_context, get_user_id_context
        with log_context(user_id="user_ctx_456"):
            assert get_user_id_context() == "user_ctx_456"
        assert get_user_id_context() is None

    @pytest.mark.asyncio
    async def test_bind_request_context_starlette_request_without_auth_middleware(self):
        from starlette.requests import Request
        from app.utils.logging_context import bind_request_context, get_user_id_context
        request = Request({"type": "http", "headers": []})
        agen = bind_request_context(request)
        try:
            await anext(agen)
            assert get_user_id_context() is None
        except StopAsyncIteration:
            pass

    def test_extract_user_id_unauthenticated_user_and_objects_without_id(self):
        from starlette.authentication import UnauthenticatedUser
        from app.utils.logging_context import extract_user_id

        unauth_user = UnauthenticatedUser()
        assert extract_user_id(unauth_user) is None

        class CustomObjWithoutId:
            def __init__(self):
                self.name = "test"

        assert extract_user_id(CustomObjWithoutId()) is None

