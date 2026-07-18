# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep tests for JWT/JWKS verification.

Extensions to test_jwks_verifier.py covering edge cases:
  - RS256 valid token accepted
  - HS256 rejected when JWKS configured
  - Expired token returns 401
  - Wrong issuer returns 401
  - Malformed token returns 401
  - JWKS cache refresh
  - No JWKS fallback (HMAC-only mode)
"""

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.config.settings import settings
from app.security import jwks_verifier


def _make_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "rsa-test-kid"
    return private_key, jwk


def _restore_settings(**originals):
    for k, v in originals.items():
        setattr(settings, k, v)


class TestRS256Token:
    def test_rs256_valid_token_accepted(self, monkeypatch):
        originals = {"SUPABASE_URL": settings.SUPABASE_URL, "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET}
        settings.SUPABASE_URL = "https://example.supabase.co"
        settings.SUPABASE_JWT_SECRET = "test-secret"

        private_key, jwk = _make_rsa_keypair()
        payload = {
            "sub": "user-rsa",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "rsa-test-kid"})
        monkeypatch.setattr(jwks_verifier, "_fetch_jwks", lambda: {"rsa-test-kid": jwk})
        jwks_verifier._JWKS_CACHE["keys"] = {}
        jwks_verifier._JWKS_CACHE["fetched_at"] = 0.0

        decoded = jwks_verifier.verify_jwt(token)
        assert decoded["sub"] == "user-rsa"
        _restore_settings(**originals)


class TestHS256Rejection:
    def test_hs256_rejected_when_jwks_configured(self, monkeypatch):
        originals = {"SUPABASE_URL": settings.SUPABASE_URL, "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET}
        settings.SUPABASE_URL = "https://example.supabase.co"
        settings.SUPABASE_JWT_SECRET = "test-secret"

        payload = {
            "sub": "user-hs",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

        jwks_verifier._JWKS_CACHE["keys"] = {}
        jwks_verifier._JWKS_CACHE["fetched_at"] = 0.0

        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt(token)
        assert excinfo.value.status_code == 401
        _restore_settings(**originals)


class TestExpiredToken:
    def test_expired_token_returns_401(self):
        originals = {"SUPABASE_URL": settings.SUPABASE_URL, "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET}
        settings.SUPABASE_URL = "https://expired-test.supabase.co"
        settings.SUPABASE_JWT_SECRET = "test-secret-for-expired-jwt-test"

        private_key, jwk = _make_rsa_keypair()
        payload = {
            "sub": "user-expired",
            "aud": "authenticated",
            "iss": "https://expired-test.supabase.co/auth/v1",
            "exp": int(time.time()) - 3600,
        }
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "rsa-test-kid"})
        jwks_verifier._JWKS_CACHE["keys"] = {"rsa-test-kid": jwk}
        jwks_verifier._JWKS_CACHE["fetched_at"] = time.time()

        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt(token)
        assert excinfo.value.status_code == 401
        assert "expired" in excinfo.value.detail.lower()
        _restore_settings(**originals)


class TestWrongIssuer:
    def test_wrong_issuer_returns_401(self, monkeypatch):
        originals = {"SUPABASE_URL": settings.SUPABASE_URL, "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET}
        settings.SUPABASE_URL = "https://real.supabase.co"
        settings.SUPABASE_JWT_SECRET = "test-secret"

        private_key, jwk = _make_rsa_keypair()
        payload = {
            "sub": "user-wrong-iss",
            "aud": "authenticated",
            "iss": "https://attacker.com/auth/v1",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "rsa-test-kid"})
        monkeypatch.setattr(jwks_verifier, "_fetch_jwks", lambda: {"rsa-test-kid": jwk})
        jwks_verifier._JWKS_CACHE["keys"] = {"rsa-test-kid": jwk}
        jwks_verifier._JWKS_CACHE["fetched_at"] = time.time()

        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt(token)
        assert excinfo.value.status_code == 401
        _restore_settings(**originals)


class TestMalformedToken:
    def test_malformed_token_returns_401(self):
        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt("not-a-valid-jwt-token")
        assert excinfo.value.status_code == 401

    def test_empty_token_returns_401(self):
        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt("")
        assert excinfo.value.status_code == 401

    def test_none_token_returns_401(self):
        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt(None)
        assert excinfo.value.status_code == 401


class TestJwksCacheRefresh:
    def test_jwks_cache_refresh_on_missing_key(self, monkeypatch):
        originals = {"SUPABASE_URL": settings.SUPABASE_URL, "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET}
        settings.SUPABASE_URL = "https://example.supabase.co"
        settings.SUPABASE_JWT_SECRET = "test-secret"

        private_key, jwk = _make_rsa_keypair()
        payload = {
            "sub": "user-cache",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "rsa-test-kid"})

        call_count = 0

        def fetch_jwks_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {}
            return {"rsa-test-kid": jwk}

        monkeypatch.setattr(jwks_verifier, "_fetch_jwks", fetch_jwks_once)
        jwks_verifier._JWKS_CACHE["keys"] = {}
        jwks_verifier._JWKS_CACHE["fetched_at"] = 0.0

        decoded = jwks_verifier.verify_jwt(token)
        assert decoded["sub"] == "user-cache"
        assert call_count == 2
        _restore_settings(**originals)


class TestNoJwksFallback:
    def test_no_jwks_fallback_hmac_only_mode(self):
        originals = {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET,
        }
        settings.SUPABASE_URL = None
        settings.SUPABASE_JWT_SECRET = "hmac-only-secret"

        payload = {
            "sub": "user-hmac",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

        decoded = jwks_verifier.verify_jwt(token)
        assert decoded["sub"] == "user-hmac"
        _restore_settings(**originals)

    def test_no_jwks_fallback_rs256_fails(self, monkeypatch):
        originals = {
            "SUPABASE_URL": settings.SUPABASE_URL,
            "SUPABASE_JWT_SECRET": settings.SUPABASE_JWT_SECRET,
        }
        settings.SUPABASE_URL = None
        settings.SUPABASE_JWT_SECRET = "hmac-only-secret"

        private_key, _ = _make_rsa_keypair()
        payload = {
            "sub": "user-rsa-fail",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "rsa-test-kid"})

        monkeypatch.setattr(jwks_verifier, "_fetch_jwks", lambda: {})
        jwks_verifier._JWKS_CACHE["keys"] = {}
        jwks_verifier._JWKS_CACHE["fetched_at"] = 0.0

        with pytest.raises(HTTPException) as excinfo:
            jwks_verifier.verify_jwt(token)
        assert excinfo.value.status_code == 401
        _restore_settings(**originals)
