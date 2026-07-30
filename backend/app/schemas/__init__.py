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
    SignupRequest,
    LoginRequest,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
    AuthTokenResponse,
    MessageResponse,
    OTPVerifyResponse,
)

# ── Document ──────────────────────────────────────────────────────────────────
from app.schemas.document import (
    ExportFormat,
    DocumentStatus,
    PageSize,
    TemplateChoice,
    FormattingOptions,
    DocumentUploadResponse,
    PhaseStatus,
    DocumentStatusResponse,
    DocumentBase,
    Document,
    DocumentListItem,
    DocumentListResponse,
    DocumentMetaSummary,
    DocumentPreviewResponse,
    CompareOriginal,
    CompareFormatted,
    DocumentCompareResponse,
)

# ── User ──────────────────────────────────────────────────────────────────────
from app.schemas.user import (
    UserBase,
    User,
    UserProfile,
    UserUpdateRequest,
)

# ── Update Management (v1) ───────────────────────────────────────────────────
from app.schemas.update import (
    UpdateCheckRequest,
    UpdateInfoSchema,
    UpdateCheckResponse,
    UpdateDownloadRequest,
    UpdateDownloadResponse,
    UpdateInstallRequest,
    UpdateInstallResponse,
    UpdateRollbackRequest,
    UpdateRollbackResponse,
    UpdateVerifyRequest,
    UpdateVerifyResponse,
    UpdateSettingsSchema,
    UpdateSettingsUpdateSchema,
    ReleaseNotesSchema,
    ChannelSchema,
    VersionInfoSchema,
    UpdateHistoryItemSchema,
    UpdateHistoryResponse,
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
    # Update v1
    "UpdateCheckRequest",
    "UpdateInfoSchema",
    "UpdateCheckResponse",
    "UpdateDownloadRequest",
    "UpdateDownloadResponse",
    "UpdateInstallRequest",
    "UpdateInstallResponse",
    "UpdateRollbackRequest",
    "UpdateRollbackResponse",
    "UpdateVerifyRequest",
    "UpdateVerifyResponse",
    "UpdateSettingsSchema",
    "UpdateSettingsUpdateSchema",
    "ReleaseNotesSchema",
    "ChannelSchema",
    "VersionInfoSchema",
    "UpdateHistoryItemSchema",
    "UpdateHistoryResponse",
]

