# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Reference Field Normalizer - Cleans parsed reference fields.
"""

import re
from typing import List


def clean_author_name(name: str) -> str:
    """
    Clean author name.
    e.g. "Smith, J." -> "Smith, J."
    e.g. "J. Smith" -> "J. Smith"
    Removes extra spaces, trailing periods if strictly separator.
    """
    cleaned = name.strip()
    # Remove surrounding quotes if somehow present
    cleaned = cleaned.strip("\"'")
    return cleaned


def clean_title(title: str) -> str:
    """
    Clean title text.
    Removes surrounding quotes typical in IEEE ("Title").
    """
    cleaned = title.strip()
    # Remove common wrapping quotes for titles
    if (
        (cleaned.startswith('"') and cleaned.endswith('"'))
        or (cleaned.startswith("'") and cleaned.endswith("'"))
        or (cleaned.startswith("“") and cleaned.endswith("”"))
    ):
        cleaned = cleaned[1:-1]

    # Remove trailing comma/period inside title if it was part of citation style
    cleaned = cleaned.strip(".,;")
    return cleaned.strip()


def normalize_page_range(pages: str) -> str:
    """
    Normalize page range numbers.
    e.g. "pp. 123-145" -> "123-145"
    """
    if not pages:
        return ""

    # Remove "pp.", "p." prefix
    cleaned = re.sub(r"^p{1,2}\.?\s*", "", pages.strip(), flags=re.IGNORECASE)
    return cleaned
