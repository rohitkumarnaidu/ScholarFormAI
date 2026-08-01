# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import patch



class TestToolMarketplace:
    def test_init_creates_cache_dir(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path / "tm"))
        assert tm.cache_dir.exists()
        assert tm.installed_tools == {}

    def test_publish_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.publish_tool("my_tool", "print('hello')", "A test tool", "author1")
        assert result["success"] is True
        assert (tmp_path / "my_tool_v1.0.0.json").exists()

    def test_publish_tool_exception(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm2 = ToolMarketplace(local_cache_dir=str(tmp_path / "broken"))
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = tm2.publish_tool("t", "code", "desc", "a")
            assert result["success"] is False

    def test_search_tools_by_query(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("alpha_tool", "c1", "Alpha desc", "a1", tags=["nlp"])
        tm.publish_tool("beta_tool", "c2", "Beta desc", "a2", tags=["cv"])
        alpha = tm.search_tools(query="alpha")
        assert len(alpha) == 1
        assert alpha[0]["name"] == "alpha_tool"
        both = tm.search_tools(query="tool")
        assert len(both) == 2

    def test_search_tools_by_tags(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("t1", "c", "d", "a", tags=["nlp", "text"])
        tm.publish_tool("t2", "c", "d", "a", tags=["cv"])
        results = tm.search_tools(tags=["nlp"])
        assert len(results) == 1
        assert results[0]["name"] == "t1"

    def test_search_tools_limit(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        for i in range(5):
            tm.publish_tool(f"t{i}", "c", "d", "a")
        results = tm.search_tools(limit=3)
        assert len(results) == 3

    def test_install_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("my_tool", "print('hi')", "desc", "author")
        result = tm.install_tool("my_tool")
        assert result["success"] is True
        assert "my_tool" in tm.installed_tools

    def test_install_tool_not_found(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        result = tm.install_tool("nonexistent")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_install_tool_integrity_fail(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.publish_tool("my_tool", "code", "desc", "author")
        # Tamper with published file
        tool_file = tmp_path / "my_tool_v1.0.0.json"
        data = json.loads(tool_file.read_text())
        data["code_hash"] = "tampered"
        tool_file.write_text(json.dumps(data))
        result = tm.install_tool("my_tool")
        assert result["success"] is False

    def test_uninstall_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.installed_tools["my_tool"] = {"version": "1.0"}
        assert tm.uninstall_tool("my_tool") is True
        assert "my_tool" not in tm.installed_tools

    def test_uninstall_tool_not_installed(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        assert tm.uninstall_tool("missing") is False

    def test_get_installed_tools(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        tm.installed_tools["t1"] = {"version": "1.0", "installed_at": "now", "description": "desc"}
        tools = tm.get_installed_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "t1"

    def test_rate_tool(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        assert tm.rate_tool("my_tool", 5) is True

    def test_get_tool_stats(self, tmp_path):
        from app.pipeline.agents.tool_marketplace import ToolMarketplace
        tm = ToolMarketplace(local_cache_dir=str(tmp_path))
        stats = tm.get_tool_stats("my_tool")
        assert stats["name"] == "my_tool"
