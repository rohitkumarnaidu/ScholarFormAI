# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.config.settings import settings
from app.security import jwks_verifier


def _make_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "test-kid"
    return private_key, jwk


def _make_ec_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(public_key))
    jwk["kid"] = "ec-test-kid"
    return private_key, jwk


@pytest.mark.unit
def test_jwks_verify_and_refresh(monkeypatch):
    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://example.supabase.co"
    private_key, correct_jwk = _make_rsa_keypair()
    _, wrong_jwk = _make_rsa_keypair()
    wrong_jwk["kid"] = "test-kid"

    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})

    jwks_verifier._JWKS_CACHE["keys"] = {"test-kid": wrong_jwk}
    jwks_verifier._JWKS_CACHE["fetched_at"] = time.time()

    monkeypatch.setattr(jwks_verifier, "_fetch_jwks", lambda: {"test-kid": correct_jwk})

    decoded = jwks_verifier.verify_jwt(token)
    assert decoded["sub"] == "user-123"
    settings.SUPABASE_URL = original_url


@pytest.mark.unit
def test_jwks_verify_es256_ec_key():
    original_url = settings.SUPABASE_URL
    settings.SUPABASE_URL = "https://example.supabase.co"
    private_key, ec_jwk = _make_ec_keypair()

    payload = {
        "sub": "user-ec-123",
        "aud": "authenticated",
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "ec-test-kid"})

    jwks_verifier._JWKS_CACHE["keys"] = {"ec-test-kid": ec_jwk}
    jwks_verifier._JWKS_CACHE["fetched_at"] = time.time()

    decoded = jwks_verifier.verify_jwt(token)
    assert decoded["sub"] == "user-ec-123"
    settings.SUPABASE_URL = original_url
