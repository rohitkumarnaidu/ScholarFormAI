# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Validation pipeline - Check document integrity."""

from .validator_v3 import DocumentValidator, ValidationResult, validate_document

__all__ = ["DocumentValidator", "ValidationResult", "validate_document"]
