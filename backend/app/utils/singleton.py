# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Shared helpers for lazy singleton initialization and optional dependency loading.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib import import_module
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


def get_or_create(current: Optional[T], factory: Callable[[], T]) -> T:
    """Return existing singleton instance or create a new one."""
    if current is None:
        return factory()
    return current


def get_or_create_safe(
    current: Optional[T],
    factory: Callable[[], T],
    *,
    logger: logging.Logger,
    name: str,
    log_level: str = "error",
) -> Optional[T]:
    """Safe singleton getter that logs and returns None on initialization failure."""
    if current is not None:
        return current
    try:
        return factory()
    except Exception as exc:
        log_method = getattr(logger, log_level, logger.error)
        log_method("%s initialization failed: %s", name, exc)
        return None


def get_or_create_catching(
    current: Optional[T],
    factory: Callable[[], T],
    *,
    exceptions: Tuple[Type[BaseException], ...],
) -> Optional[T]:
    """Return singleton or create it, swallowing only declared exception types."""
    if current is not None:
        return current
    try:
        return factory()
    except exceptions:
        return None


@lru_cache(maxsize=64)
def _load_callable(module_path: str, callable_name: str) -> Callable[[], Any]:
    module = import_module(module_path)
    return getattr(module, callable_name)


def resolve_optional_callable(module_path: str, callable_name: str) -> Any:
    """
    Import a callable dynamically and execute it.
    Returns None when import/call fails.
    """
    try:
        target = _load_callable(module_path, callable_name)
        return target()
    except Exception:
        return None
