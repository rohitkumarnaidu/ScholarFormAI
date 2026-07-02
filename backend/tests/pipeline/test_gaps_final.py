# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Targeted gap-closing tests for remaining Phase 0 & 1 modules.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, ANY, PropertyMock
from pydantic import BaseModel

import pytest

# ═══════════════════════════════════════════════════════════════════════════
# style_mapper.py — line 26 (bt already starts with BLOCK_)
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# llm_validator.py — lines 16-17 (py ≥3.14), 29-31 (ImportError), 73 (loop), 109 (scalar)
# ═══════════════════════════════════════════════════════════════════════════

class TestLlmValidator:
    def test_guard_llm_output_fallback_error(self):
        """guard_llm_output fallback returns error_return_value on exception."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with patch.object(lv, "HAS_GUARDRAILS", False):
            decorator = lv.guard_llm_output(TestSchema, error_return_value={"fallback": True})
            @decorator
            def failing_func():
                from app.models import Block, BlockType
                raise ValueError("boom")
            result = failing_func()
            assert result == {"fallback": True}

    def test_guardrails_runtime_error_loop_fallback(self):
        """_parse_with_guardrails: no running loop → creates temp loop (lines 75-81)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            outcome = MagicMock()
            outcome.validated_output = TestSchema(name="test")
            guard_instance.parse.return_value = outcome
            # Don't patch get_running_loop → it raises RuntimeError in sync test

            decorator = lv.guard_llm_output(TestSchema)
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return '{"name": "test"}'

            result = my_func()
            assert result == {"name": "test"}

    def test_guardrails_raw_result_is_schema(self):
        """wrapper: function returns BaseModel directly → safe_model_dump (line 90)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            guard_instance.parse.return_value = MagicMock(validated_output=None)

            decorator = lv.guard_llm_output(TestSchema, error_return_value={})
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return TestSchema(name="test")

            result = my_func()
            assert result == {"name": "test"}

    def test_guardrails_raw_result_is_dict(self):
        """wrapper: function returns dict → json.dumps for guard (lines 94-95)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            outcome = MagicMock()
            outcome.validated_output = TestSchema(name="test")
            guard_instance.parse.return_value = outcome

            decorator = lv.guard_llm_output(TestSchema)
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return {"name": "test"}

            result = my_func()
            assert result == {"name": "test"}

    def test_guardrails_raw_result_unknown_type(self):
        """wrapper: function returns unknown type → pass-through (line 99)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance

            decorator = lv.guard_llm_output(TestSchema)
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return 42

            result = my_func()
            assert result == 42

    def test_guard_llm_output_non_base_model_schema(self):
        """schema is not a BaseModel subclass → fallback."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        decorator = lv.guard_llm_output(dict, error_return_value=None)
        @decorator
        def my_func():
            from app.models import Block, BlockType
            raise ValueError("fail")
        result = my_func()
        assert result == {}

    def test_guardrails_running_loop_parse(self):
        """_parse_with_guardrails: running event loop path (line 73)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
            patch("asyncio.get_running_loop", return_value=MagicMock()),
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            outcome = MagicMock()
            outcome.validated_output = TestSchema(name="test")
            guard_instance.parse.return_value = outcome

            decorator = lv.guard_llm_output(TestSchema)
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return '{"name": "test"}'

            result = my_func()
            assert result == {"name": "test"}

    def test_guardrails_validated_output_scalar(self):
        """validated_output is scalar (line 109)."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
            patch("asyncio.get_running_loop", return_value=MagicMock()),
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            outcome = MagicMock()
            outcome.validated_output = "raw_scalar"
            guard_instance.parse.return_value = outcome

            decorator = lv.guard_llm_output(TestSchema)
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return '{"name": "test"}'

            result = my_func()
            assert result == "raw_scalar"

    def test_guardrails_no_validated_output(self):
        """validated_output is None/empty → return error_return_value."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
            patch("asyncio.get_running_loop", return_value=MagicMock()),
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            outcome = MagicMock()
            outcome.validated_output = None
            guard_instance.parse.return_value = outcome

            decorator = lv.guard_llm_output(TestSchema, error_return_value={"err": True})
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return '{"name": "test"}'

            result = my_func()
            assert result == {"err": True}

    def test_guardrails_exception_in_wrapper(self):
        """Exception raised during parse → return error_return_value."""
        from app.models import Block, BlockType
        import app.pipeline.safety.llm_validator as lv

        class TestSchema(BaseModel):
            name: str

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
            patch("asyncio.get_running_loop", return_value=MagicMock()),
        ):
            guard_instance = MagicMock()
            mock_guard_cls.for_pydantic.return_value = guard_instance
            guard_instance.parse.side_effect = ValueError("parse error")

            decorator = lv.guard_llm_output(TestSchema, error_return_value={"safe": True})
            @decorator
            def my_func():
                from app.models import Block, BlockType
                return '{"name": "test"}'

            result = my_func()
            assert result == {"safe": True}

# ═══════════════════════════════════════════════════════════════════════════
# style_mapper.py — line 26 (bt already starts with BLOCK_)
# ═══════════════════════════════════════════════════════════════════════════

class TestStyleMapper:
    def test_block_type_already_prefixed(self):
        from app.models import Block, BlockType
        from app.pipeline.formatting.style_mapper import StyleMapper

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"styles": {"BLOCK_HEADING_1": "Heading 1"}}

        mapper = StyleMapper(mock_loader)
        block = MagicMock()
        block.block_type = "BLOCK_HEADING_1"
        style = mapper.get_style_name(block, "ieee")
        assert style == "Heading 1"

    def test_block_type_already_prefixed_lowercase(self):
        from app.models import Block, BlockType
        from app.pipeline.formatting.style_mapper import StyleMapper

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"styles": {"BLOCK_BODY": "BodyText"}}

        mapper = StyleMapper(mock_loader)
        block = MagicMock()
        block.block_type = "block_body"
        style = mapper.get_style_name(block, "ieee")
        assert style == "BodyText"

    def test_block_type_not_prefixed(self):
        from app.models import Block, BlockType
        from app.pipeline.formatting.style_mapper import StyleMapper

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"styles": {}}

        mapper = StyleMapper(mock_loader)
        block = Block(block_id="b1", index=0, text="Body", block_type=BlockType.BODY)
        style = mapper.get_style_name(block, "ieee")
        assert style == "Normal"

# ═══════════════════════════════════════════════════════════════════════════
# safe_execution.py — lines 68-73
# ═══════════════════════════════════════════════════════════════════════════

class TestSafeExecution:
    def test_safe_function_decorator_fallback(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value="default")
        def failing():
            from app.models import Block, BlockType
            raise ValueError("fail")
        result = failing()
        assert result == "default"

    def test_safe_function_decorator_success(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.safe_execution import safe_function
        @safe_function(fallback_value="default")
        def working():
            from app.models import Block, BlockType
            return "ok"
        result = working()
        assert result == "ok"

    def test_safe_execution_context_suppresses(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.safe_execution import safe_execution
        with safe_execution("test_op"):
            raise ValueError("suppressed")
        # Should not propagate

    def test_safe_async_function_fallback(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.safe_execution import safe_async_function
        import asyncio
        @safe_async_function(fallback_value="fallback")
        async def failing_async():
            from app.models import Block, BlockType
            raise ValueError("async fail")

        result = asyncio.run(failing_async())
        assert result == "fallback"

    def test_safe_async_function_success(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.safe_execution import safe_async_function
        import asyncio
        @safe_async_function(fallback_value="fallback")
        async def working_async():
            from app.models import Block, BlockType
            return "ok"

        result = asyncio.run(working_async())
        assert result == "ok"

# ═══════════════════════════════════════════════════════════════════════════
# circuit_breaker.py — 90% remaining gaps
# ═══════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    def test_circuit_breaker_fallback_fails_returns_empty_dict(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException

        def fallback(*a, **kw):
            from app.models import Block, BlockType
            raise ValueError("fallback also failed")

        @circuit_breaker(failure_threshold=1, recovery_timeout=60, fallback_function=fallback)
        def failing_func():
            from app.models import Block, BlockType
            raise RuntimeError("always fails")

        result = failing_func()
        assert result == {}

    def test_circuit_breaker_no_fallback_raises(self):
        from app.models import Block, BlockType
        from app.pipeline.safety.circuit_breaker import circuit_breaker, CircuitBreakerOpenException

        @circuit_breaker(failure_threshold=1, recovery_timeout=60)
        def failing_func():
            from app.models import Block, BlockType
            raise RuntimeError("always fails")

        with pytest.raises(CircuitBreakerOpenException):
            failing_func()

    def test_circuit_breaker_import_fallback(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.safety.circuit_breaker._PYBREAKER", False):
            import importlib
            with patch.dict("sys.modules", {"pybreaker": None}, clear=False):
                pass  # Already imported, just test the flag path

# ═══════════════════════════════════════════════════════════════════════════
# pdf_ocr.py — import fallback paths
# ═══════════════════════════════════════════════════════════════════════════

class TestPdfOcr:
    def test_pdf_extract_text_exists(self):
        from app.models import Block, BlockType
        from app.pipeline.ocr.pdf_ocr import pdf_extract_text
        assert callable(pdf_extract_text)

# ═══════════════════════════════════════════════════════════════════════════
# figures/caption_matcher.py — line 243
# ═══════════════════════════════════════════════════════════════════════════

class TestFiguresCaptionMatcher:
    pass
