from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestGetRecentActivity:
    @pytest.fixture
    def mock_request(self):
        from fastapi import Request

        req = MagicMock(spec=Request)
        req.state.request_id = "req-test-activity"
        req.url.path = "/api/v1/activity/recent"
        return req

    @pytest.fixture
    def mock_user(self):
        from app.schemas.user import User

        user = MagicMock(spec=User)
        user.id = "user-123"
        return user

    @pytest.mark.asyncio
    async def test_default_limit(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(
                return_value=[{"id": "a1", "activity_type": "upload"}]
            )

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=20, current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_recent_activities.assert_called_once_with(
            user_id="user-123", limit=20
        )

    @pytest.mark.asyncio
    async def test_custom_limit(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(return_value=[])

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=5, current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_recent_activities.assert_called_once_with(
            user_id="user-123", limit=5
        )

    @pytest.mark.asyncio
    async def test_max_limit(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(
                return_value=[{"id": f"a{i}"} for i in range(100)]
            )

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=100, current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_recent_activities.assert_called_once_with(
            user_id="user-123", limit=100
        )

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(return_value=[])

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=20, current_user=mock_user
            )

        assert resp.status_code == 200
        import json
        body = json.loads(resp.body.decode())
        assert body["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_multiple_activities(self, mock_request, mock_user):
        activities = [
            {"id": "a1", "activity_type": "upload"},
            {"id": "a2", "activity_type": "format"},
            {"id": "a3", "activity_type": "download"},
        ]
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(return_value=activities)

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=20, current_user=mock_user
            )

        assert resp.status_code == 200
        import json
        body = json.loads(resp.body.decode())
        assert body["data"]["total"] == 3

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_503(self, mock_request, mock_user):
        from fastapi import HTTPException

        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(
                side_effect=HTTPException(status_code=503, detail="Database not available")
            )

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=20, current_user=mock_user
            )

        assert resp.status_code == 503
        body = resp.body.decode()
        assert "DATABASE_UNAVAILABLE" in body

    @pytest.mark.asyncio
    async def test_unauthorized_returns_401(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_recent_activities = AsyncMock(
                side_effect=HTTPException(401, "Unauthorized")
            )

            from app.routers.v1.activity import get_recent_activity

            resp = await get_recent_activity(
                request=mock_request, limit=20, current_user=mock_user
            )

        assert resp.status_code == 401
        body = resp.body.decode()
        assert "UNAUTHORIZED" in body


class TestGetActivitySummary:
    @pytest.fixture
    def mock_request(self):
        from fastapi import Request

        req = MagicMock(spec=Request)
        req.state.request_id = "req-test-activity-summary"
        req.url.path = "/api/v1/activity/summary"
        return req

    @pytest.fixture
    def mock_user(self):
        from app.schemas.user import User

        user = MagicMock(spec=User)
        user.id = "user-456"
        return user

    @pytest.mark.asyncio
    async def test_default_period(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                return_value={
                    "total_activities": 5,
                    "period": "7d",
                    "activity_breakdown": {"upload": 3, "format": 2},
                    "most_frequent": "upload",
                }
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="7d", current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_activity_summary.assert_called_once_with(
            user_id="user-456", period="7d"
        )

    @pytest.mark.asyncio
    async def test_custom_period_30d(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                return_value={
                    "total_activities": 12,
                    "period": "30d",
                    "activity_breakdown": {},
                    "most_frequent": None,
                }
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="30d", current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_activity_summary.assert_called_once_with(
            user_id="user-456", period="30d"
        )

    @pytest.mark.asyncio
    async def test_custom_period_90d(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                return_value={
                    "total_activities": 30,
                    "period": "90d",
                    "activity_breakdown": {"upload": 10, "edit": 20},
                    "most_frequent": "edit",
                }
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="90d", current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_activity_summary.assert_called_once_with(
            user_id="user-456", period="90d"
        )

    @pytest.mark.asyncio
    async def test_period_all(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                return_value={
                    "total_activities": 100,
                    "period": "all",
                    "activity_breakdown": {"upload": 50, "format": 50},
                    "most_frequent": "upload",
                }
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="all", current_user=mock_user
            )

        assert resp.status_code == 200
        mock_svc.get_activity_summary.assert_called_once_with(
            user_id="user-456", period="all"
        )

    @pytest.mark.asyncio
    async def test_empty_activity_breakdown(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                return_value={
                    "total_activities": 0,
                    "period": "7d",
                    "activity_breakdown": {},
                    "most_frequent": None,
                }
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="7d", current_user=mock_user
            )

        assert resp.status_code == 200
        import json
        body = json.loads(resp.body.decode())
        assert body["data"]["total_activities"] == 0
        assert body["data"]["most_frequent"] is None
        assert body["data"]["activity_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_503(self, mock_request, mock_user):
        from fastapi import HTTPException

        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                side_effect=HTTPException(status_code=503, detail="Database not available")
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="7d", current_user=mock_user
            )

        assert resp.status_code == 503
        body = resp.body.decode()
        assert "DATABASE_UNAVAILABLE" in body

    @pytest.mark.asyncio
    async def test_unauthorized_returns_401(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                side_effect=HTTPException(401, "Unauthorized")
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="7d", current_user=mock_user
            )

        assert resp.status_code == 401
        body = resp.body.decode()
        assert "UNAUTHORIZED" in body

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_500(self, mock_request, mock_user):
        with patch("app.routers.v1.activity.activity_service") as mock_svc:
            mock_svc.get_activity_summary = AsyncMock(
                side_effect=ValueError("Something unexpected")
            )

            from app.routers.v1.activity import get_activity_summary

            resp = await get_activity_summary(
                request=mock_request, period="7d", current_user=mock_user
            )

        assert resp.status_code == 500
        body = resp.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
