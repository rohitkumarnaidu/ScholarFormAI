# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import HTTPException, status

from app.config.settings import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60 * 60
_JWKS_LOCK = threading.Lock()
_JWKS_CACHE: Dict[str, Any] = {"keys": {}, "fetched_at": 0.0}


class _RetryableJWTError(Exception):
    pass


def _resolve_jwks_url() -> Optional[str]:
    if settings.SUPABASE_JWKS_URL:
        explicit = settings.SUPABASE_JWKS_URL.rstrip("/")
        if explicit.endswith("/auth/v1/keys"):
            base = explicit[: -len("/auth/v1/keys")]
            return f"{base}/auth/v1/.well-known/jwks.json"
        return explicit
    if settings.SUPABASE_URL:
        base = settings.SUPABASE_URL.rstrip("/")
        return f"{base}/auth/v1/.well-known/jwks.json"
    return None


def _fetch_jwks() -> Dict[str, dict]:
    url = _resolve_jwks_url()
    if not url:
        return {}
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        payload = response.json()
        keys = {key.get("kid"): key for key in payload.get("keys", []) if key.get("kid")}
        with _JWKS_LOCK:
            _JWKS_CACHE["keys"] = keys
            _JWKS_CACHE["fetched_at"] = time.time()
        return keys
    except Exception as exc:
        logger.warning("JWKS fetch failed: %s", exc)
        return {}


def _get_cached_keys(*, refresh: bool = False) -> Dict[str, dict]:
    with _JWKS_LOCK:
        cached = dict(_JWKS_CACHE.get("keys") or {})
        fetched_at = float(_JWKS_CACHE.get("fetched_at") or 0.0)
    if not refresh and cached and (time.time() - fetched_at) < _CACHE_TTL_SECONDS:
        return cached
    return _fetch_jwks()


def _decode_with_secret(token: str, *, expected_issuer: Optional[str]) -> dict:
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT secret not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=[settings.ALGORITHM],
        audience="authenticated",
        issuer=expected_issuer,
        options={
            "verify_exp": True,
            "verify_iss": True if expected_issuer else False,
        },
    )


def _public_key_from_jwk(jwk: dict):
    kty = (jwk.get("kty") or "").upper()
    if kty == "RSA":
        return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    if kty == "EC":
        return jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))
    if kty == "OKP":
        return jwt.algorithms.OKPAlgorithm.from_jwk(json.dumps(jwk))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unsupported JWT key type",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_with_jwks(token: str, *, expected_issuer: Optional[str], refresh: bool = False) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg") or "RS256"
    if not kid:
        raise _RetryableJWTError("Missing kid in JWT header")

    keys = _get_cached_keys(refresh=refresh)
    jwk = keys.get(kid)
    if not jwk:
        raise _RetryableJWTError("Key not found in JWKS cache")

    public_key = _public_key_from_jwk(jwk)
    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=[alg],
            audience="authenticated",
            issuer=expected_issuer,
            options={
                "verify_exp": True,
                "verify_iss": True if expected_issuer else False,
            },
        )
    except (jwt.InvalidSignatureError, jwt.InvalidKeyError, jwt.DecodeError) as exc:
        raise _RetryableJWTError(str(exc))


def verify_jwt(token: str) -> dict:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected_issuer = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1" if settings.SUPABASE_URL else None
    try:
        header = jwt.get_unverified_header(token)
        alg = (header.get("alg") or "").upper()
        if alg.startswith("HS"):
            return _decode_with_secret(token, expected_issuer=expected_issuer)
        return _decode_with_jwks(token, expected_issuer=expected_issuer, refresh=False)
    except _RetryableJWTError:
        try:
            return _decode_with_jwks(token, expected_issuer=expected_issuer, refresh=True)
        except _RetryableJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
