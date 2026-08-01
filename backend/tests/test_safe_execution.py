from unittest.mock import patch

import pytest


class TestSafeExecution:
    def test_swallows_exception(self):
        from app.pipeline.safety.safe_execution import safe_execution
        with safe_execution("test_op"):
            raise ValueError("boom")
        assert True

    def test_no_exception_passes_through(self):
        from app.pipeline.safety.safe_execution import safe_execution
        result = []
        with safe_execution("test_op"):
            result.append(42)
        assert result == [42]

    def test_logs_exception(self):
        from app.pipeline.safety.safe_execution import safe_execution
        with patch("app.pipeline.safety.safe_execution.logger") as mock_logger:
            with safe_execution("op_x"):
                raise RuntimeError("crash")
            mock_logger.log.assert_called()


class TestSafeFunction:
    def test_returns_fallback_on_error(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value=-1)
        def failing():
            raise ValueError()
        assert failing() == -1

    def test_normal_execution(self):
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value=None)
        def working():
            return 99
        assert working() == 99


class TestSafeAsyncFunction:
    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        from app.pipeline.safety.safe_execution import safe_async_function
        @safe_async_function(fallback_value="fallback")
        async def failing():
            raise KeyError("missing")
        assert await failing() == "fallback"

    @pytest.mark.asyncio
    async def test_success_returns_value(self):
        from app.pipeline.safety.safe_execution import safe_async_function
        @safe_async_function(fallback_value="fallback")
        async def working():
            return "ok"
        assert await working() == "ok"
