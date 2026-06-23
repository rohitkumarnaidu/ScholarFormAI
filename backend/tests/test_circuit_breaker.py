# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for the circuit breaker decorator — public API behavior.
"""
from __future__ import annotations

import pytest
from app.pipeline.safety.circuit_breaker import (
    circuit_breaker,
    CircuitBreakerOpenException,
)

class TestCircuitBreakerAPI:

    def test_starts_closed(self):
        """Fresh function allows calls."""
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def ok():
            return "ok"
        assert ok() == "ok"

    def test_open_circuit_uses_fallback(self):
        """When it fails repetitively, the fallback function is called instead of raising."""
        fallback_called = {"v": False}

        def my_fallback(*args, **kwargs):
            fallback_called["v"] = True
            return "fallback"

        @circuit_breaker(failure_threshold=2, recovery_timeout=9999, fallback_function=my_fallback)
        def always_fails():
            raise ValueError("fail")

        for _ in range(3):
            always_fails()

        assert fallback_called["v"] is True

    def test_open_without_fallback_raises_open_exception(self):
        """Open circuit without fallback → CircuitBreakerOpenException or the underlying exception."""
        @circuit_breaker(failure_threshold=2, recovery_timeout=9999)
        def bad():
            raise IOError("io")

        for _ in range(2):
            try:
                bad()
            except Exception:
                pass

        with pytest.raises(CircuitBreakerOpenException):
            bad()
