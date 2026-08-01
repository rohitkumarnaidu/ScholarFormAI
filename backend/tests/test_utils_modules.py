# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from app.utils.serialization import build_structured_data, safe_model_dump
from app.utils.singleton import resolve_optional_callable


class TestSerialization:
    """Tests for serialization utilities."""

    def test_build_structured_data_with_blocks(self):
        from types import SimpleNamespace

        from app.models import Block, BlockType, DocumentMetadata, TextStyle

        doc = SimpleNamespace(
            blocks=[
                Block(block_id="b1", text="Hello", index=0,                 block_type=BlockType.BODY, style=TextStyle()),
            ],
            metadata=DocumentMetadata(title="Test"),
            references=[],
            processing_history=[],
        )
        result = build_structured_data(doc)
        assert "blocks" in result
        assert "sections" in result
        assert "metadata" in result
        assert len(result["blocks"]) == 1

    def test_build_structured_data_partial(self):
        from types import SimpleNamespace

        doc = SimpleNamespace(blocks=[], metadata=None, references=[], processing_history=[])
        result = build_structured_data(doc, partial=True)
        assert result["partial"] is True

    def test_safe_model_dump_dict(self):
        data = {"key": "value", "number": 42}
        result = safe_model_dump(data)
        assert result == data

    def test_safe_model_dump_object(self):
        class MockModel:
            def model_dump(self, mode="python"):
                return {"name": "test", "value": 123}

        obj = MockModel()
        result = safe_model_dump(obj)
        assert result == {"name": "test", "value": 123}

    def test_safe_model_dump_fallback(self):
        result = safe_model_dump("plain-string")
        assert result == {"value": "plain-string"}

    def test_safe_model_dump_none(self):
        result = safe_model_dump(None)
        assert result == {}


class TestSingleton:
    """Tests for singleton/resolution utilities."""

    def test_resolve_optional_callable_missing_module(self):
        result = resolve_optional_callable("nonexistent_module_xyz", "something")
        assert result is None

    def test_resolve_optional_callable_missing_attr(self):
        result = resolve_optional_callable("app.config.settings", "nonexistent_attr_xyz")
        assert result is None

    def test_resolve_optional_callable_returns_none_for_non_callable_attr(self):
        result = resolve_optional_callable("app.config.settings", "settings")
        assert result is None  # settings is an instance, not callable -> None
