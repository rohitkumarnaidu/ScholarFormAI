# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel


class TestValidatorGuard:
    def test_basic_pass_through(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema=None)
        def func():
            return {"key": "value"}
        assert func() == {"key": "value"}

    def test_pydantic_model_validation(self):
        from app.pipeline.safety.validator_guard import validate_output
        class MyModel(BaseModel):
            name: str
            age: int
        @validate_output(schema=MyModel)
        def func():
            return {"name": "Alice", "age": 30}
        result = func()
        assert result["name"] == "Alice"

    def test_pydantic_model_invalid_returns_empty(self):
        from app.pipeline.safety.validator_guard import validate_output
        class MyModel(BaseModel):
            name: str
            age: int
        @validate_output(schema=MyModel)
        def func():
            return {"name": "Alice"}
        result = func()
        assert result == {}

    def test_pydantic_model_instance(self):
        from app.pipeline.safety.validator_guard import validate_output
        class MyModel(BaseModel):
            name: str
        @validate_output(schema=MyModel)
        def func():
            return MyModel(name="Bob")
        result = func()
        assert result["name"] == "Bob"

    def test_dict_schema_missing_keys(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema={"name": str, "age": int})
        def func():
            return {"name": "Alice"}
        result = func()
        assert result == {}

    def test_dict_schema_valid(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema={"name": str})
        def func():
            return {"name": "Alice", "extra": "ignored"}
        result = func()
        assert result == {"name": "Alice", "extra": "ignored"}

    def test_exception_in_func_returns_empty(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema=None)
        def func():
            raise RuntimeError("boom")
        result = func()
        assert result == {}

    def test_custom_error_return_value(self):
        from app.pipeline.safety.validator_guard import validate_output
        @validate_output(schema=None, error_return_value={"error": "custom"})
        def func():
            raise RuntimeError("boom")
        result = func()
        assert result == {"error": "custom"}
