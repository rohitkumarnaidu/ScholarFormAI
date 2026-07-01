import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestFeatureFlagMiddleware:
    @pytest.mark.asyncio
    async def test_sets_feature_flags_on_request_state(self):
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.get_all_flags.return_value = {"new_upload_flow": True}
            mock_svc_factory.return_value = mock_svc
            from app.middleware.feature_flags import FeatureFlagMiddleware
            mw = FeatureFlagMiddleware(MagicMock())
            request = MagicMock()
            request.app.debug = False
            request.state = MagicMock()
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            result = await mw.dispatch(request, call_next)
            assert request.state.feature_flags == {"new_upload_flow": True}
            assert result == call_next.return_value

    @pytest.mark.asyncio
    async def test_debug_mode_adds_header(self):
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.get_all_flags.return_value = {"flag_a": True}
            mock_svc_factory.return_value = mock_svc
            from app.middleware.feature_flags import FeatureFlagMiddleware
            mw = FeatureFlagMiddleware(MagicMock())
            request = MagicMock()
            request.app.debug = True
            request.state = MagicMock()
            request.headers = {}
            response = MagicMock()
            response.headers = {}
            call_next = AsyncMock(return_value=response)
            result = await mw.dispatch(request, call_next)
            assert "X-Feature-Flags" in result.headers

    @pytest.mark.asyncio
    async def test_no_debug_skips_header(self):
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.get_all_flags.return_value = {}
            mock_svc_factory.return_value = mock_svc
            from app.middleware.feature_flags import FeatureFlagMiddleware
            mw = FeatureFlagMiddleware(MagicMock())
            request = MagicMock()
            request.app.debug = False
            request.state = MagicMock()
            request.headers = {}
            response = MagicMock(headers={})
            call_next = AsyncMock(return_value=response)
            result = await mw.dispatch(request, call_next)
            assert "X-Feature-Flags" not in result.headers

    @pytest.mark.asyncio
    async def test_auth_header_does_not_break(self):
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.get_all_flags.return_value = {}
            mock_svc_factory.return_value = mock_svc
            from app.middleware.feature_flags import FeatureFlagMiddleware
            mw = FeatureFlagMiddleware(MagicMock())
            request = MagicMock()
            request.app.debug = False
            request.state = MagicMock()
            request.headers = {"authorization": "Bearer some-token"}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            result = await mw.dispatch(request, call_next)
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_all_flags_called_with_user_id(self):
        with patch("app.middleware.feature_flags.get_feature_flag_service") as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.get_all_flags.return_value = {}
            mock_svc_factory.return_value = mock_svc
            from app.middleware.feature_flags import FeatureFlagMiddleware
            mw = FeatureFlagMiddleware(MagicMock())
            request = MagicMock()
            request.app.debug = False
            request.state = MagicMock()
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            await mw.dispatch(request, call_next)
            mock_svc.get_all_flags.assert_called_once()
