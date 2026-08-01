# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
app/schemas/__init__.py

Central import hub for all Pydantic schemas.

Primary schemas (v1):
  from app.schemas import SignupRequest, Document, User, ...

All schemas are available from this single import point.
"""

# ── Auth ──────────────────────────────────────────────────────────────────────
from app.schemas.auth import (
    AuthTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OTPVerifyResponse,
    ResetPasswordRequest,
    SignupRequest,
    VerifyOTPRequest,
)

# ── Document ──────────────────────────────────────────────────────────────────
from app.schemas.document import (
    CompareFormatted,
    CompareOriginal,
    Document,
    DocumentBase,
    DocumentCompareResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentMetaSummary,
    DocumentPreviewResponse,
    DocumentStatus,
    DocumentStatusResponse,
    DocumentUploadResponse,
    ExportFormat,
    FormattingOptions,
    PageSize,
    PhaseStatus,
    TemplateChoice,
)

# ── User ──────────────────────────────────────────────────────────────────────
from app.schemas.user import (
    User,
    UserBase,
    UserProfile,
    UserUpdateRequest,
)

__all__ = [
    # Auth v1
    # Document v1
    "SignupRequest",
    "LoginRequest",
    "ForgotPasswordRequest",
    "VerifyOTPRequest",
    "ResetPasswordRequest",
    "AuthTokenResponse",
    "MessageResponse",
    "OTPVerifyResponse",
    "ExportFormat",
    "DocumentStatus",
    "PageSize",
    "TemplateChoice",
    "FormattingOptions",
    "DocumentUploadResponse",
    "PhaseStatus",
    "DocumentStatusResponse",
    "DocumentBase",
    "Document",
    "DocumentListItem",
    "DocumentListResponse",
    "DocumentMetaSummary",
    "DocumentPreviewResponse",
    "CompareOriginal",
    "CompareFormatted",
    "DocumentCompareResponse",
    "UserBase",
    "User",
    "UserProfile",
    "UserUpdateRequest",
]
