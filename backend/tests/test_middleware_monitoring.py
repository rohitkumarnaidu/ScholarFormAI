from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMonitoringMiddleware:
    @pytest.mark.asyncio
    async def test_sets_request_id(self):
        from app.middleware.monitoring import MonitoringMiddleware

        mw = MonitoringMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {}
        request.method = "GET"
        request.url.path = "/test"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        with patch("app.middleware.monitoring.logger") as mock_logger:
            result = await mw.dispatch(request, call_next)
        assert request.state.request_id is not None
        assert result.headers["X-Request-Id"] == request.state.request_id
        assert "X-Processing-Time" in result.headers
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_uses_x_request_id_from_header(self):
        from app.middleware.monitoring import MonitoringMiddleware

        mw = MonitoringMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {"x-request-id": "from-header"}
        request.method = "GET"
        request.url.path = "/test"
        response = MagicMock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        with patch("app.middleware.monitoring.logger"):
            result = await mw.dispatch(request, call_next)
        assert request.state.request_id == "from-header"
        assert result.headers["X-Request-Id"] == "from-header"

    @pytest.mark.asyncio
    async def test_exception_logged(self):
        from app.middleware.monitoring import MonitoringMiddleware

        mw = MonitoringMiddleware(MagicMock())
        request = MagicMock()
        request.headers = {}
        request.method = "GET"
        request.url.path = "/test"
        call_next = AsyncMock(side_effect=ValueError("something broke"))
        with patch("app.middleware.monitoring.logger") as mock_logger:
            with pytest.raises(ValueError):
                await mw.dispatch(request, call_next)
            mock_logger.error.assert_called_once()
            assert "something broke" in str(mock_logger.error.call_args)
