# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Text Normalization Utilities

Helper functions for normalizing text content without changing meaning.
"""

import re
import unicodedata

# Unicode normalization mappings
# These are common Unicode variants that should be normalized to ASCII equivalents

# Quotation marks
QUOTE_MAPPING: dict[str, str] = {
    "\u2018": "'",  # Left single quotation mark
    "\u2019": "'",  # Right single quotation mark
    "\u201a": "'",  # Single low-9 quotation mark
    "\u201b": "'",  # Single high-reversed-9 quotation mark
    "\u201c": '"',  # Left double quotation mark
    "\u201d": '"',  # Right double quotation mark
    "\u201e": '"',  # Double low-9 quotation mark
    "\u201f": '"',  # Double high-reversed-9 quotation mark
    "\u2039": "'",  # Single left-pointing angle quotation mark
    "\u203a": "'",  # Single right-pointing angle quotation mark
    "\u00ab": '"',  # Left-pointing double angle quotation mark
    "\u00bb": '"',  # Right-pointing double angle quotation mark
}

# Dashes and hyphens
DASH_MAPPING: dict[str, str] = {
    "\u2010": "-",  # Hyphen
    "\u2011": "-",  # Non-breaking hyphen
    "\u2012": "-",  # Figure dash
    "\u2013": "-",  # En dash
    "\u2014": "--",  # Em dash (replace with double hyphen)
    "\u2015": "--",  # Horizontal bar
    "\u2212": "-",  # Minus sign
}

# Spaces
SPACE_MAPPING: dict[str, str] = {
    "\u00a0": " ",  # Non-breaking space
    "\u2002": " ",  # En space
    "\u2003": " ",  # Em space
    "\u2004": " ",  # Three-per-em space
    "\u2005": " ",  # Four-per-em space
    "\u2006": " ",  # Six-per-em space
    "\u2007": " ",  # Figure space
    "\u2008": " ",  # Punctuation space
    "\u2009": " ",  # Thin space
    "\u200a": " ",  # Hair space
    "\u202f": " ",  # Narrow no-break space
    "\u205f": " ",  # Medium mathematical space
}

# Bullet and list characters
BULLET_MAPPING: dict[str, str] = {
    "\u2022": "•",  # Bullet (keep as is, it's common)
    "\u2023": "•",  # Triangular bullet
    "\u2043": "•",  # Hyphen bullet
    "\u25aa": "•",  # Black small square
    "\u25ab": "•",  # White small square
    "\u25cf": "•",  # Black circle
    "\u25e6": "•",  # White bullet
    "\u2219": "•",  # Bullet operator
    "\u00b7": "•",  # Middle dot
}

# Combined mapping
UNICODE_MAPPING: dict[str, str] = {
    **QUOTE_MAPPING,
    **DASH_MAPPING,
    **SPACE_MAPPING,
    **BULLET_MAPPING,
}


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters to their ASCII equivalents or standard forms.

    This replaces fancy quotes, dashes, spaces, and bullets with standard ASCII
    or common Unicode equivalents.

    Args:
        text: Input text with potential Unicode variants

    Returns:
        Normalized text with standard characters

    Example:
        >>> normalize_unicode("It's a "quote" — with dashes")
        "It's a \"quote\" -- with dashes"
    """
    # Apply character mappings
    for unicode_char, replacement in UNICODE_MAPPING.items():
        text = text.replace(unicode_char, replacement)

    return text


def normalize_whitespace(text: str, collapse_newlines: bool = False) -> str:
    """
    Normalize whitespace in text.

    - Replaces tabs with spaces
    - Collapses multiple spaces into one
    - Trims leading/trailing whitespace
    - Optionally collapses multiple newlines

    Args:
        text: Input text
        collapse_newlines: If True, collapse multiple newlines to max 2

    Returns:
        Text with normalized whitespace

    Example:
        >>> normalize_whitespace("Hello    world\\t\\n  test")
        "Hello world\\n test"
    """
    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces (but preserve newlines)
    # Split by newlines, process each line, then rejoin
    lines = text.split("\n")
    normalized_lines = []

    for line in lines:
        # Collapse multiple spaces within the line
        line = re.sub(r" +", " ", line)
        # Trim leading/trailing spaces from each line
        line = line.strip()
        normalized_lines.append(line)

    # Rejoin with newlines
    text = "\n".join(normalized_lines)

    # Collapse multiple newlines if requested
    if collapse_newlines:
        # Replace 3+ newlines with 2 newlines (max one blank line)
        text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def normalize_list_markers(text: str) -> str:
    """
    Normalize list markers/bullets to standard format.

    Handles edge case where bullet comes before list text.

    Args:
        text: Input text potentially starting with bullet

    Returns:
        Text with normalized bullet (if present)
    """
    # Trim the text first
    text = text.strip()

    # Check if starts with a bullet character followed by space
    if text and text[0] in BULLET_MAPPING:
        # Replace the bullet with standard bullet
        text = "• " + text[1:].lstrip()

    return text


def clean_metadata_field(field: str) -> str:
    """
    Clean a metadata field (title, author, keyword, etc.).

    - Normalize Unicode
    - Normalize whitespace
    - Trim leading/trailing whitespace
    - Remove control characters

    Args:
        field: Metadata field value

    Returns:
        Cleaned field value
    """
    if not field:
        return field

    # Normalize Unicode
    field = normalize_unicode(field)

    # Normalize whitespace (don't preserve newlines in metadata)
    field = field.replace("\n", " ").replace("\r", " ")
    field = re.sub(r" +", " ", field)

    # Trim
    field = field.strip()

    # Remove control characters (except tab and newline, which we already handled)
    field = "".join(char for char in field if not unicodedata.category(char).startswith("C"))

    return field


def normalize_block_text(text: str, is_empty_ok: bool = True) -> str:
    """
    Normalize text content in a block.

    This is the main normalization function for block text.

    Args:
        text: Input block text
        is_empty_ok: If True, allow empty strings; if False, return original on empty

    Returns:
        Normalized text
    """
    if text is None:
        return ""

    original_text = text

    # Step 1: Normalize Unicode characters
    text = normalize_unicode(text)

    # Step 2: Normalize whitespace (preserve paragraph breaks)
    text = normalize_whitespace(text, collapse_newlines=True)

    # Step 3: If the text became empty and empty is not okay, return original
    if not is_empty_ok and not text.strip():
        return original_text

    return text


def normalize_table_cell_text(text: str) -> str:
    """
    Normalize text in a table cell.

    More aggressive than block normalization:
    - Removes all newlines (cells should be single line)
    - Collapses all whitespace
    - Trims edges

    Args:
        text: Table cell text

    Returns:
        Normalized cell text
    """
    if not text:
        return ""

    # Normalize Unicode
    text = normalize_unicode(text)

    # Replace newlines with spaces
    text = text.replace("\n", " ").replace("\r", " ")

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Trim
    text = text.strip()

    return text
