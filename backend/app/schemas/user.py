# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
User Schemas — Pydantic models for the authenticated user object.

Used by:
- `get_current_user` dependency (JWT → User)
- `/api/v1/auth/me` response
- All document endpoints that scope by user_id
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields (safe to expose in API responses)."""

    email: Optional[EmailStr] = Field(None, description="User's email address.")
    name: Optional[str] = Field(None, description="User's display name.")
    institution: Optional[str] = Field(
        None, description="University or organisation the user belongs to."
    )
    role: str = Field(
        "authenticated",
        description="Supabase role. Typically 'authenticated' or 'service_role'.",
    )


class User(UserBase):
    """Full user record — returned from JWT decode and /api/v1/auth/me."""

    id: str = Field(..., description="Supabase user UUID.")
    app_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Supabase app_metadata payload (used for RBAC).",
    )

    model_config = ConfigDict(from_attributes=True)


class UserProfile(User):
    """Extended user profile with optional metadata fields."""

    avatar_url: Optional[str] = Field(None, description="URL to the user's avatar image.")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp (UTC).")
    last_sign_in_at: Optional[datetime] = Field(
        None, description="Last successful login timestamp (UTC)."
    )
    is_verified: bool = Field(
        False, description="Whether the user's email has been verified."
    )
    document_count: Optional[int] = Field(
        None, description="Total number of documents processed by this user."
    )

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Request body for updating user profile fields."""

    name: Optional[str] = Field(None, max_length=120, description="New display name.")
    institution: Optional[str] = Field(
        None, max_length=200, description="New institution name."
    )
    avatar_url: Optional[str] = Field(None, description="New avatar URL.")
