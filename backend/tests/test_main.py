from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestBuildCorsOrigins:
    def test_splits_comma_list(self):
        from app.main import _build_cors_origins
        origins = _build_cors_origins("http://a.com,http://b.com")
        assert "http://a.com" in origins
        assert "http://b.com" in origins

    def test_strips_whitespace(self):
        from app.main import _build_cors_origins
        origins = _build_cors_origins("  http://a.com , http://b.com  ")
        assert "http://a.com" in origins

    def test_debug_adds_dev_ports(self):
        with patch("app.main.settings.DEBUG", True):
            from app.main import _build_cors_origins
            origins = _build_cors_origins("http://example.com")
            assert "http://localhost:3000" in origins
            assert "http://127.0.0.1:5173" in origins

    def test_debug_skips_duplicates(self):
        with patch("app.main.settings.DEBUG", True):
            from app.main import _build_cors_origins
            origins = _build_cors_origins("http://localhost:3000")
            count = origins.count("http://localhost:3000")
            assert count == 1

    def test_non_debug_no_dev_ports(self):
        with patch("app.main.settings.DEBUG", False):
            from app.main import _build_cors_origins
            origins = _build_cors_origins("http://example.com")
            assert "http://localhost:3000" not in origins


class TestCleanupExpiredUploads:
    def test_no_directory(self):
        from app.main import _cleanup_expired_uploads
        result = _cleanup_expired_uploads(upload_dir="/nonexistent_dir_xyz", retention_days=7)
        assert result == 0

    def test_removes_expired_file(self, tmp_path):
        from app.main import _cleanup_expired_uploads
        old_file = tmp_path / "old.docx"
        old_file.write_text("old")
        old_mtime = 1000000.0
        os.utime(str(old_file), (old_mtime, old_mtime))
        result = _cleanup_expired_uploads(upload_dir=str(tmp_path), retention_days=1)
        assert result == 1
        assert not old_file.exists()

    def test_skips_recent_file(self, tmp_path):
        from app.main import _cleanup_expired_uploads
        new_file = tmp_path / "new.docx"
        new_file.write_text("new")
        result = _cleanup_expired_uploads(upload_dir=str(tmp_path), retention_days=36500)
        assert result == 0
        assert new_file.exists()

    def test_skips_directories(self, tmp_path):
        from app.main import _cleanup_expired_uploads
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        result = _cleanup_expired_uploads(upload_dir=str(tmp_path), retention_days=0)
        assert result == 0


class TestNormalizeRequestPath:
    def test_none_returns_root(self):
        from app.main import _normalize_request_path
        assert _normalize_request_path(None) == "/"

    def test_empty_returns_root(self):
        from app.main import _normalize_request_path
        assert _normalize_request_path("") == "/"

    def test_adds_leading_slash(self):
        from app.main import _normalize_request_path
        assert _normalize_request_path("api/v1/health") == "/api/v1/health"

    def test_strips_trailing_slash(self):
        from app.main import _normalize_request_path
        assert _normalize_request_path("/health/") == "/health"

    def test_root_stays_root(self):
        from app.main import _normalize_request_path
        assert _normalize_request_path("/") == "/"


class TestShouldBypassHttpsRedirect:
    def test_health_bypasses(self):
        from app.main import _should_bypass_https_redirect
        assert _should_bypass_https_redirect("/health") is True
        assert _should_bypass_https_redirect("/ready") is True
        assert _should_bypass_https_redirect("/api/v1/health") is True
        assert _should_bypass_https_redirect("/api/v1/health/live") is True
        assert _should_bypass_https_redirect("/api/v1/health/ready") is True
        assert _should_bypass_https_redirect("/api/v1/health/admin") is True

    def test_api_paths_do_not_bypass(self):
        from app.main import _should_bypass_https_redirect
        assert _should_bypass_https_redirect("/api/v1/documents") is False
        assert _should_bypass_https_redirect("/api/v1/generator/sessions") is False

    def test_root_does_not_bypass(self):
        from app.main import _should_bypass_https_redirect
        assert _should_bypass_https_redirect("/") is False


class TestIsV1Request:
    def test_v1_path(self):
        from app.main import _is_v1_request
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        assert _is_v1_request(request) is True

    def test_non_v1_path(self):
        from app.main import _is_v1_request
        request = MagicMock()
        request.url.path = "/docs"
        assert _is_v1_request(request) is False

    def test_preview_path_is_not_v1(self):
        from app.main import _is_v1_request
        request = MagicMock()
        request.url.path = "/api/preview/live"
        assert _is_v1_request(request) is False


class TestSentryBeforeSend:
    def test_cancelled_error_filtered(self):
        from app.main import _sentry_before_send
        event = {"exception": {"values": [{"type": "CancelledError"}]}}
        assert _sentry_before_send(event, {}) is None

    def test_keyboard_interrupt_filtered(self):
        from app.main import _sentry_before_send
        event = {"exception": {"values": [{"type": "KeyboardInterrupt"}]}}
        assert _sentry_before_send(event, {}) is None

    def test_normal_error_passes(self):
        from app.main import _sentry_before_send
        event = {"exception": {"values": [{"type": "ValueError"}]}}
        assert _sentry_before_send(event, {}) == event

    def test_exc_info_filter(self):
        from asyncio import CancelledError
        from app.main import _sentry_before_send
        event = {}
        hint = {"exc_info": (CancelledError, CancelledError(), None)}
        result = _sentry_before_send(event, hint)
        assert result is None

    def test_exc_info_type_check_fail(self):
        from app.main import _sentry_before_send
        event = {}
        hint = {"exc_info": (None, ValueError("test"), None)}
        result = _sentry_before_send(event, hint)
        assert result == event


class TestInitSentry:
    def test_sentry_not_available(self):
        with patch("app.main.SENTRY_AVAILABLE", False):
            from app.main import _init_sentry
            result = _init_sentry()
            assert result is None

    def test_no_dsn(self):
        with (
            patch("app.main.SENTRY_AVAILABLE", True),
            patch("app.main.sentry_sdk", MagicMock()),
            patch("app.main.settings.SENTRY_DSN", None),
        ):
            from app.main import _init_sentry
            _init_sentry()

    def test_sentry_none_guard(self):
        with (
            patch("app.main.SENTRY_AVAILABLE", True),
            patch("app.main.sentry_sdk", None),
            patch("app.main.settings.SENTRY_DSN", "https://key@sentry.io/1"),
        ):
            from app.main import _init_sentry
            _init_sentry()

    def test_successful_init(self):
        mock_sentry = MagicMock()
        with (
            patch("app.main.SENTRY_AVAILABLE", True),
            patch("app.main.sentry_sdk", mock_sentry),
            patch("app.main.settings.SENTRY_DSN", "https://key@sentry.io/1"),
        ):
            from app.main import _init_sentry
            _init_sentry()
            mock_sentry.init.assert_called_once()


class TestValidateStartup:
    def test_missing_required_raises(self):
        with patch("app.main.settings.ALGORITHM", None):
            from app.main import _validate_startup
            with pytest.raises(RuntimeError, match="Missing required settings"):
                _validate_startup()

    def test_missing_optional_logs_warning(self):
        with (
            patch("app.main.settings.ALGORITHM", "HS256"),
            patch("app.main.settings.NVIDIA_API_KEY", None),
        ):
            from app.main import _validate_startup
            _validate_startup()

    def test_validation_passes(self):
        with (
            patch("app.main.settings.ALGORITHM", "HS256"),
            patch("app.main.settings.NVIDIA_API_KEY", "nk-xxx"),
            patch("app.main.settings.REDIS_ENABLED", False),
            patch("app.main.settings.SUPABASE_URL", None),
        ):
            from app.main import _validate_startup
            _validate_startup()


class TestFetchQueueDepths:
    def test_redis_disabled(self):
        import app.main as _m
        _m._queue_depth_redis_client = None
        with patch("app.main.settings.REDIS_ENABLED", False):
            from app.main import _fetch_queue_depths
            result = _fetch_queue_depths()
            assert result == {"interactive": 0, "batch": 0}

    def test_redis_enabled(self):
        import app.main as _m
        _m._queue_depth_redis_client = None
        mock_redis = MagicMock()
        mock_redis.llen.side_effect = [3, 7]
        with (
            patch("app.main.settings.REDIS_ENABLED", True),
            patch("app.main.settings.REDIS_URL", "redis://localhost"),
            patch("redis.Redis.from_url", return_value=mock_redis),
        ):
            from app.main import _fetch_queue_depths
            result = _fetch_queue_depths()
            assert result == {"interactive": 3, "batch": 7}

    def test_redis_error_returns_zero(self):
        import app.main as _m
        _m._queue_depth_redis_client = None
        with (
            patch("app.main.settings.REDIS_ENABLED", True),
            patch("redis.Redis.from_url", side_effect=Exception("conn failed")),
        ):
            from app.main import _fetch_queue_depths
            result = _fetch_queue_depths()
            assert result == {"interactive": 0, "batch": 0}


class TestRunStartupStep:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.main import _run_startup_step
        result = await _run_startup_step(
            "test", lambda: "ok", timeout_seconds=5.0
        )
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_timeout(self):
        from app.main import _run_startup_step
        import time

        def slow_op():
            time.sleep(0.5)
            return "late"

        result = await _run_startup_step(
            "slow", slow_op, timeout_seconds=0.1, default_value="default"
        )
        assert result == "default"

    @pytest.mark.asyncio
    async def test_exception(self):
        from app.main import _run_startup_step

        def failing_op():
            raise ValueError("fail")

        result = await _run_startup_step(
            "fail", failing_op, timeout_seconds=5.0, default_value="fallback"
        )
        assert result == "fallback"


class TestResetInterruptedJobs:
    @pytest.mark.asyncio
    async def test_no_supabase_client(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value=None):
            from app.main import _reset_interrupted_jobs_on_startup
            _reset_interrupted_jobs_on_startup()

    @pytest.mark.asyncio
    async def test_exception_during_reset(self):
        from app.main import _reset_interrupted_jobs_on_startup
        with patch("app.db.supabase_client.get_supabase_client", side_effect=Exception("fail")):
            _reset_interrupted_jobs_on_startup()

    def test_with_interrupted_jobs(self):
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "doc-1"}, {"id": "doc-2"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
            from app.main import _reset_interrupted_jobs_on_startup
            _reset_interrupted_jobs_on_startup()
            mock_sb.table.return_value.update.assert_called_once()
            mock_sb.table.return_value.update.return_value.in_.assert_called_once_with("id", ["doc-1", "doc-2"])

    def test_no_interrupted_jobs(self):
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result
        with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
            from app.main import _reset_interrupted_jobs_on_startup
            _reset_interrupted_jobs_on_startup()
            mock_sb.table.return_value.update.assert_not_called()


class TestEnsureRoutersLoaded:
    @pytest.mark.asyncio
    async def test_already_loaded(self):
        from app.main import _ensure_routers_loaded
        mock_app = MagicMock()
        mock_app.state._routers_loaded = True
        await _ensure_routers_loaded(mock_app)


class TestLoadOptionalRouters:
    def test_already_loaded(self):
        from app.main import _load_optional_routers
        mock_app = MagicMock()
        mock_app.state._routers_loaded = True
        _load_optional_routers(mock_app)
        mock_app.include_router.assert_not_called()

    def test_first_load(self):
        from app.main import _load_optional_routers
        mock_app = MagicMock()
        mock_app.state._routers_loaded = False
        with (
            patch("app.routers.v1.v1_router", MagicMock()),
            patch("app.routers.preview.router", MagicMock()),
        ):
            _load_optional_routers(mock_app)
        assert mock_app.state._routers_loaded is True


class TestRefreshEnhancementCapabilities:
    def test_refresh(self):
        mock_em = MagicMock()
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {"enabled": True}
        mock_em.refresh.return_value = mock_profile
        with patch("app.main.enhancement_manager", mock_em):
            from app.main import _refresh_enhancement_capabilities
            _refresh_enhancement_capabilities()
            mock_em.refresh.assert_called_once()


class TestPreloadPreviewCss:
    def test_preload(self):
        mock_preloader = MagicMock()
        with patch("app.services.preview_renderer.preload_template_css", mock_preloader):
            from app.main import _preload_preview_css
            _preload_preview_css()
            mock_preloader.assert_called_once()


class TestBuildErrorResponse:
    def test_basic_error(self):
        from app.main import build_error_response
        request = MagicMock()
        request.state.request_id = "req-1"
        resp = build_error_response(request, status_code=404, code="NOT_FOUND", message="Not found")
        assert resp.status_code == 404
        body = resp.body.decode()
        assert "NOT_FOUND" in body
        assert "Not found" in body

    def test_with_details(self):
        from app.main import build_error_response
        request = MagicMock()
        request.state.request_id = "req-2"
        resp = build_error_response(request, status_code=400, code="BAD_REQUEST", message="bad",
                                      details={"field": "err"})
        assert resp.status_code == 400
        body = resp.body.decode()
        assert "field" in body


class TestProbeGrobid:
    @pytest.mark.asyncio
    async def test_disabled(self):
        with patch("app.main.settings.GROBID_ENABLED", False):
            from app.main import _probe_grobid_startup
            result = await _probe_grobid_startup()
            assert result is False

    @pytest.mark.asyncio
    async def test_success(self):
        with (
            patch("app.main.settings.GROBID_ENABLED", True),
            patch("app.main.settings.GROBID_URL", "http://grobid:8070"),
            patch("app.main.settings.get_grobid_urls", return_value=["http://grobid:8070"]),
            patch("app.main.settings.get_service_health_path", return_value="/api/isalive"),
        ):
            from app.main import _probe_grobid_startup
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.__aenter__.return_value.get.return_value = mock_response
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await _probe_grobid_startup(attempts=1, timeout_seconds=1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_all_failures(self):
        with (
            patch("app.main.settings.GROBID_ENABLED", True),
            patch("app.main.settings.GROBID_URL", "http://grobid:8070"),
            patch("app.main.settings.get_grobid_urls", return_value=["http://grobid:8070"]),
            patch("app.main.settings.get_service_health_path", return_value="/api/isalive"),
        ):
            from app.main import _probe_grobid_startup
            with patch("httpx.AsyncClient", side_effect=Exception("connection refused")):
                result = await _probe_grobid_startup(attempts=1, timeout_seconds=1.0)
            assert result is False
