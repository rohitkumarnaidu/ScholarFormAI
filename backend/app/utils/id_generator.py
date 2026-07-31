# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
ID Generator - Generate unique identifiers for document elements.

Provides consistent, sequential IDs for blocks, figures, tables, and references.
"""


def generate_block_id(index: int) -> str:
    """
    Generate a unique block ID.

    Args:
        index: Sequential index (0-based)

    Returns:
        Block ID in format 'blk_XXX' (e.g., 'blk_001', 'blk_042')
    """
    return f"blk_{index:03d}"


def generate_figure_id(index: int) -> str:
    """
    Generate a unique figure ID.

    Args:
        index: Sequential index (0-based)

    Returns:
        Figure ID in format 'fig_XXX' (e.g., 'fig_001', 'fig_012')
    """
    return f"fig_{index:03d}"


def generate_table_id(index: int) -> str:
    """
    Generate a unique table ID.

    Args:
        index: Sequential index (0-based)

    Returns:
        Table ID in format 'tbl_XXX' (e.g., 'tbl_001', 'tbl_005')
    """
    return f"tbl_{index:03d}"


def generate_reference_id(index: int) -> str:
    """
    Generate a unique reference ID.

    Args:
        index: Sequential index (0-based)

    Returns:
        Reference ID in format 'ref_XXX' (e.g., 'ref_001', 'ref_023')
    """
    return f"ref_{index:03d}"


def generate_equation_id(index: int) -> str:
    """
    Generate a unique equation ID.

    Args:
        index: Sequential index (0-based)

    Returns:
        Equation ID in format 'eqn_XXX' (e.g., 'eqn_001', 'eqn_021')
    """
    return f"eqn_{index:03d}"


def generate_document_id(prefix: str = "doc") -> str:
    """
    Generate a unique document ID with timestamp.

    Args:
        prefix: Prefix for the ID (default: 'doc')

    Returns:
        Document ID in format 'prefix_timestamp' (e.g., 'doc_20240202_103045')
    """
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"
