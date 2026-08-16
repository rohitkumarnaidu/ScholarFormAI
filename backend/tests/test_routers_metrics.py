from unittest.mock import MagicMock, patch

import pytest


class TestMetricsDB:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import get_database_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.count = 42
        mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result

        with patch("app.routers.v1.metrics.get_supabase_client", return_value=mock_sb):
            result = await get_database_metrics(mock_request, admin_user=MagicMock())
        assert result is not None

    @pytest.mark.asyncio
    async def test_unavailable(self):
        from app.routers.v1.metrics import get_database_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.get_supabase_client", return_value=None):
            result = await get_database_metrics(mock_request, admin_user=MagicMock())
        assert result is not None

    @pytest.mark.asyncio
    async def test_db_query_exception(self):
        from app.routers.v1.metrics import get_database_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("fail")

        with patch("app.routers.v1.metrics.get_supabase_client", return_value=mock_sb):
            response = await get_database_metrics(mock_request, admin_user=MagicMock())
        assert response is not None


class TestLogFrontendError:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import log_frontend_error

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = await log_frontend_error(
            mock_request,
            {"message": "test", "stack": "trace", "url": "/page", "timestamp": "now"},
            current_user=None,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_minimal_payload(self):
        from app.routers.v1.metrics import log_frontend_error

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = await log_frontend_error(mock_request, {"message": "test"}, current_user=None)
        assert result is not None


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import health_check

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.limit.return_value.execute()

        with (
            patch("app.routers.v1.metrics.get_supabase_client", return_value=mock_sb),
            patch("app.services.llm_service.check_health") as mock_llm,
        ):
            mock_llm.return_value = {"nvidia": "healthy", "deepseek": "healthy"}
            result = await health_check(mock_request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_degraded(self):
        from app.routers.v1.metrics import health_check

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with (
            patch("app.routers.v1.metrics.get_supabase_client", return_value=None),
            patch("app.services.llm_service.check_health") as mock_llm,
        ):
            mock_llm.return_value = {"nvidia": "unhealthy", "deepseek": "unhealthy"}
            result = await health_check(mock_request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_check_exception(self):
        from app.routers.v1.metrics import health_check

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with (
            patch("app.routers.v1.metrics.get_supabase_client", return_value=None),
            patch("app.services.llm_service.check_health", side_effect=Exception("llm error")),
        ):
            result = await health_check(mock_request)
        assert result is not None


class TestMetricsDashboard:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import get_metrics_dashboard

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_sb = MagicMock()
        res_mock = MagicMock()
        res_mock.count = 5
        mock_sb.table.return_value.select.return_value.limit.side_effect = [res_mock, res_mock]

        with patch("app.routers.v1.metrics.get_supabase_client", return_value=mock_sb):
            with patch("app.routers.v1.metrics.get_model_metrics") as mock_mm:
                mock_mm.return_value.get_summary.return_value = {}
                mock_mm.return_value.get_model_comparison.return_value = {}
                with patch("app.routers.v1.metrics.get_ab_testing") as mock_ab:
                    mock_ab.return_value.get_test_summary.return_value = {}
                    result = await get_metrics_dashboard(mock_request, admin_user=MagicMock())
        assert result is not None

    @pytest.mark.asyncio
    async def test_exception_handled(self):
        from app.routers.v1.metrics import get_metrics_dashboard

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with patch("app.routers.v1.metrics.get_supabase_client", side_effect=Exception("fail")):
            with patch("app.routers.v1.metrics.get_model_metrics") as mock_mm:
                mock_mm.return_value.get_summary.return_value = {}
                mock_mm.return_value.get_model_comparison.return_value = {}
                with patch("app.routers.v1.metrics.get_ab_testing") as mock_ab:
                    mock_ab.return_value.get_test_summary.return_value = {}
                    result = await get_metrics_dashboard(mock_request, admin_user=MagicMock())
        assert result is not None


class TestEnhancementsMetrics:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import get_enhancement_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {
            "enabled": True,
            "queue_provider": "redis",
            "queue_available": True,
            "ocr_backends": ["tesseract"],
            "keyword_backends": ["rake"],
        }

        with patch("app.routers.v1.metrics.enhancement_manager") as mock_em:
            mock_em.refresh.return_value = mock_profile
            result = await get_enhancement_metrics(mock_request, admin_user=MagicMock())
        assert result is not None


class TestVLLMReadiness:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.metrics import get_vllm_readiness

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        with patch("app.routers.v1.metrics.build_vllm_adoption_report", return_value={"ready": True}):
            result = await get_vllm_readiness(mock_request, admin_user=MagicMock())
        assert result is not None
