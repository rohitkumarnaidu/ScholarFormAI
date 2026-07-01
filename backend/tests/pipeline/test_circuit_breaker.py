# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


class TestCircuitBreaker:
    def test_decorator_success(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        call_count = [0]
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def my_func():
            call_count[0] += 1
            return "ok"
        assert my_func() == "ok"
        assert call_count[0] == 1

    def test_decorator_failure_and_trip(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
        call_count = [0]
        @circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def fail_func():
            call_count[0] += 1
            raise ValueError("fail")
        with pytest.raises(ValueError):
            fail_func()
        with pytest.raises(CircuitBreakerOpenException):
            fail_func()
        assert call_count[0] == 2

    def test_fallback_function(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        def fallback(*a, **kw):
            return "fallback_ok"
        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
        def fail_func():
            raise ValueError("boom")
        result = fail_func()
        assert result == "fallback_ok"

    def test_fallback_also_fails_returns_dict(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker
        def fallback(*a, **kw):
            raise RuntimeError("fallback also failed")
        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
        def fail_func():
            raise ValueError("boom")
        result = fail_func()
        assert result == {}

    def test_instance_isolation(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
        class MyClass:
            @circuit_breaker(failure_threshold=2, recovery_timeout=60)
            def method(self):
                raise ValueError("fail")
        a = MyClass()
        b = MyClass()
        with pytest.raises(ValueError):
            a.method()
        with pytest.raises(ValueError):
            b.method()
        with pytest.raises(CircuitBreakerOpenException):
            a.method()
        with pytest.raises(CircuitBreakerOpenException):
            b.method()
