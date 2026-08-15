# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import re
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Basic heuristics for detecting jailbreak attempts and prompt injections
_SUSPICIOUS_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+)?(instructions|directions)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous\s+)?(instructions|directions)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous\s+)?(instructions|directions)", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"act\s+as\s+a", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"Developer\s+Mode", re.IGNORECASE),
    re.compile(r"simulated\s+environment", re.IGNORECASE),
]

def check_prompt_injection(user_input: str) -> None:
    """
    Validates user input against common prompt injection and jailbreak patterns.
    Raises an HTTPException if a violation is detected.
    """
    if not user_input:
        return

    # 1. Length bounds checking
    if len(user_input) > 100000:
        logger.warning("Prompt injection filter triggered: Input too large.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input exceeds maximum allowed length for AI processing."
        )

    # 2. Heuristics matching
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(user_input):
            logger.warning(f"Prompt injection filter triggered: Matched pattern {pattern.pattern}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your input triggered the AI security filter and cannot be processed."
            )

def safe_prompt(user_input: str) -> str:
    """
    Checks for prompt injection and returns the string if safe.
    """
    check_prompt_injection(user_input)
    return user_input
