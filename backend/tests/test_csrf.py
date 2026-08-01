from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCSRFMiddleware:
    def test_module_imports(self):
        import app.middleware.csrf
        assert app.middleware.csrf is not None


class TestGetCsrfSecret:
    def test_uses_signed_url_secret(self):
        with patch("app.middleware.csrf.settings.SIGNED_URL_SECRET", "my-secret"):
            with patch("app.middleware.csrf.settings.SUPABASE_JWT_SECRET", "jwt-secret"):
                from app.middleware.csrf import _get_csrf_secret
                result = _get_csrf_secret()
        assert result == b"my-secret"

    def test_falls_back_to_jwt_secret(self):
        with patch("app.middleware.csrf.settings.SIGNED_URL_SECRET", None):
            with patch("app.middleware.csrf.settings.SUPABASE_JWT_SECRET", "jwt-secret"):
                from app.middleware.csrf import _get_csrf_secret
                result = _get_csrf_secret()
        assert result == b"jwt-secret"

    def test_fallback_when_no_secret(self):
        with patch("app.middleware.csrf.settings.SIGNED_URL_SECRET", None):
            with patch("app.middleware.csrf.settings.SUPABASE_JWT_SECRET", None):
                from app.middleware.csrf import _get_csrf_secret
                result = _get_csrf_secret()
        assert result == b"csrf-fallback-secret-do-not-use-in-production"


class TestGenerateToken:
    def test_generates_valid_format(self):
        from app.middleware.csrf import generate_csrf_token
        token = generate_csrf_token()
        parts = token.split(":")
        assert len(parts) == 3
        assert parts[0].isdigit()


class TestValidateToken:
    def test_valid_token(self):
        from app.middleware.csrf import generate_csrf_token, validate_csrf_token
        token = generate_csrf_token()
        assert validate_csrf_token(token) is True

    def test_empty_token_false(self):
        from app.middleware.csrf import validate_csrf_token
        assert validate_csrf_token("") is False

    def test_wrong_format_false(self):
        from app.middleware.csrf import validate_csrf_token
        assert validate_csrf_token("bad") is False

    def test_expired_token_false(self):
        import time

        from app.middleware.csrf import validate_csrf_token
        old_ts = str(int(time.time()) - 7200)
        token = f"{old_ts}:random:sig"
        assert validate_csrf_token(token) is False

    def test_bad_signature_false(self):
        import time

        from app.middleware.csrf import validate_csrf_token
        now = str(int(time.time()))
        token = f"{now}:random:badsig"
        assert validate_csrf_token(token) is False

    def test_non_numeric_timestamp_false(self):
        from app.middleware.csrf import validate_csrf_token
        assert validate_csrf_token("abc:random:sig") is False


class TestIsExemptPath:
    def test_api_path_is_exempt(self):
        from app.middleware.csrf import _is_exempt_path
        assert _is_exempt_path("/api/v1/documents") is True

    def test_non_api_path_not_exempt(self):
        from app.middleware.csrf import _is_exempt_path
        assert _is_exempt_path("/some/other/path") is False


class TestHasBearerAuth:
    def test_with_bearer_header(self):
        from app.middleware.csrf import _has_bearer_auth
        request = MagicMock()
        request.headers.get.return_value = "Bearer mytoken"
        assert _has_bearer_auth(request) is True

    def test_without_bearer_header(self):
        from app.middleware.csrf import _has_bearer_auth
        request = MagicMock()
        request.headers.get.return_value = ""
        assert _has_bearer_auth(request) is False
