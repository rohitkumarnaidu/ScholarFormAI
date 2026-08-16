from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetCsrfSecret:
    def test_uses_signed_url_secret(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.SIGNED_URL_SECRET = "my-secret"
            mock_settings.SUPABASE_JWT_SECRET = "jwt-secret"
            from app.middleware.csrf import _get_csrf_secret

            secret = _get_csrf_secret()
            assert secret == b"my-secret"

    def test_falls_back_to_jwt_secret(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.SIGNED_URL_SECRET = None
            mock_settings.SUPABASE_JWT_SECRET = "jwt-secret"
            from app.middleware.csrf import _get_csrf_secret

            secret = _get_csrf_secret()
            assert secret == b"jwt-secret"

    def test_fallback_warning_secret(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.SIGNED_URL_SECRET = None
            mock_settings.SUPABASE_JWT_SECRET = None
            from app.middleware.csrf import _get_csrf_secret

            secret = _get_csrf_secret()
            assert b"csrf-fallback" in secret


class TestGenerateCsrfToken:
    def test_token_has_three_parts(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            from app.middleware.csrf import generate_csrf_token

            token = generate_csrf_token()
            parts = token.split(":")
            assert len(parts) == 3

    def test_timestamp_is_numeric(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            from app.middleware.csrf import generate_csrf_token

            token = generate_csrf_token()
            timestamp_str = token.split(":")[0]
            assert timestamp_str.isdigit()


class TestValidateCsrfToken:
    def test_empty_token(self):
        from app.middleware.csrf import validate_csrf_token

        assert validate_csrf_token("") is False

    def test_none_token(self):
        from app.middleware.csrf import validate_csrf_token

        assert validate_csrf_token(None) is False

    def test_wrong_parts(self):
        from app.middleware.csrf import validate_csrf_token

        assert validate_csrf_token("only:two") is False

    def test_invalid_timestamp(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            from app.middleware.csrf import validate_csrf_token

            assert validate_csrf_token("notanumber:raw:sig") is False

    def test_expired_token(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            with patch("app.middleware.csrf.time.time", return_value=9999999999):
                from app.middleware.csrf import validate_csrf_token

                assert validate_csrf_token("1000000000:raw:somesignature") is False

    def test_valid_token(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            with patch("app.middleware.csrf.time.time") as mock_time:
                mock_time.return_value = 1000000000
                from app.middleware.csrf import generate_csrf_token, validate_csrf_token

                token = generate_csrf_token()
                mock_time.return_value = 1000000300  # 5 min later, still valid
                assert validate_csrf_token(token) is True

    def test_bad_signature(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=b"test-secret"):
            with patch("app.middleware.csrf.time.time", return_value=1000000000):
                from app.middleware.csrf import validate_csrf_token

                assert validate_csrf_token("1000000000:raw:bad-signature") is False


class TestIsExemptPath:
    def test_api_path_exempt(self):
        from app.middleware.csrf import _is_exempt_path

        assert _is_exempt_path("/api/v1/documents") is True

    def test_health_path_exempt(self):
        from app.middleware.csrf import _is_exempt_path

        assert _is_exempt_path("/health") is True

    def test_regular_path_not_exempt(self):
        from app.middleware.csrf import _is_exempt_path

        assert _is_exempt_path("/some-page") is False


class TestHasBearerAuth:
    def test_has_bearer(self):
        from app.middleware.csrf import _has_bearer_auth

        request = MagicMock()
        request.headers = {"authorization": "Bearer token123"}
        assert _has_bearer_auth(request) is True

    def test_no_auth_header(self):
        from app.middleware.csrf import _has_bearer_auth

        request = MagicMock()
        request.headers = {}
        assert _has_bearer_auth(request) is False

    def test_basic_auth_not_bearer(self):
        from app.middleware.csrf import _has_bearer_auth

        request = MagicMock()
        request.headers = {"authorization": "Basic dXNlcjpwYXNz"}
        assert _has_bearer_auth(request) is False


class TestCSRFMiddleware:
    @pytest.mark.asyncio
    async def test_safe_method_sets_cookie(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.DEBUG = True
            mock_settings.SIGNED_URL_SECRET = "test"
            from app.middleware.csrf import CSRFMiddleware

            mw = CSRFMiddleware(MagicMock())
            request = MagicMock()
            request.method = "GET"
            request.cookies = {}
            response = MagicMock()
            response.headers = {}
            call_next = AsyncMock(return_value=response)
            result = await mw.dispatch(request, call_next)
            result.set_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_method_skip_cookie_if_present(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.DEBUG = True
            from app.middleware.csrf import CSRFMiddleware

            mw = CSRFMiddleware(MagicMock())
            request = MagicMock()
            request.method = "GET"
            request.cookies = {"csrf_token": "existing"}
            response = MagicMock()
            response.headers = {}
            call_next = AsyncMock(return_value=response)
            result = await mw.dispatch(request, call_next)
            assert result == response

    @pytest.mark.asyncio
    async def test_exempt_path_passes(self):
        from app.middleware.csrf import CSRFMiddleware

        mw = CSRFMiddleware(MagicMock())
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents"
        call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_bearer_auth_passes(self):
        from app.middleware.csrf import CSRFMiddleware

        mw = CSRFMiddleware(MagicMock())
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/custom"
        request.headers = {"authorization": "Bearer token"}
        call_next = AsyncMock(return_value="response")
        result = await mw.dispatch(request, call_next)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_missing_tokens_returns_403(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.DEBUG = True
            from app.middleware.csrf import CSRFMiddleware

            mw = CSRFMiddleware(MagicMock())
            request = MagicMock()
            request.method = "POST"
            request.url.path = "/custom"
            request.headers = {}
            request.cookies = {}
            call_next = AsyncMock()
            result = await mw.dispatch(request, call_next)
            assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_returns_403(self):
        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.DEBUG = True
            from app.middleware.csrf import CSRFMiddleware

            mw = CSRFMiddleware(MagicMock())
            request = MagicMock()
            request.method = "POST"
            request.url.path = "/custom"
            request.cookies = {"csrf_token": "some-cookie"}
            request.headers = {"X-CSRF-Token": "invalid-token"}
            call_next = AsyncMock()
            result = await mw.dispatch(request, call_next)
            assert result.status_code == 403
