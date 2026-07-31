# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Signals for human-in-the-loop review."""

    OK = "OK"
    REVIEW = "REVIEW"
    CRITICAL = "CRITICAL"


class ReviewMetadata(BaseModel):
    """Confidence-based review signals."""

    # Use string for type hint to avoid "not defined" error during model initialization
    status: str = "OK"
    flags: List[str] = Field(default_factory=list)
    lowest_confidence: float = 1.0
    reason: Optional[str] = None
