from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestActivityServiceUtcNowIso:
    @pytest.fixture
    def svc(self):
        from app.services.activity_service import ActivityService
        return ActivityService

    def test_returns_iso_string(self, svc):
        result = svc._utc_now_iso()
        assert "T" in result
        assert result.endswith("+00:00") or result.endswith("Z") or "+" in result


class TestActivityServiceComputePeriodStart:
    @pytest.fixture
    def svc(self):
        from app.services.activity_service import ActivityService
        return ActivityService

    def test_7d(self, svc):
        from datetime import datetime, timedelta, timezone
        result = svc._compute_period_start("7d")
        assert result is not None
        diff = datetime.now(timezone.utc) - result
        assert diff >= timedelta(days=6)

    def test_30d(self, svc):
        from datetime import datetime, timedelta, timezone
        result = svc._compute_period_start("30d")
        assert result is not None
        diff = datetime.now(timezone.utc) - result
        assert diff >= timedelta(days=29)

    def test_90d(self, svc):
        from datetime import datetime, timedelta, timezone
        result = svc._compute_period_start("90d")
        assert result is not None
        diff = datetime.now(timezone.utc) - result
        assert diff >= timedelta(days=89)

    def test_all(self, svc):
        assert svc._compute_period_start("all") is None

    def test_unknown_defaults_7d(self, svc):
        from datetime import datetime, timedelta, timezone
        result = svc._compute_period_start("invalid")
        assert result is not None
        diff = datetime.now(timezone.utc) - result
        assert diff >= timedelta(days=6)


class TestRecordActivity:
    @pytest.fixture
    def svc(self):
        from app.services.activity_service import ActivityService
        svc = ActivityService
        svc._table_available = None
        svc._table_warning_logged = False
        return svc

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_records_activity(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.return_value = MagicMock()
        await svc.record_activity("user-1", "upload", {"file": "test.pdf"})
        assert svc._table_available is True

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_unknown_activity_type(self, mock_to_thread, mock_get_sb, svc):
        await svc.record_activity("user-1", "invalid_type")
        mock_to_thread.assert_not_called()

    async def test_table_unavailable_skips(self, svc):
        svc._table_available = False
        with patch("app.services.activity_service.get_supabase_client") as mock_get_sb:
            await svc.record_activity("user-1", "upload")
            mock_get_sb.assert_not_called()

    @patch("app.services.activity_service.get_supabase_client", return_value=None)
    async def test_supabase_none_skips(self, mock_get_sb, svc):
        await svc.record_activity("user-1", "upload")
        mock_get_sb.assert_called_once()

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_missing_table_sets_flag(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        error_text = (
            '{"message": "Could not find the table \'user_activity\' in schema \'public\'"}'
        )
        mock_to_thread.side_effect = Exception(error_text)
        await svc.record_activity("user-1", "upload")
        assert svc._table_available is False

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_generic_exception_logged(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("DB connection error")
        await svc.record_activity("user-1", "format")
        assert svc._table_available is None


class TestGetRecentActivities:
    @pytest.fixture
    def svc(self):
        from app.services.activity_service import ActivityService
        return ActivityService

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_returns_activities(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "activity_type": "upload"}]
        mock_to_thread.return_value = mock_result
        result = await svc.get_recent_activities("user-1", limit=10)
        assert len(result) == 1
        assert result[0]["activity_type"] == "upload"

    @patch("app.services.activity_service.get_supabase_client", return_value=None)
    async def test_raises_when_supabase_none(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_recent_activities("user-1")

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_missing_table_returns_empty(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'user_activity'")
        result = await svc.get_recent_activities("user-1")
        assert result == []

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_other_error_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Other error")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_recent_activities("user-1")


class TestGetActivitySummary:
    @pytest.fixture
    def svc(self):
        from app.services.activity_service import ActivityService
        return ActivityService

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_returns_summary(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [
            {"activity_type": "upload"},
            {"activity_type": "upload"},
            {"activity_type": "format"},
        ]
        mock_to_thread.return_value = mock_result
        result = await svc.get_activity_summary("user-1", period="7d")
        assert result["total_activities"] == 3
        assert result["activity_breakdown"]["upload"] == 2
        assert result["most_frequent"] == "upload"

    @patch("app.services.activity_service.get_supabase_client", return_value=None)
    async def test_raises_when_supabase_none(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_activity_summary("user-1")

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_missing_table_returns_empty_summary(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'user_activity'")
        result = await svc.get_activity_summary("user-1", period="30d")
        assert result["total_activities"] == 0
        assert result["period"] == "30d"

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_other_error_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("DB error")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_activity_summary("user-1")

    @patch("app.services.activity_service.get_supabase_client")
    @patch("app.services.activity_service.asyncio.to_thread")
    async def test_empty_most_frequent_none(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = []
        mock_to_thread.return_value = mock_result
        result = await svc.get_activity_summary("user-1")
        assert result["most_frequent"] is None


class TestActivityServiceModule:
    def test_activity_service_instance(self):
        from app.services.activity_service import activity_service
        assert activity_service is not None

    def test_activity_types(self):
        from app.services.activity_service import ACTIVITY_TYPES
        assert "upload" in ACTIVITY_TYPES
        assert "format" in ACTIVITY_TYPES
        assert "edit" in ACTIVITY_TYPES


_INLINE_TO_THREAD = lambda fn, *a, **kw: fn(*a, **kw)


class TestRecordActivityInnerClosure:
    @pytest.mark.asyncio
    async def test_run_insert_success(self):
        from app.services.activity_service import ActivityService
        svc = ActivityService
        svc._table_available = None
        svc._table_warning_logged = False
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("app.services.activity_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.activity_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                await svc.record_activity("user-1", "upload", {"file": "test.pdf"})
        assert svc._table_available is True

    @pytest.mark.asyncio
    async def test_run_insert_missing_table(self):
        from app.services.activity_service import ActivityService
        svc = ActivityService
        svc._table_available = None
        svc._table_warning_logged = False
        mock_sb = MagicMock()
        error_text = '{"message": "Could not find the table \'user_activity\' in schema \'public\'"}'
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception(error_text)
        with patch("app.services.activity_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.activity_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                await svc.record_activity("user-1", "upload")
        assert svc._table_available is False


class TestGetRecentActivitiesInnerClosure:
    @pytest.mark.asyncio
    async def test_run_query_success(self):
        from app.services.activity_service import ActivityService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "1", "activity_type": "upload"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result
        with patch("app.services.activity_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.activity_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await ActivityService.get_recent_activities("user-1", limit=10)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_missing_table_returns_empty(self):
        from app.services.activity_service import ActivityService
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("Could not find the table 'user_activity'")
        with patch("app.services.activity_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.activity_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await ActivityService.get_recent_activities("user-1")
        assert result == []


class TestGetActivitySummaryInnerClosure:
    @pytest.mark.asyncio
    async def test_run_query_with_gte(self):
        from app.services.activity_service import ActivityService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {"activity_type": "upload"},
            {"activity_type": "upload"},
            {"activity_type": "format"},
        ]
        mock_eq = MagicMock()
        mock_eq.gte.return_value.execute.return_value = mock_result
        mock_sb.table.return_value.select.return_value.eq.return_value = mock_eq
        with patch("app.services.activity_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.activity_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await ActivityService.get_activity_summary("user-1", period="7d")
        assert result["total_activities"] == 3
        assert result["most_frequent"] == "upload"
