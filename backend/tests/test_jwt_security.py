import time
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.security]


class TestJWTTokenValidation:

    def test_expired_jwt_rejected(self):
        import jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "iss": "https://supabase.co/auth/v1",
            "exp": int(time.time()) - 3600,
            "iat": int(time.time()) - 7200,
        }
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            from app.security.jwks_verifier import _decode_with_secret
            with pytest.raises(Exception):
                _decode_with_secret(
                    jwt.encode(payload, "test-secret", algorithm="HS256"),
                    expected_issuer="https://supabase.co/auth/v1",
                )

    def test_jwt_wrong_audience_rejected(self):
        import jwt
        payload = {
            "sub": "user-1",
            "aud": "wrong-audience",
            "iss": "https://supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            from app.security.jwks_verifier import _decode_with_secret
            with pytest.raises(Exception):
                _decode_with_secret(token, expected_issuer="https://supabase.co/auth/v1")

    def test_jwt_wrong_issuer_rejected(self):
        import jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "iss": "https://evil.com/auth/v1",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            from app.security.jwks_verifier import _decode_with_secret
            with pytest.raises(Exception):
                _decode_with_secret(token, expected_issuer="https://supabase.co/auth/v1")

    def test_malformed_jwt_rejected(self):
        from fastapi import HTTPException

        from app.security.jwks_verifier import verify_jwt
        with pytest.raises(HTTPException) as exc:
            verify_jwt("not.a.jwt")
        assert exc.value.status_code == 401

    def test_empty_token_rejected(self):
        from fastapi import HTTPException

        from app.security.jwks_verifier import verify_jwt
        with pytest.raises(HTTPException) as exc:
            verify_jwt("")
        assert exc.value.status_code == 401

    def test_blank_token_rejected(self):
        from fastapi import HTTPException

        from app.security.jwks_verifier import verify_jwt
        with pytest.raises(HTTPException) as exc:
            verify_jwt("   ")
        assert exc.value.status_code == 401

    def test_tampered_signature_rejected(self):
        import jwt

        from app.security.jwks_verifier import verify_jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "iss": "https://supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "real-secret", algorithm="HS256")
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".tampered-signature"
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "real-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            with pytest.raises(Exception):
                verify_jwt(tampered)

    def test_jwt_with_none_algorithm_rejected(self):
        import jwt

        from app.security.jwks_verifier import verify_jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "iss": "https://supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, None, algorithm=None, headers={"alg": "none"})
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            with pytest.raises(Exception):
                verify_jwt(token)

    def test_jwt_algorithm_confusion_hs256_vs_rs256_prevented(self):
        import jwt

        from app.security.jwks_verifier import verify_jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "iss": "https://supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "known-public-key", algorithm="HS256")
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = "https://supabase.co"
            ms.SUPABASE_JWKS_URL = "https://supabase.co/auth/v1/.well-known/jwks.json"
            ms.ALGORITHM = "HS256"
            with pytest.raises(Exception):
                verify_jwt(token)

    def test_valid_jwt_accepted(self):
        import jwt

        from app.security.jwks_verifier import verify_jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = "test-secret"
            ms.SUPABASE_URL = None
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            result = verify_jwt(token)
        assert result["sub"] == "user-1"


class TestJWTKeyManagement:

    def test_jwks_fetch_failure_does_not_crash(self):
        from app.security.jwks_verifier import _fetch_jwks
        with patch("app.security.jwks_verifier.httpx.get") as mock_get:
            mock_get.side_effect = Exception("Network error")
            result = _fetch_jwks()
        assert result == {}

    def test_jwks_cache_ttl_respected(self):
        from app.security.jwks_verifier import _get_cached_keys
        with (
            patch("app.security.jwks_verifier._fetch_jwks") as mock_fetch,
            patch("app.security.jwks_verifier._JWKS_CACHE", new={"keys": {"kid-1": {"kty": "RSA"}}, "fetched_at": time.time()}),
        ):
            result = _get_cached_keys(refresh=False)
            mock_fetch.assert_not_called()
            assert "kid-1" in result

    def test_jwks_cache_expired_refetches(self):
        from app.security.jwks_verifier import _get_cached_keys
        old_time = time.time() - 7200
        with (
            patch("app.security.jwks_verifier._fetch_jwks", return_value={"kid-new": {"kty": "RSA"}}) as mock_fetch,
            patch("app.security.jwks_verifier._JWKS_CACHE", new={"keys": {"kid-1": {"kty": "RSA"}}, "fetched_at": old_time}),
        ):
            result = _get_cached_keys(refresh=False)
            mock_fetch.assert_called_once()
            assert "kid-new" in result

    def test_expired_jwks_key_handled_gracefully(self):
        import jwt

        from app.security.jwks_verifier import verify_jwt
        payload = {
            "sub": "user-1",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWT_SECRET = None
            ms.SUPABASE_URL = None
            ms.SUPABASE_JWKS_URL = None
            ms.ALGORITHM = "HS256"
            with pytest.raises(Exception):
                verify_jwt(token)

    def test_jwks_resolve_url_handles_missing_config(self):
        from app.security.jwks_verifier import _resolve_jwks_url
        with patch("app.security.jwks_verifier.settings") as ms:
            ms.SUPABASE_JWKS_URL = None
            ms.SUPABASE_URL = None
            result = _resolve_jwks_url()
        assert result is None


class TestJWTAuthService:

    def test_decode_token_invalid_401(self):
        from fastapi import HTTPException

        from app.services.auth_service import AuthService
        with pytest.raises(HTTPException) as exc:
            AuthService.decode_token("invalid-token")
        assert exc.value.status_code == 401

    def test_get_user_id_from_payload_returns_sub(self):
        from app.services.auth_service import AuthService
        result = AuthService.get_user_id_from_payload({"sub": "user-abc"})
        assert result == "user-abc"

    def test_get_user_id_from_payload_missing_sub_401(self):
        from fastapi import HTTPException

        from app.services.auth_service import AuthService
        with pytest.raises(HTTPException) as exc:
            AuthService.get_user_id_from_payload({"email": "test@test.com"})
        assert exc.value.status_code == 401

    def test_decode_token_proxies_to_verify_jwt(self):
        from app.services.auth_service import AuthService
        with patch("app.services.auth_service.verify_jwt") as mock_verify:
            mock_verify.return_value = {"sub": "user-1", "aud": "authenticated"}
            result = AuthService.decode_token("some-token")
            mock_verify.assert_called_once_with("some-token")
            assert result["sub"] == "user-1"
