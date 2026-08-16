import pytest


class TestCircuitBreaker:
    def test_decorates_function(self):
        from app.pipeline.safety.circuit_breaker import circuit_breaker

        @circuit_breaker(failure_threshold=5, recovery_timeout=30)
        def my_func():
            return "ok"

        assert my_func() == "ok"


class TestRetryGuard:
    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        calls = []

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def succeeds():
            calls.append(1)
            return "done"

        result = await succeeds()
        assert result == "done"
        assert len(calls) == 1

    def test_sync_retry_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def succeeds():
            return "done"

        assert succeeds() == "done"

    def test_sync_retry_exhausted(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff

        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def always_fails():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            always_fails()

    def test_execute_with_retry(self):
        from app.pipeline.safety.retry_guard import execute_with_retry

        def works():
            return 42

        assert execute_with_retry(works, max_retries=1, backoff_factor=0.01) == 42


class TestValidateOutput:
    def test_pydantic_schema_dict_input(self):
        from pydantic import BaseModel

        from app.pipeline.safety.validator_guard import validate_output

        class TestSchema(BaseModel):
            name: str
            value: int

        @validate_output(TestSchema)
        def produce():
            return {"name": "test", "value": 1}

        result = produce()
        assert result["name"] == "test"

    def test_dict_schema_missing_key(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output({"key": str})
        def produce():
            return {"other": 1}

        result = produce()
        assert result == {}

    def test_pydantic_validation_error_returns_fallback(self):
        from pydantic import BaseModel

        from app.pipeline.safety.validator_guard import validate_output

        class TestSchema(BaseModel):
            name: str

        @validate_output(TestSchema)
        def produce():
            return {"name": 123}

        result = produce()
        assert result == {}

    def test_exception_in_func_returns_fallback(self):
        from app.pipeline.safety.validator_guard import validate_output

        @validate_output(None, error_return_value={"fallback": True})
        def produce():
            raise ValueError("bad")

        result = produce()
        assert result == {"fallback": True}


class TestSafeExecution:
    def test_context_manager_does_not_raise(self):
        from app.pipeline.safety.safe_execution import safe_execution

        with safe_execution("test_op"):
            pass
        assert True

    def test_context_manager_suppresses_exception(self):
        from app.pipeline.safety.safe_execution import safe_execution

        with safe_execution("test_fail"):
            raise ValueError("caught")
        assert True

    def test_safe_function_decorator(self):
        from app.pipeline.safety.safe_execution import safe_function

        @safe_function(fallback_value="fallback", error_message="failed")
        def failing():
            raise RuntimeError("boom")

        assert failing() == "fallback"

    def test_safe_function_success(self):
        from app.pipeline.safety.safe_execution import safe_function

        @safe_function(fallback_value="fallback")
        def working():
            return "success"

        assert working() == "success"
