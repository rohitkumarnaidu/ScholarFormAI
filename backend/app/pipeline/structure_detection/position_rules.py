# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Position-based Rules - Positional heuristics for structure detection.

This module contains rules based on block positioning and spacing:
- First block detection (likely title)
- Isolated lines (surrounded by blank lines)
- Relative positioning
- Spacing patterns
"""

from typing import List, Dict, Any
from app.models import Block


def is_first_non_empty_block(block: Block, all_blocks: List[Block]) -> bool:
    """
    Check if this is the first non-empty block in the document.

    The first non-empty block is often the title.

    Args:
        block: Block to check
        all_blocks: All blocks in document (in order)

    Returns:
        True if this is the first non-empty block
    """
    for b in all_blocks:
        if b.text.strip():
            return b.block_id == block.block_id
    return False


def is_isolated_line(block: Block, all_blocks: List[Block]) -> bool:
    """
    Check if a block is an isolated line (surrounded by empty blocks).

    Isolated lines are often headings or important structural elements.

    Args:
        block: Block to check
        all_blocks: All blocks in document (in order)

    Returns:
        True if block is isolated (empty blocks before and after)
    """
    # Find this block's position
    try:
        block_idx = next(i for i, b in enumerate(all_blocks) if b.block_id == block.block_id)
    except StopIteration:
        return False

    # Check previous block (if exists)
    has_empty_before = False
    if block_idx > 0:
        prev_block = all_blocks[block_idx - 1]
        has_empty_before = not prev_block.text.strip()
    else:
        has_empty_before = True  # First block counts as having empty before

    # Check next block (if exists)
    has_empty_after = False
    if block_idx < len(all_blocks) - 1:
        next_block = all_blocks[block_idx + 1]
        has_empty_after = not next_block.text.strip()
    else:
        has_empty_after = True  # Last block counts as having empty after

    return has_empty_before and has_empty_after


def count_empty_blocks_before(block: Block, all_blocks: List[Block]) -> int:
    """
    Count consecutive empty blocks immediately before this block.

    More empty lines before a block suggests it starts a new section.

    Args:
        block: Block to check
        all_blocks: All blocks in document

    Returns:
        Number of consecutive empty blocks before this one
    """
    try:
        block_idx = next(i for i, b in enumerate(all_blocks) if b.block_id == block.block_id)
    except StopIteration:
        return 0

    count = 0
    for i in range(block_idx - 1, -1, -1):
        if not all_blocks[i].text.strip():
            count += 1
        else:
            break

    return count


def count_empty_blocks_after(block: Block, all_blocks: List[Block]) -> int:
    """
    Count consecutive empty blocks immediately after this block.

    Args:
        block: Block to check
        all_blocks: All blocks in document

    Returns:
        Number of consecutive empty blocks after this one
    """
    try:
        block_idx = next(i for i, b in enumerate(all_blocks) if b.block_id == block.block_id)
    except StopIteration:
        return 0

    count = 0
    for i in range(block_idx + 1, len(all_blocks)):
        if not all_blocks[i].text.strip():
            count += 1
        else:
            break

    return count


def get_block_position_ratio(block: Block, all_blocks: List[Block]) -> float:
    """
    Get the relative position of block in document (0.0 = start, 1.0 = end).

    Args:
        block: Block to check
        all_blocks: All blocks in document

    Returns:
        Position ratio (0.0 to 1.0)
    """
    if not all_blocks:
        return 0.0

    try:
        block_idx = next(i for i, b in enumerate(all_blocks) if b.block_id == block.block_id)
        return block_idx / max(len(all_blocks) - 1, 1)
    except StopIteration:
        return 0.0


def analyze_position(block: Block, all_blocks: List[Block]) -> Dict[str, Any]:
    """
    Comprehensive positional analysis of a block.

    Args:
        block: Block to analyze
        all_blocks: All blocks in document (in order)

    Returns:
        Dict with positional information
        {
            "is_first": bool,
            "is_isolated": bool,
            "empty_before": int,
            "empty_after": int,
            "position_ratio": float,
            "position_hints": list of strings
        }
    """
    is_first = is_first_non_empty_block(block, all_blocks)
    is_isolated = is_isolated_line(block, all_blocks)
    empty_before = count_empty_blocks_before(block, all_blocks)
    empty_after = count_empty_blocks_after(block, all_blocks)
    position_ratio = get_block_position_ratio(block, all_blocks)

    hints = []

    if is_first:
        hints.append("First non-empty block (likely title)")

    if is_isolated:
        hints.append("Isolated line (surrounded by blank lines)")

    if empty_before >= 2:
        hints.append(f"{empty_before} blank lines before (section break)")

    if empty_after >= 1:
        hints.append(f"{empty_after} blank line(s) after")

    if position_ratio < 0.1:
        hints.append("Near document start")
    elif position_ratio > 0.9:
        hints.append("Near document end")

    return {
        "is_first": is_first,
        "is_isolated": is_isolated,
        "empty_before": empty_before,
        "empty_after": empty_after,
        "position_ratio": position_ratio,
        "position_hints": hints,
    }


def boost_heading_confidence_by_position(base_confidence: float, position_info: Dict[str, Any]) -> float:
    """
    Adjust heading confidence based on positional cues.

    Args:
        base_confidence: Confidence from text/style analysis
        position_info: Output from analyze_position()

    Returns:
        Adjusted confidence (0.0-1.0)
    """
    confidence = base_confidence

    # First block boost (likely title)
    if position_info["is_first"]:
        confidence += 0.2

    # Isolated line boost
    if position_info["is_isolated"]:
        confidence += 0.15

    # Multiple blank lines before (section break)
    if position_info["empty_before"] >= 2:
        confidence += 0.1

    # Cap at 1.0
    return min(confidence, 1.0)
