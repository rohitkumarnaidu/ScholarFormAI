# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class CursorPage[T](BaseModel):
    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = Field(default=None, description="Base64-encoded cursor for the next page")
    has_more: bool = Field(default=False, description="Whether more items exist after this page")
    total: int | None = Field(default=None, description="Total item count, set only when requested")


class PaginationParams(BaseModel):
    cursor: str | None = Field(default=None, description="Base64-encoded cursor from the previous response")
    limit: int = Field(default=50, ge=1, le=100, description="Number of items per page")
    order_by: str = Field(default="created_at", description="Column to order by")
    order_dir: str = Field(default="desc", description="Order direction: asc or desc")
