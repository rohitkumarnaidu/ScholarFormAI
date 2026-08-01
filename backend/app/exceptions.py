# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Custom exception classes for the Automated Manuscript Formatter.

All service-layer code should raise these instead of swallowing errors
or returning None/empty collections on failure.
"""

from __future__ import annotations

from fastapi import status


class ScholarFormError(Exception):
    """Base exception for all ScholarForm AI domain errors.

    Each subclass carries an ``http_status`` that the global FastAPI exception
    handler uses to build the HTTP response automatically.
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str | None = None) -> None:
        if message:
            super().__init__(message)
        else:
            super().__init__(self.__doc__)


class DatabaseUnavailableError(ScholarFormError):
    """Raised when a database operation fails due to connectivity or server issues."""

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, message: str = "Database is currently unavailable.") -> None:
        super().__init__(message)


class DocumentNotFoundError(ScholarFormError):
    """Raised when a requested document does not exist."""

    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, doc_id: str | None = None) -> None:
        detail = "Document not found" + (f": {doc_id}" if doc_id else ".")
        super().__init__(detail)
        self.doc_id = doc_id


class NotFoundError(ScholarFormError):
    """Raised when a requested resource does not exist."""

    http_status = status.HTTP_404_NOT_FOUND


class AuthenticationError(ScholarFormError):
    """Raised when authentication fails or credentials are invalid."""

    http_status = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message)


class RateLimitExceededError(ScholarFormError):
    """Raised when a rate limit has been exceeded."""

    http_status = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, message: str = "Rate limit exceeded. Please try again later.") -> None:
        super().__init__(message)


class PipelineError(ScholarFormError):
    """Raised when a pipeline processing step fails."""

    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR


class ValidationError(ScholarFormError):
    """Raised when input validation fails."""

    http_status = 422


class FileStorageError(ScholarFormError):
    """Raised when a file storage operation fails."""

    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "File storage operation failed.") -> None:
        super().__init__(message)


class ExternalServiceError(ScholarFormError):
    """Raised when an external service (LLM, GROBID, OCR, etc.) fails."""

    http_status = status.HTTP_502_BAD_GATEWAY

    def __init__(self, service: str | None = None, message: str = "External service call failed.") -> None:
        if service:
            message = f"{service}: {message}"
        super().__init__(message)
        self.service = service
