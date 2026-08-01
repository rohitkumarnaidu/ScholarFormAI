# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import patch
import pytest
pytestmark = [pytest.mark.pipeline]


# =============================================================================
# ToolRegistry (custom_tools.py)
# =============================================================================

class TestToolRegistry:
    def test_init(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.tools == {}

    def test_register(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def my_fn(inputs):
            return f"Result: {inputs['x']}"
        tool_cls = r.register(
            name="my_tool",
            description="My custom tool",
            input_schema={"x": (str, "Input param")},
            execute_fn=my_fn
        )
        assert "my_tool" in r.tools
        assert tool_cls.name == "my_tool"
        assert tool_cls.description == "My custom tool"

    def test_register_and_execute(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def my_fn(inputs):
            return f"Got: {inputs['x']}"
        tool_cls = r.register("exec_tool", "Exec test", {"x": (str, "input")}, my_fn)
        instance = tool_cls()
        result = instance._run(x="hello")
        assert result == "Got: hello"

    def test_register_execution_error(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        def broken_fn(inputs):
            raise ValueError("broken")
        tool_cls = r.register("broken_tool", "Broken", {"x": (str, "in")}, broken_fn)
        instance = tool_cls()
        result = instance._run(x="test")
        assert result.startswith("ERROR:")

    def test_register_async_raises(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        tool_cls = r.register("async_tool", "Async", {"x": (str, "in")}, lambda i: "ok")
        instance = tool_cls()
        import pytest
        with pytest.raises(NotImplementedError):
            import asyncio
            asyncio.run(instance._arun(x="test"))

    def test_get_tool(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        r.register("tool_a", "desc", {"p": (str, "param")}, lambda i: "ok")
        cls = r.get_tool("tool_a")
        assert cls is not None
        assert cls.description == "desc"

    def test_get_tool_not_found(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.get_tool("nonexistent") is None

    def test_list_tools(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        r.register("t1", "d1", {"p": (str, "p")}, lambda i: "ok")
        r.register("t2", "d2", {"p": (str, "p")}, lambda i: "ok")
        tools = r.list_tools()
        assert "t1" in tools
        assert "t2" in tools

    def test_list_tools_empty(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.list_tools() == []

    def test_create_instance(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        r.register("inst_tool", "desc", {"x": (str, "x")}, lambda i: "ok")
        instance = r.create_instance("inst_tool")
        assert instance is not None
        assert instance._run(x="test") == "ok"

    def test_create_instance_not_found(self):
        from app.pipeline.agents.custom_tools import ToolRegistry
        r = ToolRegistry()
        assert r.create_instance("missing") is None


# =============================================================================
# Global functions (custom_tools.py)
# =============================================================================

class TestGlobalCustomTools:
    def test_register_custom_tool(self):
        from app.pipeline.agents.custom_tools import register_custom_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = register_custom_tool(
            name="global_tool", description="Global tool",
            input_schema={"q": (str, "query")},
            execute_fn=lambda i: f"res: {i['q']}"
        )
        assert "global_tool" in _global_registry.tools
        result = tool_cls()._run(q="hello")
        assert result == "res: hello"

    def test_get_custom_tool(self):
        from app.pipeline.agents.custom_tools import get_custom_tool, register_custom_tool, _global_registry
        _global_registry.tools.clear()
        register_custom_tool("get_test", "desc", {"x": (str, "x")}, lambda i: "ok")
        instance = get_custom_tool("get_test")
        assert instance is not None

    def test_get_custom_tool_not_found(self):
        from app.pipeline.agents.custom_tools import get_custom_tool
        instance = get_custom_tool("no_such_tool")
        assert instance is None

    def test_list_custom_tools(self):
        from app.pipeline.agents.custom_tools import list_custom_tools, register_custom_tool, _global_registry
        _global_registry.tools.clear()
        register_custom_tool("list_test", "desc", {"x": (str, "x")}, lambda i: "ok")
        tools = list_custom_tools()
        assert "list_test" in tools

    def test_list_custom_tools_empty(self):
        from app.pipeline.agents.custom_tools import list_custom_tools, _global_registry
        _global_registry.tools.clear()
        assert list_custom_tools() == []

    def test_create_citation_formatter_tool_apa(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_citation_formatter_tool()
        instance = tool_cls()
        result = instance._run(authors=["Smith, J.", "Doe, A.", "Lee, B.", "Kim, C."],
                               title="Test Paper", year="2024", style="apa")
        assert "Smith, J., Doe, A., Lee, B., et al." in result
        assert "2024" in result

    def test_create_citation_formatter_tool_mla(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_citation_formatter_tool()
        instance = tool_cls()
        result = instance._run(authors=["Smith, J."], title="Test Paper", year="2024", style="mla")
        assert "Smith, J." in result
        assert '"Test Paper."' in result or '"Test Paper"' in result

    def test_create_citation_formatter_tool_chicago(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_citation_formatter_tool()
        instance = tool_cls()
        result = instance._run(authors=["Smith, J.", "Doe, A."], title="Test Paper", year="2024", style="chicago")
        assert "Smith, J., Doe, A." in result

    def test_create_citation_formatter_tool_no_authors(self):
        from app.pipeline.agents.custom_tools import create_citation_formatter_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_citation_formatter_tool()
        instance = tool_cls()
        result = instance._run(authors=[], title="Test", year="2024", style="mla")
        assert '"Test."' in result

    def test_create_keyword_extractor_tool(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_keyword_extractor_tool()
        instance = tool_cls()
        result = instance._run(text="machine learning and deep learning are both very important", max_keywords=3)
        data = json.loads(result)
        assert "keywords" in data
        assert len(data["keywords"]) <= 3

    def test_create_keyword_extractor_tool_empty_text(self):
        from app.pipeline.agents.custom_tools import create_keyword_extractor_tool, _global_registry
        _global_registry.tools.clear()
        tool_cls = create_keyword_extractor_tool()
        instance = tool_cls()
        result = instance._run(text="", max_keywords=5)
        data = json.loads(result)
        assert data["keywords"] == []


# =============================================================================
# ToolMarketplace (tool_marketplace.py)
# =============================================================================

class TestToolMarketplace:
    def test_init(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        assert tm.cache_dir == tmp_path
        assert tm.installed_tools == {}

    def test_init_loads_existing(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        (tmp_path / "installed_tools.json").write_text(
            json.dumps({"tool_a": {"version": "1.0.0", "installed_at": "2026-01-01", "code": "", "description": ""}})
        )
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        assert "tool_a" in tm.installed_tools
        assert tm.installed_tools["tool_a"]["version"] == "1.0.0"

    def test_publish_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.publish_tool(
            tool_name="my_tool", tool_code="def run(): pass",
            description="My tool", author="test_user", version="1.0.0",
            tags=["nlp", "formatting"]
        )
        assert result["success"] is True
        assert result["tool_id"] == "my_tool_v1.0.0"
        tool_file = tmp_path / "my_tool_v1.0.0.json"
        assert tool_file.exists()

    def test_publish_tool_no_tags(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.publish_tool(
            tool_name="simple_tool", tool_code="print(1)",
            description="Simple", author="u", version="0.0.1"
        )
        assert result["success"] is True

    def test_publish_tool_failure(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        from unittest.mock import patch
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        with patch("builtins.open", side_effect=OSError("write error")):
            result = tm.publish_tool("fail_tool", "code", "desc", "author")
            assert result["success"] is False

    def test_search_tools_no_results(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        results = tm.search_tools()
        assert results == []

    def test_search_tools_with_results(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("search_tool", "code", "A searchable tool", "author", tags=["test"])
        results = tm.search_tools()
        assert len(results) == 1
        assert results[0]["name"] == "search_tool"

    def test_search_tools_by_query(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("alpha_tool", "code1", "Alpha tool", "author", tags=["a"])
        tm.publish_tool("beta_tool", "code2", "Beta tool", "author", tags=["b"])
        results = tm.search_tools(query="alpha")
        assert len(results) == 1
        assert results[0]["name"] == "alpha_tool"

    def test_search_tools_by_tags(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("tagged_tool", "code", "Tagged", "author", tags=["nlp"])
        tm.publish_tool("other_tool", "code", "Other", "author", tags=["other"])
        results = tm.search_tools(tags=["nlp"])
        assert len(results) == 1
        assert results[0]["name"] == "tagged_tool"

    def test_search_tools_skips_installed_json(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        (tmp_path / "installed_tools.json").write_text(json.dumps({"dummy": "data"}))
        tm.publish_tool("real_tool", "code", "Real", "author")
        results = tm.search_tools()
        names = [r["name"] for r in results]
        assert "real_tool" in names
        assert "installed_tools" not in str(results)

    def test_search_tools_skips_bad_file(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        (tmp_path / "corrupt.json").write_text("not json")
        tm.publish_tool("good_tool", "code", "Good", "author")
        results = tm.search_tools()
        assert len(results) == 1

    def test_install_tool_no_version(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("install_test", "code_data", "Install test", "author", version="2.0.0")
        result = tm.install_tool("install_test")
        assert result["success"] is True
        assert "install_test" in tm.installed_tools
        assert tm.installed_tools["install_test"]["version"] == "2.0.0"

    def test_install_tool_with_version(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("ver_test", "code", "Version test", "author", version="1.0.0")
        tm.publish_tool("ver_test", "code_v2", "Version test v2", "author", version="2.0.0")
        result = tm.install_tool("ver_test", version="1.0.0")
        assert result["success"] is True

    def test_install_tool_not_found(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.install_tool("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_install_tool_version_not_found(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("some_tool", "code", "desc", "author", version="1.0.0")
        result = tm.install_tool("some_tool", version="9.9.9")
        assert result["success"] is False

    def test_install_tool_integrity_fail(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("integrity_test", "original_code", "desc", "author")
        # Corrupt the file after publishing
        tm._save_installed_tools()
        # Read and corrupt the tool file
        tool_file = tmp_path / "integrity_test_v1.0.0.json"
        data = json.loads(tool_file.read_text())
        data["code_hash"] = "corrupted_hash"
        tool_file.write_text(json.dumps(data))
        result = tm.install_tool("integrity_test")
        assert result["success"] is False
        assert "integrity" in result["error"]

    def test_install_tool_exception(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("exception_tool", "code", "desc", "author")
        with patch("builtins.open", side_effect=[OSError("io error")]):
            result = tm.install_tool("exception_tool", version="1.0.0")
            assert result["success"] is False

    def test_uninstall_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("uninstall_test", "code", "desc", "author")
        tm.install_tool("uninstall_test")
        assert "uninstall_test" in tm.installed_tools
        result = tm.uninstall_tool("uninstall_test")
        assert result is True
        assert "uninstall_test" not in tm.installed_tools

    def test_uninstall_tool_not_found(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.uninstall_tool("not_installed")
        assert result is False

    def test_get_installed_tools_empty(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        assert tm.get_installed_tools() == []

    def test_get_installed_tools(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("listed_tool", "code", "Listed tool", "author")
        tm.install_tool("listed_tool")
        tools = tm.get_installed_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "listed_tool"
        assert tools[0]["version"] == "1.0.0"

    def test_rate_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.rate_tool("some_tool", rating=5, review="Great!")
        assert result is True

    def test_rate_tool_without_review(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.rate_tool("some_tool", rating=3)
        assert result is True

    def test_get_tool_stats(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        stats = tm.get_tool_stats("my_tool")
        assert stats["name"] == "my_tool"
        assert stats["total_installs"] == 0
        assert stats["average_rating"] == 0.0
        assert stats["review_count"] == 0
