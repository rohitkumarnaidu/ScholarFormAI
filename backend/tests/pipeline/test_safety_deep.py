# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestCircuitBreaker:
    def test_circuit_breaker_open_exception(self):
        from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException

        exc = CircuitBreakerOpenException("test")
        assert isinstance(exc, Exception)
        assert "test" in str(exc)

    def test_pybreaker_available(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            call_count = [0]

            @circuit_breaker(failure_threshold=3, recovery_timeout=60)
            def my_func():
                call_count[0] += 1
                return "ok"

            assert my_func() == "ok"
            assert call_count[0] == 1

    def test_pybreaker_failure_and_trip(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException, circuit_breaker

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

    def test_pybreaker_fallback(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            def fallback(*a, **kw):
                return "fallback_ok"

            @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
            def fail_func():
                raise ValueError("boom")

            result = fail_func()
            assert result == "fallback_ok"

    def test_pybreaker_fallback_also_fails(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            def fallback(*a, **kw):
                raise RuntimeError("fallback failed")

            @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
            def fail_func():
                raise ValueError("boom")

            result = fail_func()
            assert result == {}

    def test_pybreaker_instance_isolation(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException, circuit_breaker

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

    def test_pybreaker_instance_method_success(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", True):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            class MyClass:
                @circuit_breaker(failure_threshold=3, recovery_timeout=60)
                def method(self):
                    return "success"

            instance = MyClass()
            result = instance.method()
            assert result == "success"

    def test_legacy_fallback_success(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            @circuit_breaker(failure_threshold=3, recovery_timeout=60)
            def my_func():
                return "legacy_ok"

            assert my_func() == "legacy_ok"

    def test_legacy_fallback_failure(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import CircuitBreakerOpenException, circuit_breaker

            @circuit_breaker(failure_threshold=1, recovery_timeout=60)
            def fail_func():
                raise ValueError("fail")

            with pytest.raises(ValueError):
                fail_func()
            with pytest.raises(CircuitBreakerOpenException):
                fail_func()

    def test_legacy_half_open_recovery(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            call_count = [0]

            @circuit_breaker(failure_threshold=1, recovery_timeout=0)
            def my_func():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ValueError("first call fails")
                return "recovered"

            with patch("time.time") as mock_time:
                mock_time.return_value = 1000.0
                with pytest.raises(ValueError):
                    my_func()
            result = my_func()
            assert result == "recovered"

    def test_legacy_instance_state(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            class MyClass:
                @circuit_breaker(failure_threshold=2, recovery_timeout=60)
                def method(self):
                    raise ValueError("fail")

            a = MyClass()
            with pytest.raises(ValueError):
                a.method()

    def test_legacy_fallback_function(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            def fallback(*a, **kw):
                return "fb"

            @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
            def fail_func():
                raise ValueError("boom")

            result = fail_func()
            assert result == "fb"

    def test_legacy_fallback_also_fails(self):
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            from app.pipeline.safety.circuit_breaker import circuit_breaker

            def fallback(*a, **kw):
                raise RuntimeError("fb fail")

            @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
            def fail_func():
                raise ValueError("boom")

            result = fail_func()
            assert result == {}


class TestRetryGuard:
    def test_retry_sync_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def my_func():
            return "ok"

        assert my_func() == "ok"

    def test_retry_sync_eventual_failure(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        call_count = [0]

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def fail_func():
            call_count[0] += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fail_func()
        assert call_count[0] == 3

    def test_retry_sync_succeeds_on_retry(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        call_count = [0]

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def my_func():
            return "async_ok"

        result = await my_func()
        assert result == "async_ok"

    @pytest.mark.asyncio
    async def test_retry_async_failure(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        call_count = [0]

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def fail_func():
            call_count[0] += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await fail_func()
        assert call_count[0] == 3

    def test_execute_with_retry(self):
        from app.pipeline.safety.retry_guard import execute_with_retry

        def ok_func():
            return "ok"

        result = execute_with_retry(ok_func, max_retries=2, backoff_factor=0.01)
        assert result == "ok"

    def test_execute_with_retry_failure(self):
        from app.pipeline.safety.retry_guard import execute_with_retry

        def fail_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            execute_with_retry(fail_func, max_retries=1, backoff_factor=0.01)

    def test_retry_guard_alias(self):
        from app.pipeline.safety.retry_guard import retry_guard

        assert retry_guard is not None

    def test_base_delay_override(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        @retry_with_backoff(max_retries=1, base_delay=0.05)
        def my_func():
            return "ok"

        assert my_func() == "ok"


class TestSafeExecution:
    def test_safe_execution_context_no_error(self):
        from app.pipeline.safety.safe_execution import safe_execution

        result = []
        with safe_execution("test_op"):
            result.append(1)
        assert result == [1]

    def test_safe_execution_context_with_error(self):
        from app.pipeline.safety.safe_execution import safe_execution

        result = []
        with safe_execution("crash_op"):
            result.append(1)
            raise ValueError("boom")
            result.append(2)
        assert result == [1]

    def test_safe_execution_custom_log_level(self):
        from app.pipeline.safety.safe_execution import safe_execution

        with safe_execution("custom", log_level=40):
            raise ValueError("test")

    def test_safe_function_no_error(self):
        from app.pipeline.safety.safe_execution import safe_function

        @safe_function(fallback_value="fallback", error_message="Failed")
        def ok_func():
            return "ok"

        assert ok_func() == "ok"

    def test_safe_function_with_error(self):
        from app.pipeline.safety.safe_execution import safe_function

        @safe_function(fallback_value="fallback", error_message="Failed")
        def fail_func():
            raise ValueError("boom")

        assert fail_func() == "fallback"

    def test_safe_function_no_error_message(self):
        from app.pipeline.safety.safe_execution import safe_function

        @safe_function(fallback_value=0)
        def my_func():
            return 42

        assert my_func() == 42

    def test_safe_async_function_success(self):
        from app.pipeline.safety.safe_execution import safe_async_function

        @safe_async_function(fallback_value="fallback", error_message="Failed")
        async def ok_func():
            return "async_ok"

        import asyncio

        result = asyncio.run(ok_func())
        assert result == "async_ok"

    def test_safe_async_function_failure(self):
        from app.pipeline.safety.safe_execution import safe_async_function

        @safe_async_function(fallback_value="fallback", error_message="Failed")
        async def fail_func():
            raise ValueError("boom")

        import asyncio

        result = asyncio.run(fail_func())
        assert result == "fallback"


class TestValidatorGuard:
    def test_validate_output_pydantic_success(self):
        from pydantic import BaseModel

        from app.pipeline.safety.validator_guard import validate_output

        class TestSchema(BaseModel):
            name: str
            value: int

        @validate_output(schema=TestSchema)
        def my_func():
            return {"name": "test", "value": 42}

        result = my_func()
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_validate_output_pydantic_validation_error(self):
        from pydantic import BaseModel

        from app.pipeline.safety.validator_guard import validate_output

        class TestSchema(BaseModel):
            name: str
            value: int

        @validate_output(schema=TestSchema, error_return_value="error")
        def my_func():
            return {"name": "test", "value": "not_a_number"}

        result = my_func()
        assert result == "error" or result == {}

    def test_validate_output_pydantic_instance(self):
        from pydantic import BaseModel

        from app.pipeline.safety.validator_guard import validate_output

        class TestSchema(BaseModel):
            name: str

        @validate_output(schema=TestSchema)
        def my_func():
            return TestSchema(name="hello")

        result = my_func()
        assert result["name"] == "hello"

    def test_validate_output_dict_schema(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output(schema={"name": str, "value": int})
        def my_func():
            return {"name": "test", "value": 42}

        result = my_func()
        assert result["name"] == "test"

    def test_validate_output_dict_missing_keys(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output(schema={"name": str, "value": int}, error_return_value={})
        def my_func():
            return {"name": "test"}

        result = my_func()
        assert result == {}

    def test_validate_output_exception(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output(schema=None, error_return_value="error")
        def my_func():
            raise RuntimeError("fail")

        result = my_func()
        assert result == "error" or result == {}

    def test_validate_output_no_schema(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output(schema=None)
        def my_func():
            return "raw"

        result = my_func()
        assert result == "raw"


class TestLLMValidator:
    def test_guard_llm_output_no_guardrails(self):
        from app.pipeline.safety.llm_validator import guard_llm_output

        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):

            @guard_llm_output(schema=None)
            def my_func():
                return "ok"

            assert my_func() == "ok"

    def test_guard_llm_output_with_guardrails_not_basemodel(self):
        from app.pipeline.safety.llm_validator import guard_llm_output

        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True):

            @guard_llm_output(schema=str)
            def my_func():
                return "ok"

            assert my_func() == "ok"

    def test_guard_llm_output_returns_pydantic(self):
        from pydantic import BaseModel

        from app.pipeline.safety.llm_validator import guard_llm_output

        class TestModel(BaseModel):
            name: str

        with (
            patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True),
            patch("app.pipeline.safety.llm_validator.Guard") as mock_guard_cls,
        ):
            mock_guard = MagicMock()
            mock_guard_cls.for_pydantic.return_value = mock_guard
            mock_validation = MagicMock()
            mock_validation.validated_output = TestModel(name="test")
            mock_guard.parse.return_value = mock_validation

            @guard_llm_output(schema=TestModel)
            def my_func():
                return {"name": "test"}

            result = my_func()
            assert result["name"] == "test"

    def test_guard_llm_output_parse_exception(self):
        from pydantic import BaseModel

        from app.pipeline.safety.llm_validator import guard_llm_output

        class TestModel(BaseModel):
            name: str

        with (
            patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True),
            patch("app.pipeline.safety.llm_validator.Guard") as mock_guard_cls,
        ):
            mock_guard = MagicMock()
            mock_guard_cls.for_pydantic.return_value = mock_guard
            mock_guard.parse.side_effect = Exception("Parse failed")

            @guard_llm_output(schema=TestModel, error_return_value={})
            def my_func():
                return {"name": "test"}

            result = my_func()
            assert result == {}

    def test_guard_llm_output_returns_native_pydantic(self):
        from pydantic import BaseModel

        from app.pipeline.safety.llm_validator import guard_llm_output

        class TestModel(BaseModel):
            name: str

        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True):

            @guard_llm_output(schema=TestModel)
            def my_func():
                return TestModel(name="native")

            result = my_func()
            assert result["name"] == "native"

    def test_guard_llm_output_returns_other_type(self):
        from pydantic import BaseModel

        from app.pipeline.safety.llm_validator import guard_llm_output

        class TestModel(BaseModel):
            name: str

        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True):

            @guard_llm_output(schema=TestModel)
            def my_func():
                return 42

            result = my_func()
            assert result == 42

    def test_guard_llm_output_validation_none(self):
        from pydantic import BaseModel

        from app.pipeline.safety.llm_validator import guard_llm_output

        class TestModel(BaseModel):
            name: str

        with (
            patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True),
            patch("app.pipeline.safety.llm_validator.Guard") as mock_guard_cls,
        ):
            mock_guard = MagicMock()
            mock_guard_cls.for_pydantic.return_value = mock_guard
            mock_validation = MagicMock()
            mock_validation.validated_output = None
            mock_guard.parse.return_value = mock_validation

            @guard_llm_output(schema=TestModel, error_return_value="err")
            def my_func():
                return {"name": "test"}

            result = my_func()
            assert result == "err"

    def test_fallback_validate_output_not_imported(self):
        import importlib

        import app.pipeline.safety.llm_validator

        with patch.dict("sys.modules", {"app.pipeline.safety.validator_guard": None}):
            importlib.reload(app.pipeline.safety.llm_validator)
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=None)
            def my_func():
                return "fallback"

            assert my_func() == "fallback"
