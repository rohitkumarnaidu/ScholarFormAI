# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
import logging
import warnings

from fastapi import HTTPException, status

from app.config.settings import settings
from app.security.jwks_verifier import verify_jwt

logger = logging.getLogger(__name__)

_SUPABASE_WARNING_FILTERS = (
    ".*enablePackrat.*",
    ".*escChar.*",
    ".*unquoteResults.*",
    "Using `@model_validator` with mode='after' on a classmethod is deprecated.*",
    "The 'timeout' parameter is deprecated. Please configure it in the http client instead.*",
    "The 'verify' parameter is deprecated. Please configure it in the http client instead.*",
)

# Supabase auth client. If credentials are missing, auth endpoints return 503.
try:
    with warnings.catch_warnings():
        for pattern in _SUPABASE_WARNING_FILTERS:
            warnings.filterwarnings("ignore", message=pattern, category=DeprecationWarning)
        from supabase import Client as SupabaseClient
        from supabase import create_client

    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        with warnings.catch_warnings():
            for pattern in _SUPABASE_WARNING_FILTERS:
                warnings.filterwarnings("ignore", message=pattern, category=DeprecationWarning)
            supabase: SupabaseClient | None = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        logger.info("[OK] Supabase auth client initialized.")
    else:
        supabase = None
        logger.warning(
            "[WARN] SUPABASE_URL or SUPABASE_ANON_KEY not set. "
            "Auth endpoints will return 503 until credentials are configured."
        )
except Exception as _exc:
    supabase = None
    logger.error("[ERROR] Failed to initialize Supabase auth client: %s", _exc)


def _require_supabase():
    """Raise HTTP 503 if the Supabase client is not available."""
    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )
    return supabase


class AuthService:
    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Decodes and verifies the Supabase JWT.
        Validates signature, expiration (exp), audience (aud), and issuer (iss).
        """
        return verify_jwt(token)

    @staticmethod
    def get_user_id_from_payload(payload: dict) -> str:
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user identity (sub)",
            )
        return user_id

    @staticmethod
    async def signup(email: str, password: str, full_name: str, institution: str):
        sb = _require_supabase()
        try:
            response = await asyncio.to_thread(
                lambda: sb.auth.sign_up(
                    {
                        "email": email,
                        "password": password,
                        "options": {
                            "data": {
                                "full_name": full_name,
                                "institution": institution,
                            }
                        },
                    }
                )
            )
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Signup failed for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email may already exist.",
            )

    @staticmethod
    async def login(email: str, password: str):
        sb = _require_supabase()
        try:
            response = await asyncio.to_thread(
                lambda: sb.auth.sign_in_with_password(
                    {
                        "email": email,
                        "password": password,
                    }
                )
            )
            return (
                response.model_dump()
                if hasattr(response, "model_dump")
                else response.dict()
                if hasattr(response, "dict")
                else response
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Login failed for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

    @staticmethod
    async def forgot_password(email: str):
        sb = _require_supabase()
        try:
            response = await asyncio.to_thread(lambda: sb.auth.reset_password_for_email(email))
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Forgot-password failed for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset request failed. Please try again.",
            )

    @staticmethod
    async def reset_password(email: str, otp: str, new_password: str):
        sb = _require_supabase()
        try:
            await asyncio.to_thread(
                lambda: sb.auth.verify_otp(
                    {
                        "email": email,
                        "token": otp,
                        "type": "recovery",
                    }
                )
            )
            response = await asyncio.to_thread(lambda: sb.auth.update_user({"password": new_password}))
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Password reset failed for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset failed. Please try again.",
            )

    @staticmethod
    async def verify_otp(email: str, token: str):
        sb = _require_supabase()
        try:
            response = await asyncio.to_thread(
                lambda: sb.auth.verify_otp(
                    {
                        "email": email,
                        "token": token,
                        "type": "recovery",
                    }
                )
            )
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("OTP verification failed for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification failed. Please try again.",
            )
