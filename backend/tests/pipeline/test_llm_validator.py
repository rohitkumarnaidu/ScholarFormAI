# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests for llm_validator — covers HAS_GUARDRAILS, fallback_validate_output,
and guard_llm_output with all branches and edge cases.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel


class _TestSchema(BaseModel):
    name: str
    value: int


class TestModuleLevel:
    def test_HAS_GUARDRAILS_is_boolean(self):
        import app.pipeline.safety.llm_validator as lv

        assert isinstance(lv.HAS_GUARDRAILS, bool)

    def test_guardrails_path_active_when_HAS_GUARDRAILS(self):
        """guard_llm_output enters the Guardrails branch when HAS_GUARDRAILS=True and schema is BaseModel."""
        import app.pipeline.safety.llm_validator as lv

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "Guard") as mock_guard_cls,
        ):
            mock_guard = MagicMock()
            mock_guard_cls.for_pydantic.return_value = mock_guard
            decorator = lv.guard_llm_output(_TestSchema)
            # Guard.for_pydantic is called inside decorator, not guard_llm_output
            decorator(lambda: '{"name": "test", "value": 1}')
            mock_guard_cls.for_pydantic.assert_called_once_with(output_class=_TestSchema)

    def test_fallback_path_when_HAS_GUARDRAILS_False(self):
        """guard_llm_output uses fallback_validate_output when HAS_GUARDRAILS=False."""
        import app.pipeline.safety.llm_validator as lv

        with (
            patch.object(lv, "HAS_GUARDRAILS", False),
            patch.object(lv, "fallback_validate_output") as mock_fallback,
        ):
            mock_fallback.return_value = lambda f: f
            schema = MagicMock(spec=BaseModel)
            result = lv.guard_llm_output(schema)
            mock_fallback.assert_called_once_with(schema, error_return_value=None)
            assert callable(result)

    def test_fallback_path_when_not_BaseModel(self):
        """guard_llm_output falls back when schema is not a BaseModel subclass."""
        import app.pipeline.safety.llm_validator as lv

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "fallback_validate_output") as mock_fallback,
        ):
            mock_fallback.return_value = lambda f: f
            result = lv.guard_llm_output(int)
            mock_fallback.assert_called_once_with(int, error_return_value=None)
            assert callable(result)

    def test_fallback_path_when_schema_is_not_a_type(self):
        """guard_llm_output falls back when schema is not a type at all."""
        import app.pipeline.safety.llm_validator as lv

        with (
            patch.object(lv, "HAS_GUARDRAILS", True),
            patch.object(lv, "fallback_validate_output") as mock_fallback,
        ):
            mock_fallback.return_value = lambda f: f
            result = lv.guard_llm_output("not_a_type")
            mock_fallback.assert_called_once_with("not_a_type", error_return_value=None)
            assert callable(result)

    def test_fallback_validate_output_from_validator_guard(self):
        with patch("app.pipeline.safety.llm_validator.fallback_validate_output") as mock_fb:
            import app.pipeline.safety.llm_validator as lv

            lv.fallback_validate_output = mock_fb


class TestFallbackValidateOutput:
    def test_imported_from_validator_guard(self):
        import app.pipeline.safety.llm_validator as lv

        assert callable(lv.fallback_validate_output)

    def _extreme_fallback_env(self, lv):
        """Temporarily force extreme fallback by hiding validator_guard."""
        import importlib

        orig_module = sys.modules.get("app.pipeline.safety.validator_guard")
        sys.modules["app.pipeline.safety.validator_guard"] = None
        importlib.reload(lv)
        return orig_module

    def _restore_validator_guard(self, lv, orig_module):
        """Restore validator_guard module after extreme fallback test."""
        import importlib

        if orig_module:
            sys.modules["app.pipeline.safety.validator_guard"] = orig_module
        else:
            sys.modules.pop("app.pipeline.safety.validator_guard", None)
        importlib.reload(lv)

    def test_extreme_fallback_works(self):
        import app.pipeline.safety.llm_validator as lv

        orig = self._extreme_fallback_env(lv)

        @lv.fallback_validate_output(schema=_TestSchema)
        def good():
            return {"name": "test", "value": 1}

        result = good()
        assert result["name"] == "test"
        assert result["value"] == 1

        self._restore_validator_guard(lv, orig)

    def test_extreme_fallback_exception_returns_error_value(self):
        import app.pipeline.safety.llm_validator as lv

        orig = self._extreme_fallback_env(lv)

        @lv.fallback_validate_output(schema=_TestSchema, error_return_value={"fallback": True})
        def bad():
            raise ValueError("nope")

        result = bad()
        assert result == {"fallback": True}

        self._restore_validator_guard(lv, orig)

    def test_extreme_fallback_exception_no_error_value(self):
        import app.pipeline.safety.llm_validator as lv

        orig = self._extreme_fallback_env(lv)

        @lv.fallback_validate_output(schema=_TestSchema)
        def bad():
            raise ValueError("nope")

        result = bad()
        assert result == {}

        self._restore_validator_guard(lv, orig)


class TestGuardLlmOutputFallback:
    """Tests guard_llm_output when HAS_GUARDRAILS is False."""

    def test_fallback_success(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_TestSchema)
            def good():
                return {"name": "test", "value": 42}

            result = good()
            assert result["name"] == "test"
            assert result["value"] == 42

    def test_fallback_validation_error(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_TestSchema, error_return_value={"e": 1})
            def bad():
                return {"name": "test"}

            result = bad()
            assert result == {"e": 1}

    def test_fallback_exception(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", False):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_TestSchema)
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
            assert result == {"key": "val"}


class TestGuardLlmOutputGuardrails:
    """Tests guard_llm_output when HAS_GUARDRAILS is True."""

    @pytest.fixture
    def mock_guardrails(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True):
            with patch("app.pipeline.safety.llm_validator.Guard") as mock_guard_cls:
                mock_guard_instance = MagicMock()
                mock_guard_cls.for_pydantic.return_value = mock_guard_instance
                yield mock_guard_cls, mock_guard_instance

    def test_already_pydantic_model(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def returns_model():
            return _TestSchema(name="x", value=1)

        result = returns_model()
        assert result["name"] == "x"
        assert result["value"] == 1
        mock_guard_instance.parse.assert_not_called()

    def test_dict_input_validated(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_outcome = MagicMock()
        mock_outcome.validated_output = {"name": "test", "value": 42}
        mock_guard_instance.parse.return_value = mock_outcome

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def returns_dict():
            return {"name": "test", "value": 42}

        result = returns_dict()
        assert result is not None

    def test_string_input_validated(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_outcome = MagicMock()
        mock_outcome.validated_output = {"name": "test", "value": 42}
        mock_guard_instance.parse.return_value = mock_outcome

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def returns_string():
            return '{"name": "test", "value": 42}'

        result = returns_string()
        assert result is not None

    def test_unknown_type_passthrough(self, mock_guardrails):
        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def returns_int():
            return 42

        result = returns_int()
        assert result == 42

    def test_guardrails_returns_none_fallback(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_outcome = MagicMock()
        mock_outcome.validated_output = None
        mock_guard_instance.parse.return_value = mock_outcome

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema, error_return_value={"fallback": True})
        def good():
            return '{"name": "test", "value": 42}'

        result = good()
        assert result == {"fallback": True}

    def test_guardrails_exception_handled(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_guard_instance.parse.side_effect = RuntimeError("parse error")

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema, error_return_value={"err": True})
        def good():
            return '{"name": "test", "value": 42}'

        result = good()
        assert result == {"err": True}

    def test_func_exception_handled(self, mock_guardrails):
        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema, error_return_value={"err": True})
        def throws():
            raise RuntimeError("fail")

        result = throws()
        assert result == {"err": True}

    def test_validated_output_with_model_dump(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"name": "test", "value": 42}
        mock_outcome = MagicMock()
        mock_outcome.validated_output = mock_model
        mock_guard_instance.parse.return_value = mock_outcome

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def good():
            return '{"name": "test", "value": 42}'

        result = good()
        assert result["name"] == "test"

    def test_parse_with_guardrails_running_loop(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_outcome = MagicMock()
        mock_outcome.validated_output = {"name": "t", "value": 1}
        mock_guard_instance.parse.return_value = mock_outcome

        from app.pipeline.safety.llm_validator import guard_llm_output

        @guard_llm_output(schema=_TestSchema)
        def good():
            return '{"name": "t", "value": 1}'

        result = good()
        assert result is not None

    def test_parse_no_running_loop_new_loop(self, mock_guardrails):
        mock_guard_cls, mock_guard_instance = mock_guardrails
        mock_outcome = MagicMock()
        mock_outcome.validated_output = {"name": "t", "value": 1}
        mock_guard_instance.parse.return_value = mock_outcome
        mock_loop = MagicMock()

        import app.pipeline.safety.llm_validator as lv

        with patch.object(lv, "asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("no loop")
            mock_asyncio.new_event_loop.return_value = mock_loop

            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema=_TestSchema)
            def good():
                return '{"name": "t", "value": 1}'

            result = good()
            assert result is not None
            mock_loop.close.assert_called_once()


class TestGuardLlmOutputNonBaseModelSchema:
    """When schema is not a BaseModel, always falls back even if HAS_GUARDRAILS is True."""

    def test_non_base_model_fallback(self):
        with patch("app.pipeline.safety.llm_validator.HAS_GUARDRAILS", True):
            from app.pipeline.safety.llm_validator import guard_llm_output

            @guard_llm_output(schema={"key": str, "val": int})
            def ok():
                return {"key": "x", "val": 1}

            result = ok()
            assert result == {"key": "x", "val": 1}
