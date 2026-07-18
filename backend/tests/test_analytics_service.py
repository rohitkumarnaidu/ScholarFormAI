from unittest.mock import MagicMock, patch

import pytest


# Posthog is imported lazily inside AnalyticsService.__init__,
# so we patch the source package name, not the consumer module


class TestAnalyticsServiceInit:
    def test_disabled_when_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is False
        assert svc._posthog is None

    def test_disabled_when_empty_api_key(self):
        with patch.dict("os.environ", {"POSTHOG_API_KEY": ""}, clear=True):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is False
        assert svc._posthog is None

    def test_initializes_posthog_when_key_present(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test123"}, clear=True),
            patch("posthog.Posthog") as MockPosthog,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is True
        assert svc._posthog is not None
        MockPosthog.assert_called_once_with(
            project_api_key="phc_test123",
            host="https://app.posthog.com",
            debug=False,
        )

    def test_uses_custom_host_when_set(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test", "POSTHOG_HOST": "https://eu.posthog.com"}, clear=True),
            patch("posthog.Posthog") as MockPosthog,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is True
        MockPosthog.assert_called_once_with(
            project_api_key="phc_test",
            host="https://eu.posthog.com",
            debug=False,
        )

    def test_graceful_degradation_on_posthog_import_failure(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test"}, clear=True),
            patch.dict("sys.modules", {"posthog": None}),
        ):
            import importlib
            import sys
            if "app.services.analytics_service" in sys.modules:
                del sys.modules["app.services.analytics_service"]
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is False
        assert svc._posthog is None

    def test_graceful_degradation_on_posthog_init_failure(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test"}, clear=True),
            patch("posthog.Posthog", side_effect=RuntimeError("bad key")),
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
        assert svc._enabled is False
        assert svc._posthog is None


class TestAnalyticsServiceCapture:
    def test_capture_sends_to_posthog_when_enabled(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test"}, clear=True),
            patch("posthog.Posthog") as MockPosthog,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            svc.capture("user-1", "test_event", {"key": "val"})
        MockPosthog.return_value.capture.assert_called_once_with(
            distinct_id="user-1",
            event="test_event",
            properties={"key": "val"},
        )

    def test_capture_logs_event(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test"}, clear=True),
            patch("posthog.Posthog"),
            patch("app.services.analytics_service.logger") as mock_logger,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            svc.capture("user-1", "test_event", {"key": "val"})
        mock_logger.info.assert_any_call(
            "Analytics event: %s [user=%s, props=%s]",
            "test_event", "user-1", {"key": "val"},
        )

    def test_capture_does_not_send_to_posthog_when_disabled(self):
        with patch.dict("os.environ", {}, clear=True):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            svc.capture("user-1", "test_event")
        assert svc._enabled is False
        assert svc._posthog is None

    def test_capture_graceful_on_posthog_exception(self):
        with (
            patch.dict("os.environ", {"POSTHOG_API_KEY": "phc_test"}, clear=True),
            patch("posthog.Posthog") as MockPosthog,
            patch("app.services.analytics_service.logger") as mock_logger,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            mock_posthog = svc._posthog
            mock_posthog.capture.side_effect = RuntimeError("posthog down")
            svc.capture("user-1", "test_event")
        mock_logger.warning.assert_called_once()
        assert mock_logger.warning.call_args[0][0] == "Analytics capture failed: %s"
        mock_logger.info.assert_any_call(
            "Analytics event: %s [user=%s, props=%s]",
            "test_event", "user-1", None,
        )

    def test_capture_without_properties(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("app.services.analytics_service.logger") as mock_logger,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            svc.capture("user-1", "simple_event")
        mock_logger.info.assert_called_once_with(
            "Analytics event: %s [user=%s, props=%s]",
            "simple_event", "user-1", None,
        )

    def test_capture_truncates_long_distinct_id_in_log(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("app.services.analytics_service.logger") as mock_logger,
        ):
            from app.services.analytics_service import AnalyticsService
            svc = AnalyticsService()
            svc.capture("user-abcdef123456", "event")
        mock_logger.info.assert_called_once_with(
            "Analytics event: %s [user=%s, props=%s]",
            "event", "user-abc", None,
        )


class TestAnalyticsServiceSingleton:
    def test_singleton_is_analytics_service_instance(self):
        from app.services.analytics_service import analytics_service
        from app.services.analytics_service import AnalyticsService
        assert isinstance(analytics_service, AnalyticsService)

    def test_singleton_capture_works(self):
        from app.services.analytics_service import analytics_service
        with patch.object(analytics_service, "capture") as mock_capture:
            analytics_service.capture("u1", "e1", {"k": "v"})
            mock_capture.assert_called_once_with("u1", "e1", {"k": "v"})
