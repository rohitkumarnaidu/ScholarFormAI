# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException, circuit_breaker
from app.pipeline.safety.retry_guard import execute_with_retry, retry_with_backoff
from app.pipeline.safety.safe_execution import safe_async_function, safe_execution, safe_function
from app.pipeline.safety.validator_guard import validate_output


class _TestModel(BaseModel):
    name: str
    value: int


class TestCircuitBreakerLegacy:
    @pytest.fixture(autouse=True)
    def _patch_pybreaker(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            yield

    def test_closed_passes(self):
        @circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def ok():
            return "ok"

        assert ok() == "ok"

    def test_trips_after_threshold(self):
        @circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def flaky():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            flaky()
        with pytest.raises(ValueError):
            flaky()
        with pytest.raises(CircuitBreakerOpenException):
            flaky()

    def test_fallback_on_trip(self):
        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=lambda: "fallback")
        def flaky():
            raise ValueError("boom")

        assert flaky() == "fallback"

    def test_recovers_after_timeout(self):
        call_count = 0

        @circuit_breaker(failure_threshold=1, recovery_timeout=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("boom")

        with pytest.raises(ValueError):
            flaky()
        with pytest.raises(CircuitBreakerOpenException):
            flaky()
        time.sleep(0.02)
        with pytest.raises(ValueError):
            flaky()
        time.sleep(0.02)
        assert flaky() is None

    def test_fallback_also_fails_returns_empty_dict(self):
        @circuit_breaker(
            failure_threshold=1,
            recovery_timeout=60,
            fallback_function=lambda: (_ for _ in ()).throw(ValueError("fb fail")),
        )
        def flaky():
            raise ValueError("boom")

        assert flaky() == {}

    def test_success_resets_failures(self):
        call_count = 0

        @circuit_breaker(failure_threshold=2, recovery_timeout=60)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("boom")

        with pytest.raises(ValueError):
            flaky()
        assert flaky() is None
        assert flaky() is None

    def test_instance_isolation(self):
        class Service:
            @circuit_breaker(failure_threshold=1, recovery_timeout=60)
            def call(self):
                raise ValueError("fail")

        s1 = Service()
        s2 = Service()
        with pytest.raises(ValueError):
            s1.call()
        with pytest.raises(CircuitBreakerOpenException):
            s1.call()
        with pytest.raises(ValueError):
            s2.call()


class TestCircuitBreakerPybreaker:
    @pytest.fixture(autouse=True)
    def _patch_pybreaker(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            with patch("app.pipeline.safety.circuit_breaker.pybreaker") as mock_pb:
                mock_pb.CircuitBreakerError = type("Error", (Exception,), {})
                mock_pb.CircuitBreakerListener = type(
                    "Listener", (object,), {"state_change": lambda s, c, o, n: None, "failure": lambda s, c, e: None}
                )
                mock_pb.CircuitBreaker.return_value.call.side_effect = lambda f, *a, **kw: f(*a, **kw)
                yield mock_pb

    def test_closed_passes(self, _patch_pybreaker):
        @circuit_breaker(failure_threshold=3, recovery_timeout=60)
        def ok():
            return "ok"

        assert ok() == "ok"

    def test_open_raises(self, _patch_pybreaker):
        _patch_pybreaker.CircuitBreaker.return_value.call.side_effect = _patch_pybreaker.CircuitBreakerError()

        @circuit_breaker(failure_threshold=1, recovery_timeout=60)
        def fail():
            return "never"

        with pytest.raises(CircuitBreakerOpenException):
            fail()

    def test_open_fallback(self, _patch_pybreaker):
        _patch_pybreaker.CircuitBreaker.return_value.call.side_effect = _patch_pybreaker.CircuitBreakerError()

        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=lambda: "fb")
        def fail():
            raise ValueError("nope")

        assert fail() == "fb"

    def test_fallback_failure_returns_empty(self, _patch_pybreaker):
        _patch_pybreaker.CircuitBreaker.return_value.call.side_effect = ValueError("nope")

        @circuit_breaker(
            failure_threshold=1,
            recovery_timeout=60,
            fallback_function=lambda: (_ for _ in ()).throw(ValueError("fb fail")),
        )
        def fail():
            raise ValueError("nope")

        assert fail() == {}

    def test_instance_breaker_pybreaker(self, _patch_pybreaker):
        class Service:
            @circuit_breaker(failure_threshold=3, recovery_timeout=60)
            def call(self):
                return "ok"

        s = Service()
        assert s.call() == "ok"


class TestRetryGuard:
    def test_sync_success_first_try(self):
        @retry_with_backoff(max_retries=2)
        def ok():
            return "done"

        assert ok() == "done"

    def test_sync_retry_then_succeed(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("not yet")
            return "done"

        assert flaky() == "done"
        assert call_count == 2

    def test_sync_exhaust_retries(self):
        @retry_with_backoff(max_retries=1, backoff_factor=0.01)
        def always_fails():
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            always_fails()

    def test_sync_base_delay_backwards_compat(self):
        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def ok():
            return "done"

        assert ok() == "done"

    @pytest.mark.asyncio
    async def test_async_success_first_try(self):
        @retry_with_backoff(max_retries=2)
        async def ok():
            return "done"

        assert await ok() == "done"

    @pytest.mark.asyncio
    async def test_async_exhaust_retries(self):
        @retry_with_backoff(max_retries=1, backoff_factor=0.01)
        async def always_fails():
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            await always_fails()

    def test_execute_with_retry_success(self):
        result = execute_with_retry(lambda: "done", max_retries=2, backoff_factor=0.01)
        assert result == "done"

    def test_execute_with_retry_failure(self):
        with pytest.raises(ValueError):
            execute_with_retry(lambda: (_ for _ in ()).throw(ValueError("fail")), max_retries=1, backoff_factor=0.01)


class TestSafeExecution:
    def test_context_no_error(self):
        result = []
        with safe_execution("test"):
            result.append(1)
        assert result == [1]

    def test_context_suppresses_error(self):
        with safe_execution("test", error_return_value=None):
            raise ValueError("suppressed")

    def test_context_suppresses_error_with_message(self):
        with safe_execution("op_name", error_return_value="fallback"):
            raise ValueError("my error")
        # exception is suppressed

    def test_safe_function_decorator(self):
        @safe_function(fallback_value="fallback")
        def fails():
            raise ValueError("nope")

        assert fails() == "fallback"

    def test_safe_function_success(self):
        @safe_function(fallback_value="fallback")
        def ok():
            return "success"

        assert ok() == "success"

    @pytest.mark.asyncio
    async def test_safe_async_function_fallback(self):
        @safe_async_function(fallback_value="fallback")
        async def fails():
            raise ValueError("nope")

        result = await fails()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_safe_async_function_success(self):
        @safe_async_function(fallback_value="fallback")
        async def ok():
            return "success"

        assert await ok() == "success"


class _Schema(BaseModel):
    name: str
    count: int


class TestValidatorGuard:
    def test_pydantic_valid_dict(self):
        @validate_output(schema=_Schema)
        def good():
            return {"name": "test", "count": 42}

        result = good()
        assert result["name"] == "test"
        assert result["count"] == 42

    def test_pydantic_invalid_dict_returns_fallback(self):
        @validate_output(schema=_Schema, error_return_value={"fallback": True})
        def bad():
            return {"name": "test"}

        result = bad()
        assert result == {"fallback": True}

    def test_pydantic_model_instance(self):
        @validate_output(schema=_Schema)
        def model_return():
            return _Schema(name="x", count=1)

        result = model_return()
        assert result["name"] == "x"

    def test_dict_schema_missing_keys(self):
        @validate_output(schema={"title": str, "year": int})
        def missing():
            return {"title": "Test"}

        result = missing()
        assert result == {}

    def test_dict_schema_valid(self):
        @validate_output(schema={"title": str, "year": int})
        def valid():
            return {"title": "Test", "year": 2024}

        result = valid()
        assert result["title"] == "Test"

    def test_exception_in_wrapped(self):
        @validate_output(schema=_Schema)
        def throws():
            raise RuntimeError("boom")

        result = throws()
        assert result == {}

    def test_raw_return_passthrough(self):
        @validate_output(schema=_Schema)
        def raw():
            return "plain_string"

        assert raw() == "plain_string"


class TestLlmValidator:
    def test_fallback_without_guardrails(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_Schema)
            def good():
                return {"name": "t", "count": 1}

            result = good()
            assert result["name"] == "t"
            assert result["count"] == 1

    def test_fallback_returns_empty_on_validation_error(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_Schema, error_return_value={"e": 1})
            def bad():
                return {"name": "t"}

            result = bad()
            assert result == {"e": 1}

    def test_fallback_handles_exception(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_Schema)
            def throws():
                raise RuntimeError("boom")

            result = throws()
            assert result == {}

    def test_fallback_non_base_model_schema(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema={"key": str})
            def ok():
                return {"key": "val"}

            result = ok()
            # With non-BaseModel schema and fallback mode, raw dict passes through
            assert result == {"key": "val"}
