# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
CSRF protection middleware.

Generates and validates CSRF tokens for state-changing requests (POST/PUT/PATCH/DELETE).
Cookie-based token storage with validation.
Exempts API routes that use Bearer token auth.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings

logger = logging.getLogger(__name__)

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_TOKEN_EXPIRY_SECONDS = 3600

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

EXEMPT_PATH_PREFIXES = (
    "/api/v1/",
    "/api/preview",
    "/health",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _get_csrf_secret() -> bytes:
    secret = getattr(settings, "SIGNED_URL_SECRET", None) or getattr(settings, "SUPABASE_JWT_SECRET", None)
    if secret:
        return secret.encode("utf-8")
    fallback = "csrf-fallback-secret-do-not-use-in-production"
    logger.warning(
        "CSRF middleware using fallback secret. "
        "Set SIGNED_URL_SECRET or SUPABASE_JWT_SECRET for production."
    )
    return fallback.encode("utf-8")


def generate_csrf_token() -> str:
    """Generate a CSRF token: timestamped HMAC of a random value."""
    raw = secrets.token_hex(32)
    timestamp = str(int(time.time()))
    message = f"{timestamp}:{raw}"
    signature = hmac.new(
        _get_csrf_secret(),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{message}:{signature}"


def validate_csrf_token(token: str) -> bool:
    """Validate a CSRF token: check signature and expiry."""
    if not token:
        return False

    parts = token.split(":")
    if len(parts) != 3:
        return False

    timestamp_str, raw, provided_signature = parts

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        return False

    if time.time() - timestamp > CSRF_TOKEN_EXPIRY_SECONDS:
        return False

    message = f"{timestamp_str}:{raw}"
    expected_signature = hmac.new(
        _get_csrf_secret(),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(provided_signature, expected_signature)


def _is_exempt_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES)


def _has_bearer_auth(request: Request) -> bool:
    auth_header = request.headers.get("authorization", "")
    return auth_header.lower().startswith("bearer ")


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.

    - On GET/HEAD/OPTIONS: sets a CSRF token cookie if not already present.
    - On POST/PUT/PATCH/DELETE: validates the CSRF token from the request header
      against the cookie value, unless the path is exempt or Bearer auth is present.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()

        if method in SAFE_METHODS:
            response = await call_next(request)
            if CSRF_COOKIE_NAME not in request.cookies:
                token = generate_csrf_token()
                response.set_cookie(
                    key=CSRF_COOKIE_NAME,
                    value=token,
                    httponly=False,
                    samesite="lax",
                    secure=not getattr(settings, "DEBUG", False),
                    max_age=CSRF_TOKEN_EXPIRY_SECONDS,
                )
            return response

        if _is_exempt_path(request.url.path):
            return await call_next(request)

        if _has_bearer_auth(request):
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            return Response(
                status_code=403,
                content='{"error": "CSRF token missing. Include X-CSRF-Token header with the value from the csrf_token cookie."}',
                media_type="application/json",
                headers={"WWW-Authenticate": "CSRF-Token-Required"},
            )

        if not validate_csrf_token(header_token):
            logger.warning("CSRF validation failed for %s %s", method, request.url.path)
            return Response(
                status_code=403,
                content='{"error": "CSRF token invalid or expired."}',
                media_type="application/json",
            )

        return await call_next(request)
