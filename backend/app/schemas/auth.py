# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Authentication Schemas — Request & Response models for all auth endpoints.

All request models use strict Pydantic v2 validation.
All response models are typed to prevent accidental data leakage.
"""

import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Helpers ───────────────────────────────────────────────────────────────────

_PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#])[A-Za-z\d@$!%*?&_\-#]{8,}$")


def _validate_password_strength(password: str) -> str:
    """Enforce: ≥8 chars, upper, lower, digit, special character."""
    if not _PASSWORD_PATTERN.match(password):
        raise ValueError(
            "Password must be at least 8 characters and contain an uppercase letter, "
            "a lowercase letter, a digit, and a special character (@$!%*?&_-#)."
        )
    return password


# ── Request Schemas ───────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Request body for POST /api/v1/auth/signup."""

    full_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="User's full display name.",
        examples=["Jane Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address used as the login identifier.",
    )
    institution: Optional[str] = Field(
        None,
        max_length=200,
        description="University or organisation name (optional).",
        examples=["MIT"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include upper, lower, digit, special).",
    )
    terms_accepted: bool = Field(
        ...,
        description="Must be true — user has accepted the Terms & Conditions.",
    )

    @field_validator("terms_accepted")
    @classmethod
    def must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Terms and conditions must be accepted.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password.",
    )


class ForgotPasswordRequest(BaseModel):
    """Request body for POST /api/v1/auth/forgot-password."""

    email: EmailStr = Field(
        ...,
        description="Email address to send the password-reset OTP to.",
    )


class VerifyOTPRequest(BaseModel):
    """Request body for POST /api/v1/auth/verify-otp (Step 2 of reset flow)."""

    email: EmailStr = Field(..., description="Email address that received the OTP.")
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit numeric OTP sent via email.",
    )


class ResetPasswordRequest(BaseModel):
    """Request body for POST /api/v1/auth/reset-password (Step 3 of reset flow)."""

    email: EmailStr = Field(..., description="Email address of the account.")
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP received via email.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (same strength requirements as signup).",
    )

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# ── Response Schemas ──────────────────────────────────────────────────────────


class AuthTokenResponse(BaseModel):
    """Returned after a successful login."""

    access_token: str = Field(..., description="Supabase JWT access token.")
    token_type: str = Field(default="bearer", description="OAuth2 token type.")
    expires_in: Optional[int] = Field(None, description="Token lifetime in seconds (from Supabase).")
    user_id: Optional[str] = Field(None, description="Authenticated user UUID.")
    email: Optional[str] = Field(None, description="Authenticated user email.")


class MessageResponse(BaseModel):
    """Generic success/info response."""

    message: str = Field(..., description="Human-readable status message.")
    success: bool = Field(default=True)


class OTPVerifyResponse(BaseModel):
    """Returned after OTP verification."""

    verified: bool = Field(..., description="Whether the OTP was valid.")
    message: str = Field(..., description="Human-readable result.")
