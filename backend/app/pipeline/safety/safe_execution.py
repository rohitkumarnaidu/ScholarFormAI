# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import contextlib
import logging
import traceback
from collections.abc import Generator
from typing import Any

# Configure logger
logger = logging.getLogger(__name__)


@contextlib.contextmanager
def safe_execution(
    operation_name: str, error_return_value: Any = None, log_level: int = logging.ERROR
) -> Generator[None, None, None]:
    """
    Context manager that catches ANY exception within the block,
    logs it with a traceback, and suppressing the crash.

    Usage:
        with safe_execution("Critical Operation"):
            risky_code()
    """
    try:
        yield
    except Exception as e:
        logger.log(log_level, f"🛡️ Safety Net caught crash in '{operation_name}': {e}")
        logger.log(log_level, traceback.format_exc())
        # We suppress the exception so the program continues
        # If the caller *needs* a return value, they should handle it inside the block
        # or check side effects.


import functools


def safe_function(fallback_value: Any = None, error_message: str = None):
    """
    Decorator that wraps a function in the safe_execution context.
    Returns fallback_value if an exception occurs.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = error_message or func.__name__
            with safe_execution(op_name, log_level=logging.ERROR):
                return func(*args, **kwargs)
            return fallback_value

        return wrapper

    return decorator


def safe_async_function(fallback_value: Any = None, error_message: str = None):
    """
    Decorator that wraps an ASYNC function in the safe_execution context.
    Returns fallback_value if an exception occurs.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = error_message or func.__name__
            # specialized async handling
            try:
                # We can't use the sync context manager directly for the await part easily
                # without wrapping the whole block.
                # But safe_execution IS a context manager.
                with safe_execution(op_name, log_level=logging.ERROR):
                    return await func(*args, **kwargs)
            except Exception:
                # safe_execution swallows exceptions, but if the await itself raises,
                # safe_execution catches it.
                # HOWEVER, if safe_execution suppresses it, we exit the with block normally.
                # We need to ensure we return the fallback.
                pass
            return fallback_value

        return wrapper

    return decorator
