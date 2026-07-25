# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


def should_enable_llm_classification() -> bool:
    """Check whether LLM-based classification is enabled.

    Controlled by ``LLM_CLASSIFICATION_ENABLED`` in settings.
    Falls back to ``True`` when the setting is absent.
    """
    return bool(getattr(settings, "LLM_CLASSIFICATION_ENABLED", True))
