from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestDecodeToken:
    def test_decodes_jwt(self):
        from app.services.auth_service import AuthService
        with patch("app.services.auth_service.verify_jwt", return_value={"sub": "user-1"}):
            payload = AuthService.decode_token("some-token")
        assert payload["sub"] == "user-1"


class TestGetUserIdFromPayload:
    def test_returns_sub(self):
        from app.services.auth_service import AuthService
        uid = AuthService.get_user_id_from_payload({"sub": "user-123"})
        assert uid == "user-123"

    def test_missing_sub_raises(self):
        from app.services.auth_service import AuthService
        with pytest.raises(HTTPException) as exc:
            AuthService.get_user_id_from_payload({})
        assert exc.value.status_code == 401


class TestRequireSupabase:
    def test_raises_503_when_none(self):
        from app.services.auth_service import _require_supabase
        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                _require_supabase()
            assert exc.value.status_code == 503

    def test_returns_client_when_available(self):
        from app.services.auth_service import _require_supabase
        mock_sb = MagicMock()
        with patch("app.services.auth_service.supabase", mock_sb):
            result = _require_supabase()
        assert result is mock_sb


class TestAuthMethods:
    @pytest.mark.asyncio
    async def test_signup_success(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.sign_up.return_value = {"user": {"id": "u1"}}
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.signup("a@b.com", "pass", "Alice", "MIT")
        assert result["user"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_signup_exception_raises_400(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.sign_up.side_effect = RuntimeError("email taken")
        with patch("app.services.auth_service.supabase", mock_sb):
            with pytest.raises(HTTPException) as exc:
                await AuthService.signup("a@b.com", "pass", "Alice", "MIT")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"access_token": "tok"}
        mock_sb.auth.sign_in_with_password.return_value = mock_response
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.login("a@b.com", "pass")
        assert result["access_token"] == "tok"

    @pytest.mark.asyncio
    async def test_login_exception_raises_401(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.sign_in_with_password.side_effect = RuntimeError("bad credentials")
        with patch("app.services.auth_service.supabase", mock_sb):
            with pytest.raises(HTTPException) as exc:
                await AuthService.login("a@b.com", "pass")
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_forgot_password_success(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.reset_password_for_email.return_value = {"success": True}
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.forgot_password("a@b.com")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_exception_raises_400(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.reset_password_for_email.side_effect = RuntimeError("user not found")
        with patch("app.services.auth_service.supabase", mock_sb):
            with pytest.raises(HTTPException) as exc:
                await AuthService.forgot_password("a@b.com")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.verify_otp.return_value = {"success": True}
        mock_sb.auth.update_user.return_value = {"user": {"id": "u1"}}
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.reset_password("a@b.com", "otp123", "newpass")
        assert result["user"]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_reset_password_exception_raises_400(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.verify_otp.side_effect = RuntimeError("invalid otp")
        with patch("app.services.auth_service.supabase", mock_sb):
            with pytest.raises(HTTPException) as exc:
                await AuthService.reset_password("a@b.com", "bad", "pw")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_otp_success(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.verify_otp.return_value = {"success": True}
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.verify_otp("a@b.com", "otp123")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_verify_otp_exception_raises_400(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_sb.auth.verify_otp.side_effect = RuntimeError("expired token")
        with patch("app.services.auth_service.supabase", mock_sb):
            with pytest.raises(HTTPException) as exc:
                await AuthService.verify_otp("a@b.com", "bad")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_login_with_dict_fallback(self):
        from app.services.auth_service import AuthService
        mock_sb = MagicMock()
        mock_response = MagicMock(spec=["dict"])
        mock_response.dict.return_value = {"access_token": "tok"}
        mock_sb.auth.sign_in_with_password.return_value = mock_response
        with patch("app.services.auth_service.supabase", mock_sb):
            result = await AuthService.login("a@b.com", "pass")
        assert result["access_token"] == "tok"
