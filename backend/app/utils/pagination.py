# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from fastapi import HTTPException


def encode_cursor(value: str) -> str:
    """Base64-encode a cursor value for safe transport in URLs."""
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("utf-8").rstrip("=")


def decode_cursor(cursor: str) -> str:
    """Base64-decode a cursor value. Raises HTTP 422 on invalid input."""
    try:
        padded = cursor + "=" * (4 - len(cursor) % 4) if len(cursor) % 4 else cursor
        return base64.urlsafe_b64decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid cursor: {exc}")


def _normalize_cursor_value(value: Any) -> str:
    """Convert a cursor column value to its string representation."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def build_cursor_query(query, params, cursor_column: str = "created_at"):
    """Apply cursor-based pagination filters to a Supabase query builder.

    Args:
        query: A supabase-py query builder (e.g. ``client.table("documents").select("*")``).
        params: A ``PaginationParams`` instance with cursor, limit, order_by, order_dir.
        cursor_column: The column used as the cursor (default ``"created_at"``).

    Returns:
        The query builder with ``.gt()``/``.lt()``, ``.order()``, and ``.limit()`` applied.
    """
    if params.cursor:
        try:
            cursor_value = decode_cursor(params.cursor)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid cursor: {exc}")

        if params.order_dir == "desc":
            query = query.lt(cursor_column, cursor_value)
        else:
            query = query.gt(cursor_column, cursor_value)

    query = query.order(cursor_column, desc=(params.order_dir == "desc"))
    query = query.limit(params.limit + 1)
    return query


def build_cursor_response(
    items: list[dict[str, Any]],
    params,
    cursor_column: str = "created_at",
):
    """Wrap a list of items into a ``CursorPage``, computing the next cursor.

    Args:
        items: Raw items from the database query (may include one extra beyond ``params.limit``).
        params: The ``PaginationParams`` that was used for the query.
        cursor_column: The column whose value becomes the next cursor.

    Returns:
        A dict with keys ``items``, ``next_cursor``, ``has_more``, ``total``.
    """
    has_more = len(items) > params.limit
    if has_more:
        items = items[: params.limit]

    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        raw = last_item.get(cursor_column)
        if raw is not None:
            next_cursor = encode_cursor(_normalize_cursor_value(raw))

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total": None,
    }
