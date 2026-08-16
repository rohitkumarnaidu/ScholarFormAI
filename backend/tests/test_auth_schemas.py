import pytest
from pydantic import ValidationError


class TestSignupRequest:
    def test_valid_signup(self):
        from app.schemas.auth import SignupRequest

        req = SignupRequest(
            full_name="  John Doe  ",
            email="john@example.com",
            password="Password1$",
            terms_accepted=True,
        )
        assert req.full_name == "John Doe"
        assert req.email == "john@example.com"
        assert req.institution is None

    def test_valid_signup_with_institution(self):
        from app.schemas.auth import SignupRequest

        req = SignupRequest(
            full_name="Jane Doe",
            email="jane@example.com",
            institution="MIT",
            password="Password1$",
            terms_accepted=True,
        )
        assert req.institution == "MIT"

    def test_terms_must_be_true(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError, match="Terms and conditions must be accepted"):
            SignupRequest(
                full_name="John",
                email="john@example.com",
                password="Password1$",
                terms_accepted=False,
            )

    def test_weak_password(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError, match="contain an uppercase letter"):
            SignupRequest(
                full_name="John",
                email="john@example.com",
                password="alllowercase1$",
                terms_accepted=True,
            )

    def test_password_no_uppercase(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError, match="must be at least 8 characters"):
            SignupRequest(
                full_name="John",
                email="john@example.com",
                password="lowercase1$",
                terms_accepted=True,
            )

    def test_password_no_special_char(self):
        from app.schemas.auth import SignupRequest

        with pytest.raises(ValidationError, match="must be at least 8 characters"):
            SignupRequest(
                full_name="John",
                email="john@example.com",
                password="Password1",  # no special char, but wait - PASSWORD_PATTERN requires special
                terms_accepted=True,
            )


class TestLoginRequest:
    def test_valid_login(self):
        from app.schemas.auth import LoginRequest

        req = LoginRequest(email="john@example.com", password="Password1$")
        assert req.email == "john@example.com"
        assert req.password == "Password1$"

    def test_invalid_email(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="not-email", password="Password1$")

    def test_empty_password(self):
        from app.schemas.auth import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="john@example.com", password="")


class TestForgotPasswordRequest:
    def test_valid(self):
        from app.schemas.auth import ForgotPasswordRequest

        req = ForgotPasswordRequest(email="john@example.com")
        assert req.email == "john@example.com"

    def test_invalid_email(self):
        from app.schemas.auth import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-email")


class TestVerifyOTPRequest:
    def test_valid(self):
        from app.schemas.auth import VerifyOTPRequest

        req = VerifyOTPRequest(email="john@example.com", otp="123456")
        assert req.otp == "123456"

    def test_otp_too_short(self):
        from app.schemas.auth import VerifyOTPRequest

        with pytest.raises(ValidationError):
            VerifyOTPRequest(email="john@example.com", otp="12345")

    def test_otp_too_long(self):
        from app.schemas.auth import VerifyOTPRequest

        with pytest.raises(ValidationError):
            VerifyOTPRequest(email="john@example.com", otp="1234567")

    def test_otp_non_numeric(self):
        from app.schemas.auth import VerifyOTPRequest

        with pytest.raises(ValidationError):
            VerifyOTPRequest(email="john@example.com", otp="abcdef")


class TestResetPasswordRequest:
    def test_valid(self):
        from app.schemas.auth import ResetPasswordRequest

        req = ResetPasswordRequest(
            email="john@example.com",
            otp="123456",
            new_password="NewPassword1$",
        )
        assert req.new_password == "NewPassword1$"

    def test_weak_new_password(self):
        from app.schemas.auth import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(
                email="john@example.com",
                otp="123456",
                new_password="weak",
            )


class TestAuthTokenResponse:
    def test_valid(self):
        from app.schemas.auth import AuthTokenResponse

        resp = AuthTokenResponse(access_token="token123")
        assert resp.access_token == "token123"
        assert resp.token_type == "bearer"
        assert resp.expires_in is None

    def test_with_all_fields(self):
        from app.schemas.auth import AuthTokenResponse

        resp = AuthTokenResponse(
            access_token="token",
            expires_in=3600,
            user_id="user-1",
            email="john@example.com",
        )
        assert resp.expires_in == 3600
        assert resp.user_id == "user-1"
        assert resp.email == "john@example.com"


class TestMessageResponse:
    def test_valid(self):
        from app.schemas.auth import MessageResponse

        resp = MessageResponse(message="Done")
        assert resp.message == "Done"
        assert resp.success is True

    def test_false_success(self):
        from app.schemas.auth import MessageResponse

        resp = MessageResponse(message="Failed", success=False)
        assert resp.success is False


class TestOTPVerifyResponse:
    def test_valid(self):
        from app.schemas.auth import OTPVerifyResponse

        resp = OTPVerifyResponse(verified=True, message="OTP valid")
        assert resp.verified is True
        assert resp.message == "OTP valid"


class TestValidatePasswordStrength:
    def test_valid_password(self):
        from app.schemas.auth import _validate_password_strength

        result = _validate_password_strength("Abcdef1$")
        assert result == "Abcdef1$"

    def test_no_uppercase(self):
        from app.schemas.auth import _validate_password_strength

        with pytest.raises(ValueError):
            _validate_password_strength("abcdef1$")

    def test_no_lowercase(self):
        from app.schemas.auth import _validate_password_strength

        with pytest.raises(ValueError):
            _validate_password_strength("ABCDEF1$")

    def test_no_digit(self):
        from app.schemas.auth import _validate_password_strength

        with pytest.raises(ValueError):
            _validate_password_strength("Abcdefg$")

    def test_no_special_char(self):
        from app.schemas.auth import _validate_password_strength

        with pytest.raises(ValueError):
            _validate_password_strength("Abcdefg1")

    def test_too_short(self):
        from app.schemas.auth import _validate_password_strength

        with pytest.raises(ValueError):
            _validate_password_strength("Ab1$")
