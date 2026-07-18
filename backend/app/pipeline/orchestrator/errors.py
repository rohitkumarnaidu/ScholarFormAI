# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Stage-specific error types for the pipeline orchestrator."""


class StageError(Exception):
    """Base error for pipeline stage failures."""

    def __init__(self, message, stage=None, document_id=None, recoverable=True):
        self.stage = stage
        self.document_id = document_id
        self.recoverable = recoverable
        super().__init__(message)


class StageTimeoutError(StageError):
    """Raised when a pipeline stage exceeds its timeout."""

    def __init__(self, message, stage=None, document_id=None, timeout_sec=None):
        self.timeout_sec = timeout_sec
        super().__init__(message, stage=stage, document_id=document_id, recoverable=True)


class StageValidationError(StageError):
    """Raised when a pipeline stage produces invalid output."""

    def __init__(self, message, stage=None, document_id=None, errors=None):
        self.errors = errors or []
        super().__init__(message, stage=stage, document_id=document_id, recoverable=False)


class StageResourceError(StageError):
    """Raised when a required external resource is unavailable."""

    def __init__(self, message, stage=None, document_id=None, resource=None):
        self.resource = resource
        super().__init__(message, stage=stage, document_id=document_id, recoverable=True)
