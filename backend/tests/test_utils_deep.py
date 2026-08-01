from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_logging_contexts():
    from app.utils.logging_context import _job_id_ctx, _request_id_ctx, _session_id_ctx

    _request_id_ctx.set(None)
    _job_id_ctx.set(None)
    _session_id_ctx.set(None)
    return


# ═══════════════════════════════════════════════════════════════════
# Logging Context (no prior test file exists)
# ═══════════════════════════════════════════════════════════════════

MODULE = "app.utils.logging_context"


class TestBindContext:
    def test_binds_all_three(self):
        from app.utils.logging_context import _job_id_ctx, _request_id_ctx, _session_id_ctx, bind_context, reset_context

        tokens = bind_context(request_id="rid-1", job_id="jid-1", session_id="sid-1")
        assert "request_id" in tokens
        assert "job_id" in tokens
        assert "session_id" in tokens
        assert _request_id_ctx.get() == "rid-1"
        assert _job_id_ctx.get() == "jid-1"
        assert _session_id_ctx.get() == "sid-1"
        reset_context(tokens)

    def test_binds_partial(self):
        from app.utils.logging_context import _request_id_ctx, bind_context, reset_context

        tokens = bind_context(request_id="rid-only")
        assert _request_id_ctx.get() == "rid-only"
        reset_context(tokens)


class TestResetContext:
    def test_resets_all(self):
        from app.utils.logging_context import _request_id_ctx, bind_context, reset_context

        tokens = bind_context(request_id="rid")
        reset_context(tokens)
        assert _request_id_ctx.get() is None

    def test_resets_partial_tokens(self):
        from app.utils.logging_context import reset_context

        reset_context({})
        reset_context({"request_id": None})


class TestLogContext:
    def test_context_manager_sets_and_clears(self):
        from app.utils.logging_context import _request_id_ctx, log_context

        with log_context(request_id="inside"):
            assert _request_id_ctx.get() == "inside"
        assert _request_id_ctx.get() is None

    def test_context_manager_on_exception(self):
        from app.utils.logging_context import _request_id_ctx, log_context

        with pytest.raises(ValueError), log_context(request_id="exc"):
            raise ValueError("boom")
        assert _request_id_ctx.get() is None


class TestGetters:
    def test_get_request_id_context(self):
        from app.utils.logging_context import bind_context, get_request_id_context

        bind_context(request_id="rid")
        assert get_request_id_context() == "rid"

    def test_get_job_id_context(self):
        from app.utils.logging_context import bind_context, get_job_id_context

        bind_context(job_id="jid")
        assert get_job_id_context() == "jid"

    def test_get_session_id_context(self):
        from app.utils.logging_context import bind_context, get_session_id_context

        bind_context(session_id="sid")
        assert get_session_id_context() == "sid"

    def test_defaults_none(self):
        from app.utils.logging_context import get_job_id_context, get_request_id_context, get_session_id_context

        assert get_request_id_context() is None
        assert get_job_id_context() is None
        assert get_session_id_context() is None


class TestLogExtra:
    def test_uses_context_values(self):
        from app.utils.logging_context import bind_context, log_extra

        bind_context(request_id="rid", job_id="jid", session_id="sid")
        extra = log_extra()
        assert extra["request_id"] == "rid"
        assert extra["job_id"] == "jid"
        assert extra["session_id"] == "sid"

    def test_overrides_provided_values(self):
        from app.utils.logging_context import bind_context, log_extra

        bind_context(job_id="old-jid")
        extra = log_extra(job_id="new-jid")
        assert extra["job_id"] == "new-jid"

    def test_session_id_override(self):
        from app.utils.logging_context import bind_context, log_extra

        bind_context(session_id="old-sid")
        extra = log_extra(session_id="new-sid")
        assert extra["session_id"] == "new-sid"


class TestLogContextFilter:
    def test_filter_sets_request_id_on_record(self):
        from app.utils.logging_context import LogContextFilter, _request_id_ctx

        token = _request_id_ctx.set("rid-1")
        f = LogContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert f.filter(record) is True
        assert record.request_id == "rid-1"
        _request_id_ctx.reset(token)

    def test_filter_does_not_overwrite_existing(self):
        from app.utils.logging_context import LogContextFilter

        f = LogContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        record.request_id = "existing"
        f.filter(record)
        assert record.request_id == "existing"

    def test_filter_sets_job_id_and_session_id(self):
        from app.utils.logging_context import LogContextFilter, _job_id_ctx, _session_id_ctx

        jtoken = _job_id_ctx.set("jid-1")
        stoken = _session_id_ctx.set("sid-1")
        f = LogContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        f.filter(record)
        assert record.job_id == "jid-1"
        assert record.session_id == "sid-1"
        _job_id_ctx.reset(jtoken)
        _session_id_ctx.reset(stoken)


class TestBindRequestContext:
    @pytest.mark.asyncio
    async def test_binds_without_request_id_in_state(self):
        from app.utils.logging_context import _request_id_ctx, bind_request_context

        connection = MagicMock()
        connection.state.request_id = None
        connection.headers.get.return_value = "hdr-id"

        gen = bind_request_context(connection, job_id="jid-1")
        await gen.__anext__()
        assert _request_id_ctx.get() == "hdr-id"

    @pytest.mark.asyncio
    async def test_uses_existing_request_id(self):
        from app.utils.logging_context import _request_id_ctx, bind_request_context

        connection = MagicMock()
        connection.state.request_id = "state-id"

        gen = bind_request_context(connection)
        await gen.__anext__()
        assert _request_id_ctx.get() == "state-id"

    @pytest.mark.asyncio
    async def test_generates_uuid_when_no_header(self):
        from app.utils.logging_context import _request_id_ctx, bind_request_context

        connection = MagicMock()
        connection.state.request_id = None
        connection.headers.get.return_value = None

        gen = bind_request_context(connection)
        await gen.__anext__()
        rid = _request_id_ctx.get()
        assert rid is not None
        assert len(str(rid)) > 10
        assert connection.state.request_id == rid

    @pytest.mark.asyncio
    async def test_resolves_alternate_param_names(self):
        from app.utils.logging_context import _job_id_ctx, bind_request_context

        connection = MagicMock()
        connection.state.request_id = None
        connection.headers.get.return_value = None

        gen = bind_request_context(connection, jobId="alt-jid", sessionId="alt-sid")
        await gen.__anext__()
        assert _job_id_ctx.get() == "alt-jid"

    @pytest.mark.asyncio
    async def test_cleans_up_after_yield(self):
        from app.utils.logging_context import _request_id_ctx, bind_request_context

        connection = MagicMock()
        connection.state.request_id = None
        connection.headers.get.return_value = None

        gen = bind_request_context(connection)
        await gen.__anext__()
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        assert _request_id_ctx.get() is None


# ═══════════════════════════════════════════════════════════════════
# ID Generator — fill remaining branches
# ═══════════════════════════════════════════════════════════════════

class TestIdGeneratorFormats:
    def test_block_id_format(self):
        from app.utils.id_generator import generate_block_id
        assert generate_block_id(1) == "blk_001"
        assert generate_block_id(42) == "blk_042"

    def test_figure_id_format(self):
        from app.utils.id_generator import generate_figure_id
        assert generate_figure_id(0) == "fig_000"

    def test_table_id_format(self):
        from app.utils.id_generator import generate_table_id
        assert generate_table_id(10) == "tbl_010"

    def test_reference_id_format(self):
        from app.utils.id_generator import generate_reference_id
        assert generate_reference_id(23) == "ref_023"

    def test_equation_id_format(self):
        from app.utils.id_generator import generate_equation_id
        assert generate_equation_id(99) == "eqn_099"


# ═══════════════════════════════════════════════════════════════════
# Cleanup — additional edge cases
# ═══════════════════════════════════════════════════════════════════

class TestCleanupAdditional:
    @pytest.mark.asyncio
    async def test_cleanup_logs_no_old_files(self):
        from app.utils.cleanup import cleanup_old_uploads
        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=["recent.docx"]):
                with patch("app.utils.cleanup.os.path.isfile", return_value=True):
                    with patch("app.utils.cleanup.os.path.getmtime", return_value=1e9):
                        with patch("app.utils.cleanup.time.time", return_value=1000):
                            with patch("app.utils.cleanup.logger") as mock_log:
                                with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                                    task = asyncio.create_task(cleanup_old_uploads())
                                    await asyncio.sleep(0)
                                    task.cancel()
                                    mock_log.info.assert_any_call(
                                        "Cleanup complete. No old files found."
                                    )

    @pytest.mark.asyncio
    async def test_cleanup_empty_directory(self):
        from app.utils.cleanup import cleanup_old_uploads
        with patch("app.utils.cleanup.os.path.exists", return_value=True):
            with patch("app.utils.cleanup.os.listdir", return_value=[]):
                with patch("app.utils.cleanup.logger") as mock_log:
                    with patch("app.utils.cleanup.asyncio.sleep", side_effect=asyncio.sleep):
                        task = asyncio.create_task(cleanup_old_uploads())
                        await asyncio.sleep(0)
                        task.cancel()
                        mock_log.info.assert_any_call("Cleanup complete. No old files found.")


# ═══════════════════════════════════════════════════════════════════
# Background Tasks — fill remaining branches
# ═══════════════════════════════════════════════════════════════════

class TestBackgroundTasksAdditional:
    def test_sync_wrapper_creates_new_event_loop(self):
        import asyncio as real_asyncio

        from app.utils.background_tasks import with_timeout

        real_loop = real_asyncio.new_event_loop()

        @with_timeout(timeout_seconds=300)
        def sync_task():
            return "done"

        with patch("app.utils.background_tasks.asyncio.get_event_loop", side_effect=RuntimeError("no loop")):
            with patch("app.utils.background_tasks.asyncio.new_event_loop", return_value=real_loop):
                with patch("app.utils.background_tasks.asyncio.set_event_loop") as mock_set:
                    result = sync_task()
                    assert result == "done"
                    mock_set.assert_called_once_with(real_loop)

    def test_mark_job_as_failed_no_job_id(self):
        from app.utils.background_tasks import _mark_job_as_failed
        with patch("app.services.document_service.DocumentService.mark_document_failed") as mock_md:
            _mark_job_as_failed("job1", "error")
            mock_md.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# Singleton — fill remaining branches
# ═══════════════════════════════════════════════════════════════════

class TestSingletonAdditional:
    def test_get_or_create_safe_custom_log_level(self):
        from app.utils.singleton import get_or_create_safe
        logger = MagicMock()
        factory = MagicMock(side_effect=Exception("fail"))
        result = get_or_create_safe(None, factory, logger=logger, name="test", log_level="warning")
        assert result is None
        logger.warning.assert_called_once()

    def test_get_or_create_catching_unhandled_exception_raises(self):
        from app.utils.singleton import get_or_create_catching
        factory = MagicMock(side_effect=TypeError("unhandled"))
        with pytest.raises(TypeError):
            get_or_create_catching(None, factory, exceptions=(ValueError,))

    def test_resolve_optional_callable_module_error(self):
        from app.utils.singleton import resolve_optional_callable
        with patch("app.utils.singleton._load_callable", side_effect=ImportError("no module")):
            result = resolve_optional_callable("bad.module", "func")
        assert result is None

    def test_resolve_optional_callable_call_error(self):
        from app.utils.singleton import resolve_optional_callable
        with patch("app.utils.singleton._load_callable") as mock_load:
            mock_fn = MagicMock(side_effect=RuntimeError("call fail"))
            mock_load.return_value = mock_fn
            result = resolve_optional_callable("os", "getcwd")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# Dependencies — fill remaining branches
# ═══════════════════════════════════════════════════════════════════

class TestDependenciesAdditional:
    def test_get_current_user_invalid_token_error(self):
        import jwt
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user
        credentials = MagicMock()
        credentials.credentials = "bad-token"
        request = MagicMock()
        request.query_params.get.return_value = None
        with patch("app.utils.dependencies.AuthService.decode_token", side_effect=jwt.InvalidTokenError("bad")):
            with pytest.raises(HTTPException) as exc:
                get_current_user(request, credentials)
        assert exc.value.status_code == 401

    def test_get_current_user_http_exception_passthrough(self):
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user
        credentials = MagicMock()
        credentials.credentials = "fail"
        request = MagicMock()
        request.query_params.get.return_value = None
        with patch("app.utils.dependencies.AuthService.decode_token", side_effect=HTTPException(status_code=401, detail="auth fail")):
            with pytest.raises(HTTPException) as exc:
                get_current_user(request, credentials)
        assert exc.value.status_code == 401

    def test_get_optional_user_includes_role_and_metadata(self):
        from app.utils.dependencies import get_optional_user
        credentials = MagicMock()
        credentials.credentials = "tok"
        request = MagicMock()
        with patch("app.utils.dependencies.AuthService.decode_token", return_value={"email": "a@b.com", "role": "premium", "app_metadata": {"plan": "pro"}}):
            with patch("app.utils.dependencies.AuthService.get_user_id_from_payload", return_value="u1"):
                user = get_optional_user(request, credentials)
                assert user.role == "premium"
                assert user.app_metadata == {"plan": "pro"}

    def test_has_admin_scope_roles_list_no_admin(self):
        from app.utils.dependencies import _has_admin_scope
        user = MagicMock()
        user.role = "user"
        user.app_metadata = {"roles": ["editor", "viewer"]}
        assert _has_admin_scope(user) is False

