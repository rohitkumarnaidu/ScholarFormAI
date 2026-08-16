# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException


class TestDecodeToken:
    def test_decode_token_delegates_to_verify_jwt(self):
        from app.services.auth_service import AuthService

        token = "some.jwt.token"
        with patch("app.services.auth_service.verify_jwt", return_value={"sub": "user-1"}) as mock_v:
            result = AuthService.decode_token(token)
        assert result == {"sub": "user-1"}
        mock_v.assert_called_once_with(token)


class TestGetUserIdFromPayload:
    def test_valid_payload_returns_sub(self):
        from app.services.auth_service import AuthService

        result = AuthService.get_user_id_from_payload({"sub": "user-123"})
        assert result == "user-123"

    def test_missing_sub_raises_401(self):
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            AuthService.get_user_id_from_payload({})
        assert exc.value.status_code == 401

    def test_none_sub_raises_401(self):
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            AuthService.get_user_id_from_payload({"sub": None})
        assert exc.value.status_code == 401


class TestSignup:
    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.auth_service.supabase") as mock_sb:
            mock_sb.auth.sign_up.return_value = {"user": {"id": "new-user"}}
            yield mock_sb

    async def test_signup_success(self, mock_supabase):
        from app.services.auth_service import AuthService

        result = await AuthService.signup("test@test.com", "password123", "Test User", "Test Uni")
        assert result == {"user": {"id": "new-user"}}

    async def test_signup_supabase_unavail(self):
        from app.services.auth_service import AuthService

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                await AuthService.signup("a@b.com", "pw", "N", "U")
            assert exc.value.status_code == 503

    async def test_signup_generic_exception(self, mock_supabase):
        mock_supabase.auth.sign_up.side_effect = RuntimeError("API down")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.signup("a@b.com", "pw", "N", "U")
        assert exc.value.status_code == 400


class TestLogin:
    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.auth_service.supabase") as mock_sb:
            response = type("Resp", (), {"model_dump": lambda self: {"access_token": "tok", "user": {"id": "u1"}}})()
            mock_sb.auth.sign_in_with_password.return_value = response
            yield mock_sb

    async def test_login_success(self, mock_supabase):
        from app.services.auth_service import AuthService

        result = await AuthService.login("a@b.com", "pw")
        assert result["access_token"] == "tok"

    async def test_login_supabase_unavail(self):
        from app.services.auth_service import AuthService

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                await AuthService.login("a@b.com", "pw")
            assert exc.value.status_code == 503

    async def test_login_generic_exception(self, mock_supabase):
        mock_supabase.auth.sign_in_with_password.side_effect = RuntimeError("auth fail")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.login("a@b.com", "pw")
        assert exc.value.status_code == 401

    async def test_login_response_has_dict_not_model_dump(self, mock_supabase):
        class RespWithDict:
            def dict(self):
                return {"access_token": "tok", "user": {"id": "u1"}}

        mock_supabase.auth.sign_in_with_password.return_value = RespWithDict()
        from app.services.auth_service import AuthService

        result = await AuthService.login("a@b.com", "pw")
        assert result["access_token"] == "tok"

    async def test_login_response_neither_model_dump_nor_dict(self, mock_supabase):
        mock_supabase.auth.sign_in_with_password.return_value = "raw_response"
        from app.services.auth_service import AuthService

        result = await AuthService.login("a@b.com", "pw")
        assert result == "raw_response"

    async def test_login_http_exception_passthrough(self, mock_supabase):
        mock_supabase.auth.sign_in_with_password.side_effect = HTTPException(status_code=429, detail="rate limited")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.login("a@b.com", "pw")
        assert exc.value.status_code == 429


class TestForgotPassword:
    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.auth_service.supabase") as mock_sb:
            mock_sb.auth.reset_password_for_email.return_value = {"ok": True}
            yield mock_sb

    async def test_success(self, mock_supabase):
        from app.services.auth_service import AuthService

        result = await AuthService.forgot_password("a@b.com")
        assert result == {"ok": True}

    async def test_supabase_unavail(self):
        from app.services.auth_service import AuthService

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                await AuthService.forgot_password("a@b.com")
            assert exc.value.status_code == 503

    async def test_generic_exception(self, mock_supabase):
        mock_supabase.auth.reset_password_for_email.side_effect = ValueError("bad email")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.forgot_password("a@b.com")
        assert exc.value.status_code == 400

    async def test_http_exception_passthrough(self, mock_supabase):
        mock_supabase.auth.reset_password_for_email.side_effect = HTTPException(status_code=500, detail="internal")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.forgot_password("a@b.com")
        assert exc.value.status_code == 500


class TestResetPassword:
    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.auth_service.supabase") as mock_sb:
            mock_sb.auth.verify_otp.return_value = {"ok": True}
            mock_sb.auth.update_user.return_value = {"user": {"id": "u1"}}
            yield mock_sb

    async def test_success(self, mock_supabase):
        from app.services.auth_service import AuthService

        result = await AuthService.reset_password("a@b.com", "123456", "newpw")
        assert result == {"user": {"id": "u1"}}

    async def test_supabase_unavail(self):
        from app.services.auth_service import AuthService

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                await AuthService.reset_password("a@b.com", "otp", "newpw")
            assert exc.value.status_code == 503

    async def test_generic_exception(self, mock_supabase):
        mock_supabase.auth.verify_otp.side_effect = RuntimeError("otp fail")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.reset_password("a@b.com", "otp", "newpw")
        assert "Reset failed" in str(exc.value.detail)

    async def test_http_exception_passthrough(self, mock_supabase):
        mock_supabase.auth.verify_otp.side_effect = HTTPException(status_code=400, detail="bad otp")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.reset_password("a@b.com", "otp", "newpw")
        assert exc.value.status_code == 400


class TestVerifyOtp:
    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.auth_service.supabase") as mock_sb:
            mock_sb.auth.verify_otp.return_value = {"ok": True}
            yield mock_sb

    async def test_success(self, mock_supabase):
        from app.services.auth_service import AuthService

        result = await AuthService.verify_otp("a@b.com", "tok")
        assert result == {"ok": True}

    async def test_supabase_unavail(self):
        from app.services.auth_service import AuthService

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                await AuthService.verify_otp("a@b.com", "tok")
            assert exc.value.status_code == 503

    async def test_generic_exception(self, mock_supabase):
        mock_supabase.auth.verify_otp.side_effect = RuntimeError("verify fail")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.verify_otp("a@b.com", "tok")
        assert "Verification failed" in str(exc.value.detail)

    async def test_http_exception_passthrough(self, mock_supabase):
        mock_supabase.auth.verify_otp.side_effect = HTTPException(status_code=401, detail="bad tok")
        from app.services.auth_service import AuthService

        with pytest.raises(HTTPException) as exc:
            await AuthService.verify_otp("a@b.com", "tok")
        assert exc.value.status_code == 401


class TestRequireSupabase:
    def test_raises_503_when_none(self):
        from app.services.auth_service import _require_supabase

        with patch("app.services.auth_service.supabase", None):
            with pytest.raises(HTTPException) as exc:
                _require_supabase()
            assert exc.value.status_code == 503

    def test_returns_supabase_when_avail(self):
        from app.services.auth_service import _require_supabase

        with patch("app.services.auth_service.supabase", "mock_sb"):
            result = _require_supabase()
        assert result == "mock_sb"
