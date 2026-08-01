# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 2, backoff_factor: float = 1.0, base_delay: float = None):
    """
    Decorator to retry a function (sync or async) with exponential backoff.
    """
    if base_delay is not None:
        backoff_factor = base_delay

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                retries = 0
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        if retries >= max_retries:
                            logger.error(
                                "Function '%s' failed permanently after %d retries. Final error: %s",
                                func.__name__,
                                max_retries,
                                e,
                            )
                            raise

                        retries += 1
                        sleep_time = backoff_factor * (2 ** (retries - 1))
                        logger.warning(
                            "Function '%s' failed: %s. Retrying %d/%d in %ds...",
                            func.__name__,
                            e,
                            retries,
                            max_retries,
                            sleep_time,
                        )
                        await asyncio.sleep(sleep_time)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                retries = 0
                while True:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if retries >= max_retries:
                            logger.error(
                                "Function '%s' failed permanently after %d retries. Final error: %s",
                                func.__name__,
                                max_retries,
                                e,
                            )
                            raise

                        retries += 1
                        sleep_time = backoff_factor * (2 ** (retries - 1))
                        logger.warning(
                            "Function '%s' failed: %s. Retrying %d/%d in %ds...",
                            func.__name__,
                            e,
                            retries,
                            max_retries,
                            sleep_time,
                        )
                        time.sleep(sleep_time)

            return sync_wrapper

    return decorator


def execute_with_retry(func: Callable, *args, max_retries: int = 2, backoff_factor: float = 1.0, **kwargs) -> Any:
    """Helper to apply retry dynamically inline."""

    @retry_with_backoff(max_retries=max_retries, backoff_factor=backoff_factor)
    def wrapped_func():
        return func(*args, **kwargs)

    return wrapped_func()


retry_guard = retry_with_backoff
