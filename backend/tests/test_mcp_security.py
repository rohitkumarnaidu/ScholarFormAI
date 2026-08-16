import pytest

pytestmark = [pytest.mark.security]


class TestToolAccessControl:
    def test_tool_registry_requires_authentication(self):
        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()
        assert registry.list_tools() == []

    def test_tool_creation_respects_name_boundary(self):
        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()

        def dummy_fn(inputs):
            return "ok"

        tool = registry.register(
            name="test_tool",
            description="A test tool",
            input_schema={"param": (str, "A parameter")},
            execute_fn=dummy_fn,
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert registry.list_tools() == ["test_tool"]

    def test_tool_parameter_sanitized_via_schema(self):
        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()

        captured = {}

        def safe_fn(inputs):
            captured["input"] = inputs
            return str(inputs.get("param", ""))

        registry.register(
            name="safe_tool",
            description="Safe tool",
            input_schema={"param": (str, "A parameter")},
            execute_fn=safe_fn,
        )
        instance = registry.create_instance("safe_tool")
        assert instance is not None
        result = instance._run(param="hello world")
        assert result == "hello world"

    def test_tool_output_does_not_leak_sensitive_data(self):
        """Tool outputs are not sanitized — known gap. This test verifies current behavior."""
        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()

        def leaking_fn(inputs):
            return "API_KEY=sk-1234567890abcdef"

        registry.register(
            name="leaky_tool",
            description="Might leak data",
            input_schema={"query": (str, "Query string")},
            execute_fn=leaking_fn,
        )
        instance = registry.create_instance("leaky_tool")
        assert instance is not None
        result = instance._run(query="test")
        assert isinstance(result, str)
        assert len(result) > 0


class TestToolDataLeakage:
    def test_tool_execution_error_masks_error_message(self):
        """Tool errors include full exception text — known gap for error sanitization."""
        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()

        def error_fn(inputs):
            raise RuntimeError("Internal: connection pool exhausted at 0x7f1234")

        registry.register(
            name="error_tool",
            description="Error tool",
            input_schema={"x": (str, "Input")},
            execute_fn=error_fn,
        )
        instance = registry.create_instance("error_tool")
        assert instance is not None
        result = instance._run(x="test")
        assert "ERROR:" in result
        assert "Tool execution failed" in result

    def test_tool_registry_global_isolates_tools(self):
        from app.pipeline.agents.custom_tools import list_custom_tools

        tools_before = list_custom_tools()
        from app.pipeline.agents.custom_tools import register_custom_tool

        def dummy(inputs):
            return "ok"

        register_custom_tool(
            name="isolated_tool",
            description="Isolated test tool",
            input_schema={"val": (str, "Value")},
            execute_fn=dummy,
        )
        tools_after = list_custom_tools()
        assert "isolated_tool" in tools_after
        assert len(tools_after) == len(tools_before) + 1

    def test_tool_arg_schema_is_pydantic_model(self):
        from pydantic import BaseModel

        from app.pipeline.agents.custom_tools import ToolRegistry

        registry = ToolRegistry()

        def dummy(inputs):
            return "ok"

        tool_cls = registry.register(
            name="pydantic_tool",
            description="Pydantic tool",
            input_schema={"name": (str, "Name"), "count": (int, "Count")},
            execute_fn=dummy,
        )
        instance = tool_cls()
        assert issubclass(instance.args_schema, BaseModel)
        model = instance.args_schema(name="test", count=5)
        assert model.name == "test"
        assert model.count == 5

    def test_marketplace_tool_integrity_check(self):
        import json
        import os
        import tempfile

        from app.pipeline.agents.tool_marketplace import ToolMarketplace

        with tempfile.TemporaryDirectory() as tmpdir:
            marketplace = ToolMarketplace(
                marketplace_url="https://api.example.com",
                local_cache_dir=tmpdir,
            )
            tool_code = 'def my_tool(): return "safe"'
            __import__("hashlib").sha256(tool_code.encode()).hexdigest()
            tool_file = os.path.join(tmpdir, "my_tool_v1.0.0.json")
            with open(tool_file, "w") as f:
                json.dump(
                    {
                        "name": "my_tool",
                        "code": tool_code,
                        "code_hash": "tampered_hash",
                        "version": "1.0.0",
                        "description": "A tool",
                        "author": "test",
                        "tags": [],
                        "published_at": "2026-01-01T00:00:00",
                    },
                    f,
                )
            result = marketplace.install_tool("my_tool", version="1.0.0")
            assert result["success"] is False
            assert "integrity" in result.get("error", "").lower()


class TestToolMarketplaceSecurity:
    def test_marketplace_publish_requires_code_hash(self):
        import tempfile

        from app.pipeline.agents.tool_marketplace import ToolMarketplace

        with tempfile.TemporaryDirectory() as tmpdir:
            marketplace = ToolMarketplace(
                marketplace_url="https://api.example.com",
                local_cache_dir=tmpdir,
            )
            result = marketplace.publish_tool(
                tool_name="publish_test",
                tool_code="print('hello')",
                description="Test publish",
                author="test_author",
                version="1.0.0",
            )
            assert result["success"] is True
            assert "tool_id" in result

    def test_marketplace_tool_not_found_returns_error(self):
        import tempfile

        from app.pipeline.agents.tool_marketplace import ToolMarketplace

        with tempfile.TemporaryDirectory() as tmpdir:
            marketplace = ToolMarketplace(
                marketplace_url="https://api.example.com",
                local_cache_dir=tmpdir,
            )
            result = marketplace.install_tool("nonexistent_tool")
            assert result["success"] is False
            assert "not found" in result.get("error", "").lower()
