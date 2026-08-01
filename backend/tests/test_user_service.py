from unittest.mock import MagicMock, patch

import pytest


class TestGetUserById:
    @pytest.mark.asyncio
    async def test_returns_user(self):
        from app.services.user_service import UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "user-1", "email": "a@b.com"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            result = await UserService.get_user_by_id("user-1")
        assert result == {"id": "user-1", "email": "a@b.com"}

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        from app.services.user_service import UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data=None)
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            result = await UserService.get_user_by_id("user-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self):
        from app.services.user_service import UserService
        with patch("app.services.user_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client"):
                await UserService.get_user_by_id("user-1")


class TestUpdateUserProfile:
    @pytest.mark.asyncio
    async def test_updates_profile(self):
        from app.services.user_service import UserService
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "user-1", "email": "a@b.com"}]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_result
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            result = await UserService.update_user_profile("user-1", "a@b.com", "Alice", "MIT")
        assert result == {"id": "user-1", "email": "a@b.com"}

    @pytest.mark.asyncio
    async def test_empty_data_returns_none(self):
        from app.services.user_service import UserService
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_result
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            result = await UserService.update_user_profile("user-1", "a@b.com", "Alice", "MIT")
        assert result is None

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self):
        from app.services.user_service import UserService
        with patch("app.services.user_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client"):
                await UserService.update_user_profile("u", "e", "n", "i")


class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_returns_user(self):
        from app.services.user_service import UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.return_value = MagicMock(data={"id": "user-1", "email": "a@b.com"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            result = await UserService.get_user_by_email("a@b.com")
        assert result == {"id": "user-1", "email": "a@b.com"}

    @pytest.mark.asyncio
    async def test_supabase_none_raises(self):
        from app.services.user_service import UserService
        with patch("app.services.user_service.get_supabase_client", return_value=None):
            with pytest.raises(Exception, match="Supabase client"):
                await UserService.get_user_by_email("a@b.com")

    @pytest.mark.asyncio
    async def test_apierror_raises(self):
        from postgrest import APIError

        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.side_effect = APIError({"message": "db fail"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to get user"):
                await UserService.get_user_by_email("test@test.com")

    @pytest.mark.asyncio
    async def test_generic_exception_raises(self):
        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.side_effect = ValueError("unexpected")
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to get user"):
                await UserService.get_user_by_email("test@test.com")


class TestGetUserByIdErrorPaths:
    @pytest.mark.asyncio
    async def test_apierror_raises(self):
        from postgrest import APIError

        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.side_effect = APIError({"message": "db fail"})
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to get user"):
                await UserService.get_user_by_id("user-1")

    @pytest.mark.asyncio
    async def test_generic_exception_raises(self):
        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_q = MagicMock()
        mock_q.maybe_single.return_value.execute.side_effect = RuntimeError("unexpected")
        mock_client.table.return_value.select.return_value.eq.return_value = mock_q
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to get user"):
                await UserService.get_user_by_id("user-1")


class TestUpdateUserProfileErrorPaths:
    @pytest.mark.asyncio
    async def test_apierror_raises(self):
        from postgrest import APIError

        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.side_effect = APIError({"message": "db fail"})
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to update user profile"):
                await UserService.update_user_profile("user-1", "a@b.com", "Alice", "MIT")

    @pytest.mark.asyncio
    async def test_generic_exception_raises(self):
        from app.services.user_service import DatabaseUnavailableError, UserService
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.side_effect = RuntimeError("unexpected")
        with patch("app.services.user_service.get_supabase_client", return_value=mock_client):
            with pytest.raises(DatabaseUnavailableError, match="Failed to update"):
                await UserService.update_user_profile("user-1", "a@b.com", "Alice", "MIT")
