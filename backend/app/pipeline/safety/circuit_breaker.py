# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
circuit_breaker.py - pybreaker-backed circuit breaker decorator.

Replaces non-thread-safe function-attribute state with pybreaker.

Backward-compatible public API:
  circuit_breaker(failure_threshold, recovery_timeout, fallback_function)
  CircuitBreakerOpenException
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pybreaker

    _PYBREAKER = True
except ImportError:
    _PYBREAKER = False
    logger.warning("pybreaker not installed - legacy circuit breaker active. pip install pybreaker")


class CircuitBreakerOpenException(Exception):
    """Raised when the circuit is open and calls are blocked."""

    pass


def circuit_breaker(
    failure_threshold: int = 3,
    recovery_timeout: int = 60,
    fallback_function: Callable | None = None,
):
    """Thread-safe circuit breaker decorator (pybreaker-powered when available)."""
    if _PYBREAKER:

        def decorator(func: Callable) -> Callable:
            _instance_attr = "_circuit_breaker_instances"
            _breaker_key = func.__qualname__

            class _Log(pybreaker.CircuitBreakerListener):
                def state_change(self, cb, old, new):
                    logger.warning("CircuitBreaker '%s': %s -> %s", func.__name__, old.name, new.name)

                def failure(self, cb, exc):
                    logger.warning(
                        "CircuitBreaker '%s': failure %d/%d - %s",
                        func.__name__,
                        cb.fail_counter,
                        failure_threshold,
                        exc,
                    )

            def _new_breaker() -> "pybreaker.CircuitBreaker":
                return pybreaker.CircuitBreaker(
                    fail_max=failure_threshold,
                    reset_timeout=recovery_timeout,
                    listeners=[_Log()],
                )

            shared_breaker = _new_breaker()

            def _get_breaker(args) -> "pybreaker.CircuitBreaker":
                if args:
                    instance = args[0]
                    if hasattr(instance, "__dict__"):
                        breakers = instance.__dict__.setdefault(_instance_attr, {})
                        instance_breaker = breakers.get(_breaker_key)
                        if instance_breaker is None:
                            instance_breaker = _new_breaker()
                            breakers[_breaker_key] = instance_breaker
                        return instance_breaker
                return shared_breaker

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                breaker = _get_breaker(args)
                try:
                    return breaker.call(func, *args, **kwargs)
                except pybreaker.CircuitBreakerError as exc:
                    logger.error("CircuitBreaker OPEN for '%s': %s", func.__name__, exc)
                    if fallback_function:
                        try:
                            return fallback_function(*args, **kwargs)
                        except Exception as fb:
                            logger.error("Fallback also failed: %s", fb)
                            return {}
                    raise CircuitBreakerOpenException(f"Circuit Breaker is OPEN for {func.__name__}") from exc
                except Exception:
                    if fallback_function:
                        try:
                            return fallback_function(*args, **kwargs)
                        except Exception as fb:
                            logger.error("Fallback also failed: %s", fb)
                            return {}
                    raise

            return wrapper

        return decorator

    # --- Legacy fallback (original non-thread-safe implementation) ---
    import time

    def decorator(func: Callable) -> Callable:
        _instance_attr = "_circuit_breaker_states"
        _state_key = func.__qualname__

        def _new_state():
            return {"failures": 0, "last_failure_time": 0.0, "state": "CLOSED"}

        shared_state = _new_state()

        def _get_state(args):
            if args:
                instance = args[0]
                if hasattr(instance, "__dict__"):
                    states = instance.__dict__.setdefault(_instance_attr, {})
                    state = states.get(_state_key)
                    if state is None:
                        state = _new_state()
                        states[_state_key] = state
                    return state
            return shared_state

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            state = _get_state(args)
            now = time.time()
            if state["state"] == "OPEN":
                if now - state["last_failure_time"] > recovery_timeout:
                    state["state"] = "HALF_OPEN"
                else:
                    logger.warning("CircuitBreaker OPEN for %s. Using fallback.", func.__name__)
                    if fallback_function:
                        return fallback_function(*args, **kwargs)
                    raise CircuitBreakerOpenException(f"Circuit Breaker is OPEN for {func.__name__}")
            try:
                result = func(*args, **kwargs)
                if state["state"] == "HALF_OPEN":
                    logger.info("CircuitBreaker RECOVERED for %s.", func.__name__)
                state["failures"] = 0
                state["state"] = "CLOSED"
                return result
            except Exception as exc:
                state["failures"] += 1
                state["last_failure_time"] = now
                logger.warning(
                    "CircuitBreaker: %s failed (%d/%d): %s",
                    func.__name__,
                    state["failures"],
                    failure_threshold,
                    exc,
                )
                if state["failures"] >= failure_threshold:
                    state["state"] = "OPEN"
                    logger.error("CircuitBreaker TRIPPED for %s. Blocking %ds.", func.__name__, recovery_timeout)
                if fallback_function:
                    try:
                        return fallback_function(*args, **kwargs)
                    except Exception as fb:
                        logger.error("Fallback also failed: %s", fb)
                        return {}
                raise

        return wrapper

    return decorator
