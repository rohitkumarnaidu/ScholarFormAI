from __future__ import annotations

import json
import time
import pytest
from unittest.mock import MagicMock, patch
pytestmark = [pytest.mark.security]

MODULE = "app.security.jwks_verifier"


class TestResolveJwksUrl:
    def test_uses_explicit_jwks_url(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWKS_URL = "https://example.com/auth/v1/keys"
            mock_s.SUPABASE_URL = ""
            from app.security.jwks_verifier import _resolve_jwks_url
            url = _resolve_jwks_url()
            assert "jwks.json" in url

    def test_uses_supabase_url(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWKS_URL = None
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            from app.security.jwks_verifier import _resolve_jwks_url
            url = _resolve_jwks_url()
            assert url == "https://project.supabase.co/auth/v1/.well-known/jwks.json"

    def test_returns_none_when_no_url(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWKS_URL = None
            mock_s.SUPABASE_URL = None
            from app.security.jwks_verifier import _resolve_jwks_url
            assert _resolve_jwks_url() is None

    def test_jwks_url_not_ending_with_keys_returns_as_is(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWKS_URL = "https://custom.example.com/jwks"
            mock_s.SUPABASE_URL = None
            from app.security.jwks_verifier import _resolve_jwks_url
            url = _resolve_jwks_url()
            assert url == "https://custom.example.com/jwks"


class TestFetchJwks:
    def test_no_url_returns_empty(self):
        with patch(f"{MODULE}._resolve_jwks_url", return_value=None):
            from app.security.jwks_verifier import _fetch_jwks
            assert _fetch_jwks() == {}

    def test_fetch_success(self):
        mock_keys = [{"kid": "key1", "kty": "RSA", "n": "abc", "e": "AQAB"}]
        with patch(f"{MODULE}._resolve_jwks_url", return_value="https://example.com/jwks.json"):
            with patch(f"{MODULE}.httpx.get") as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {"keys": mock_keys}
                from app.security.jwks_verifier import _fetch_jwks
                result = _fetch_jwks()
                assert "key1" in result

    def test_fetch_http_error(self):
        with patch(f"{MODULE}._resolve_jwks_url", return_value="https://example.com/jwks.json"):
            with patch(f"{MODULE}.httpx.get") as mock_get:
                mock_get.side_effect = Exception("HTTP error")
                from app.security.jwks_verifier import _fetch_jwks
                result = _fetch_jwks()
                assert result == {}


class TestGetCachedKeys:
    def test_fresh_cache_returns_cached(self):
        from app.security.jwks_verifier import _JWKS_CACHE
        _JWKS_CACHE["keys"] = {"k1": {"kid": "k1"}}
        _JWKS_CACHE["fetched_at"] = time.time()
        with patch(f"{MODULE}._fetch_jwks") as mock_fetch:
            from app.security.jwks_verifier import _get_cached_keys
            result = _get_cached_keys()
            assert "k1" in result
            mock_fetch.assert_not_called()

    def test_expired_cache_refetches(self):
        from app.security.jwks_verifier import _JWKS_CACHE
        _JWKS_CACHE["keys"] = {}
        _JWKS_CACHE["fetched_at"] = 0.0
        with patch(f"{MODULE}._fetch_jwks", return_value={"k2": {"kid": "k2"}}) as mock_fetch:
            from app.security.jwks_verifier import _get_cached_keys
            result = _get_cached_keys(refresh=True)
            assert "k2" in result
            mock_fetch.assert_called_once()

    def test_empty_cache_refetches(self):
        from app.security.jwks_verifier import _JWKS_CACHE
        _JWKS_CACHE["keys"] = {}
        _JWKS_CACHE["fetched_at"] = 0.0
        with patch(f"{MODULE}._fetch_jwks", return_value={"k3": {"kid": "k3"}}) as mock_fetch:
            from app.security.jwks_verifier import _get_cached_keys
            result = _get_cached_keys()
            assert "k3" in result


class TestDecodeWithSecret:
    def test_no_secret_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWT_SECRET = None
            from app.security.jwks_verifier import _decode_with_secret
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                _decode_with_secret("token", expected_issuer=None)
            assert exc.value.status_code == 401

    def test_successful_decode(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_JWT_SECRET = "my-secret"
            mock_s.ALGORITHM = "HS256"
            with patch(f"{MODULE}.jwt.decode", return_value={"sub": "user1"}) as mock_decode:
                from app.security.jwks_verifier import _decode_with_secret
                result = _decode_with_secret("tok", expected_issuer="iss")
                assert result["sub"] == "user1"
                mock_decode.assert_called_once()


class TestPublicKeyFromJwk:
    def test_rsa_key(self):
        jwk = {"kty": "RSA", "n": "abc", "e": "AQAB", "kid": "k1"}
        with patch(f"{MODULE}.jwt.algorithms.RSAAlgorithm.from_jwk") as mock_rsa:
            mock_rsa.return_value = "rsa-key"
            from app.security.jwks_verifier import _public_key_from_jwk
            result = _public_key_from_jwk(jwk)
            assert result == "rsa-key"

    def test_ec_key(self):
        jwk = {"kty": "EC", "crv": "P-256", "x": "abc", "y": "def"}
        with patch(f"{MODULE}.jwt.algorithms.ECAlgorithm.from_jwk") as mock_ec:
            mock_ec.return_value = "ec-key"
            from app.security.jwks_verifier import _public_key_from_jwk
            result = _public_key_from_jwk(jwk)
            assert result == "ec-key"

    def test_okp_key(self):
        jwk = {"kty": "OKP", "crv": "Ed25519", "x": "abc"}
        with patch(f"{MODULE}.jwt.algorithms.OKPAlgorithm.from_jwk") as mock_okp:
            mock_okp.return_value = "okp-key"
            from app.security.jwks_verifier import _public_key_from_jwk
            result = _public_key_from_jwk(jwk)
            assert result == "okp-key"

    def test_unsupported_key_type(self):
        jwk = {"kty": "DSA"}
        from app.security.jwks_verifier import _public_key_from_jwk
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _public_key_from_jwk(jwk)
        assert exc.value.status_code == 401


class TestDecodeWithJwks:
    def test_missing_kid_raises(self):
        with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256"}):
            from app.security.jwks_verifier import _decode_with_jwks, _RetryableJWTError
            with pytest.raises(_RetryableJWTError):
                _decode_with_jwks("token", expected_issuer=None)

    def test_key_not_in_cache_raises(self):
        with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"kid": "unknown", "alg": "RS256"}):
            with patch(f"{MODULE}._get_cached_keys", return_value={}):
                from app.security.jwks_verifier import _decode_with_jwks, _RetryableJWTError
                with pytest.raises(_RetryableJWTError):
                    _decode_with_jwks("token", expected_issuer=None)

    def test_successful_decode(self):
        mock_jwk = {"kty": "RSA", "n": "abc", "e": "AQAB", "kid": "k1"}
        with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"kid": "k1", "alg": "RS256"}):
            with patch(f"{MODULE}._get_cached_keys", return_value={"k1": mock_jwk}):
                with patch(f"{MODULE}._public_key_from_jwk", return_value="pub-key"):
                    with patch(f"{MODULE}.jwt.decode", return_value={"sub": "user1"}) as mock_decode:
                        from app.security.jwks_verifier import _decode_with_jwks
                        result = _decode_with_jwks("token", expected_issuer=None)
                        assert result["sub"] == "user1"

    def test_invalid_signature_raises(self):
        mock_jwk = {"kty": "RSA", "n": "abc", "e": "AQAB", "kid": "k1"}
        with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"kid": "k1", "alg": "RS256"}):
            with patch(f"{MODULE}._get_cached_keys", return_value={"k1": mock_jwk}):
                with patch(f"{MODULE}._public_key_from_jwk", return_value="pub-key"):
                    with patch(f"{MODULE}.jwt.decode", side_effect=__import__("jwt").InvalidSignatureError("bad")):
                        from app.security.jwks_verifier import _decode_with_jwks, _RetryableJWTError
                        with pytest.raises(_RetryableJWTError):
                            _decode_with_jwks("token", expected_issuer=None)


class TestVerifyJwt:
    def test_empty_token_raises(self):
        from app.security.jwks_verifier import verify_jwt
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            verify_jwt("")
        assert exc.value.status_code == 401

    def test_none_token_raises(self):
        from app.security.jwks_verifier import verify_jwt
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            verify_jwt(None)
        assert exc.value.status_code == 401

    def test_hs_algorithm(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            mock_s.SUPABASE_JWT_SECRET = "secret"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "HS256"}):
                from app.security.jwks_verifier import verify_jwt
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    verify_jwt("token")
                assert exc.value.status_code == 401
                assert "invalid" in str(exc.value.detail).lower()

    def test_rsa_algorithm(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                with patch(f"{MODULE}._decode_with_jwks", return_value={"sub": "user1"}) as mock_jwks:
                    from app.security.jwks_verifier import verify_jwt
                    result = verify_jwt("token")
                    assert result["sub"] == "user1"
                    mock_jwks.assert_called_once_with("token", expected_issuer="https://project.supabase.co/auth/v1", refresh=False)

    def test_retryable_then_refresh_succeeds(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                from app.security.jwks_verifier import _RetryableJWTError
                with patch(f"{MODULE}._decode_with_jwks") as mock_jwks:
                    mock_jwks.side_effect = [_RetryableJWTError("cache miss"), {"sub": "retry-user"}]
                    mock_jwks_with_refresh = MagicMock(return_value={"sub": "retry-user"})
                    from app.security.jwks_verifier import verify_jwt
                    result = verify_jwt("token")
                    assert result["sub"] == "retry-user"
                    assert mock_jwks.call_count == 2

    def test_retryable_then_fail_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                from app.security.jwks_verifier import _RetryableJWTError
                with patch(f"{MODULE}._decode_with_jwks", side_effect=[_RetryableJWTError("miss"), _RetryableJWTError("still miss")]):
                    from app.security.jwks_verifier import verify_jwt
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        verify_jwt("token")
                    assert exc.value.status_code == 401

    def test_expired_signature_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                with patch(f"{MODULE}._decode_with_jwks", side_effect=__import__("jwt").ExpiredSignatureError("expired")):
                    from app.security.jwks_verifier import verify_jwt
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        verify_jwt("token")
                    assert exc.value.status_code == 401
                    assert "expired" in str(exc.value.detail).lower()

    def test_invalid_issuer_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                with patch(f"{MODULE}._decode_with_jwks", side_effect=__import__("jwt").InvalidIssuerError("bad iss")):
                    from app.security.jwks_verifier import verify_jwt
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        verify_jwt("token")
                    assert exc.value.status_code == 401

    def test_invalid_audience_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                with patch(f"{MODULE}._decode_with_jwks", side_effect=__import__("jwt").InvalidAudienceError("bad aud")):
                    from app.security.jwks_verifier import verify_jwt
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        verify_jwt("token")
                    assert exc.value.status_code == 401

    def test_generic_invalid_token_raises(self):
        with patch(f"{MODULE}.settings") as mock_s:
            mock_s.SUPABASE_URL = "https://project.supabase.co"
            with patch(f"{MODULE}.jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "k1"}):
                with patch(f"{MODULE}._decode_with_jwks", side_effect=__import__("jwt").InvalidTokenError("generic")):
                    from app.security.jwks_verifier import verify_jwt
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as exc:
                        verify_jwt("token")
                    assert exc.value.status_code == 401
