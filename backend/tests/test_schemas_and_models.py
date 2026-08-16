import pytest
from pydantic import ValidationError


class TestAuthSchemas:
    def test_signup_request_valid(self):
        from app.schemas.auth import SignupRequest

        data = SignupRequest(
            email="test@example.com", password="Abc12345!_", terms_accepted=True, full_name="Test User"
        )
        assert data.email == "test@example.com"

    def test_signup_missing_terms(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError):
            SignupRequest(email="test@example.com", password="Abc12345!_", full_name="Test")

    def test_signup_weak_password(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError):
            SignupRequest(email="test@example.com", password="weak", terms_accepted=True, full_name="Test")

    def test_login_request(self):
        from app.schemas.auth import LoginRequest

        data = LoginRequest(email="test@example.com", password="somepass")
        assert data.email == "test@example.com"

    def test_forgot_password(self):
        from app.schemas.auth import ForgotPasswordRequest

        data = ForgotPasswordRequest(email="test@example.com")
        assert data.email == "test@example.com"

    def test_reset_password(self):
        from app.schemas.auth import ResetPasswordRequest

        data = ResetPasswordRequest(email="test@example.com", otp="123456", new_password="NewStrongPass1!")
        assert data.email == "test@example.com"

    def test_verify_otp_valid(self):
        from app.schemas.auth import VerifyOTPRequest

        data = VerifyOTPRequest(email="test@example.com", otp="123456")
        assert data.otp == "123456"

    def test_verify_otp_invalid_length(self):
        from app.schemas.auth import VerifyOTPRequest

        with pytest.raises(ValidationError):
            VerifyOTPRequest(email="test@example.com", otp="12345")

    def test_verify_otp_non_digits(self):
        from app.schemas.auth import VerifyOTPRequest

        with pytest.raises(ValidationError):
            VerifyOTPRequest(email="test@example.com", otp="abcdef")


class TestUserSchemas:
    def test_user_valid(self):
        from app.schemas.user import User

        data = User(id="user-1", email="test@example.com", role="user")
        assert data.email == "test@example.com"

    def test_user_default_role(self):
        from app.schemas.user import User

        data = User(id="user-1", email="test@example.com")
        assert data.role == "authenticated"

    def test_user_invalid_email(self):
        from app.schemas.user import User

        with pytest.raises(ValidationError):
            User(id="user-1", email="not-an-email")


class TestUserModel:
    def test_user_created(self):
        from app.models.user import User

        user = User(id="user-1", email="test@example.com", role="user")
        assert user.email == "test@example.com"

    def test_user_no_default_role(self):
        from app.models.user import User

        user = User(id="user-1", email="test@example.com")
        assert user.role is None
