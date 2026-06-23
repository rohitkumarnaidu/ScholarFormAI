# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Custom exception classes for the Automated Manuscript Formatter.

All service-layer code should raise these instead of swallowing errors
or returning None/empty collections on failure.
"""
from __future__ import annotations


class DatabaseUnavailableError(Exception):
    """Raised when a database operation fails due to connectivity or server issues."""

    def __init__(self, message: str = "Database is currently unavailable.") -> None:
        super().__init__(message)


class DocumentNotFoundError(Exception):
    """Raised when a requested document does not exist."""

    def __init__(self, doc_id: str | None = None) -> None:
        detail = f"Document not found" + (f": {doc_id}" if doc_id else ".")
        super().__init__(detail)
        self.doc_id = doc_id


class AuthenticationError(Exception):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Raised when a rate limit has been exceeded."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later.") -> None:
        super().__init__(message)


class FileStorageError(Exception):
    """Raised when a file storage operation fails."""

    def __init__(self, message: str = "File storage operation failed.") -> None:
        super().__init__(message)


class ExternalServiceError(Exception):
    """Raised when an external service (LLM, GROBID, OCR, etc.) fails."""

    def __init__(self, service: str | None = None, message: str = "External service call failed.") -> None:
        if service:
            message = f"{service}: {message}"
        super().__init__(message)
        self.service = service
