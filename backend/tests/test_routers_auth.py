from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user

_VALID_PW = "Str0ng!P@ss1"
_WEAK_PW = "123"


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


@pytest.fixture
def client():
    from app.schemas.user import User
    user = User(id="user-123", email="test@example.com", role="authenticated")
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as tc:
        tc.mock_user = user
        yield tc
    app.dependency_overrides = {}


class TestReadUsersMe:
    def test_returns_current_user(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        p = resp.json()
        assert p["error"] is None
        assert p["data"]["id"] == "user-123"


class TestSignup:
    def _payload(self, **kw):
        defaults = dict(email="a@b.com", password=_VALID_PW, full_name="Alice", terms_accepted=True)
        return {**defaults, **kw}

    def test_success(self, client):
        with patch("app.routers.v1.auth.AuthService.signup", new=AsyncMock(return_value={"id": "new-user", "email": "a@b.com"})):
            resp = client.post("/api/v1/auth/signup", json=self._payload())
        assert resp.status_code == 200
        assert resp.json()["error"] is None

    def test_weak_password(self, client):
        resp = client.post("/api/v1/auth/signup", json=self._payload(password=_WEAK_PW))
        assert resp.status_code == 422

    def test_missing_terms(self, client):
        resp = client.post("/api/v1/auth/signup", json=self._payload(terms_accepted=False))
        assert resp.status_code == 422

    def test_missing_email(self, client):
        resp = client.post("/api/v1/auth/signup", json=self._payload(email=None))
        assert resp.status_code == 422


class TestLogin:
    def test_success(self, client):
        with patch("app.routers.v1.auth.AuthService.login", new=AsyncMock(return_value={"token": "jwt", "user": {"id": "u1"}})):
            resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": _VALID_PW})
        assert resp.status_code == 200
        assert resp.json()["data"]["token"] == "jwt"

    def test_failure(self, client):
        with patch("app.routers.v1.auth.AuthService.login", new=AsyncMock(side_effect=PermissionError("fail"))):
            resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
        assert resp.status_code == 500

    def test_missing_password(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "a@b.com"})
        assert resp.status_code == 422


class TestForgotPassword:
    def test_success(self, client):
        with patch("app.routers.v1.auth.AuthService.forgot_password", new=AsyncMock(return_value={"message": "sent"})):
            resp = client.post("/api/v1/auth/forgot-password", json={"email": "a@b.com"})
        assert resp.status_code == 200

    def test_missing_email(self, client):
        resp = client.post("/api/v1/auth/forgot-password", json={})
        assert resp.status_code == 422


class TestVerifyOTP:
    def test_success(self, client):
        with patch("app.routers.v1.auth.AuthService.verify_otp", new=AsyncMock(return_value={"valid": True})):
            resp = client.post("/api/v1/auth/verify-otp", json={"email": "a@b.com", "otp": "123456"})
        assert resp.status_code == 200

    def test_bad_otp_length(self, client):
        resp = client.post("/api/v1/auth/verify-otp", json={"email": "a@b.com", "otp": "12"})
        assert resp.status_code == 422

    def test_non_numeric_otp(self, client):
        resp = client.post("/api/v1/auth/verify-otp", json={"email": "a@b.com", "otp": "abcdef"})
        assert resp.status_code == 422

    def test_missing_otp(self, client):
        resp = client.post("/api/v1/auth/verify-otp", json={"email": "a@b.com"})
        assert resp.status_code == 422


class TestResetPassword:
    def test_success(self, client):
        with patch("app.routers.v1.auth.AuthService.reset_password", new=AsyncMock(return_value={"message": "done"})):
            resp = client.post("/api/v1/auth/reset-password", json={
                "email": "a@b.com", "otp": "123456", "new_password": _VALID_PW,
            })
        assert resp.status_code == 200

    def test_weak_new_password(self, client):
        resp = client.post("/api/v1/auth/reset-password", json={
            "email": "a@b.com", "otp": "123456", "new_password": _WEAK_PW,
        })
        assert resp.status_code == 422

    def test_missing_fields(self, client):
        resp = client.post("/api/v1/auth/reset-password", json={"email": "a@b.com"})
        assert resp.status_code == 422
