# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tool marketplace for community tool sharing.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import hashlib

logger = logging.getLogger(__name__)


class ToolMarketplace:
    """
    Marketplace for sharing and discovering custom tools.

    Features:
    - Publish tools to community
    - Discover and install community tools
    - Version management
    - Rating and reviews
    - Security verification
    """

    def __init__(
        self, marketplace_url: str = "https://api.toolmarketplace.ai", local_cache_dir: str = ".tool_marketplace"
    ):
        """
        Initialize tool marketplace.

        Args:
            marketplace_url: Marketplace API URL
            local_cache_dir: Local cache directory
        """
        self.marketplace_url = marketplace_url
        self.cache_dir = Path(local_cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.installed_tools_file = self.cache_dir / "installed_tools.json"
        self.installed_tools = self._load_installed_tools()

    def _load_installed_tools(self) -> Dict[str, Any]:
        """Load installed tools registry."""
        if self.installed_tools_file.exists():
            with open(self.installed_tools_file, "r") as f:
                return json.load(f)
        return {}

    def _save_installed_tools(self):
        """Save installed tools registry."""
        with open(self.installed_tools_file, "w") as f:
            json.dump(self.installed_tools, f, indent=2)

    def publish_tool(
        self,
        tool_name: str,
        tool_code: str,
        description: str,
        author: str,
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Publish a tool to the marketplace.

        Args:
            tool_name: Tool name
            tool_code: Tool source code
            description: Tool description
            author: Author name
            version: Tool version
            tags: Optional tags

        Returns:
            Publication result
        """
        # Compute hash for integrity
        code_hash = hashlib.sha256(tool_code.encode()).hexdigest()

        tool_package = {
            "name": tool_name,
            "code": tool_code,
            "description": description,
            "author": author,
            "version": version,
            "tags": tags or [],
            "code_hash": code_hash,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # In production, would POST to marketplace API
            # For now, save locally
            tool_file = self.cache_dir / f"{tool_name}_v{version}.json"
            with open(tool_file, "w") as f:
                json.dump(tool_package, f, indent=2)

            logger.info(f"Published tool: {tool_name} v{version}")

            return {"success": True, "tool_id": f"{tool_name}_v{version}", "message": "Tool published successfully"}

        except Exception as e:
            logger.error(f"Failed to publish tool: {e}")
            return {"success": False, "error": str(e)}

    def search_tools(
        self, query: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for tools in the marketplace.

        Args:
            query: Search query
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of matching tools
        """
        # In production, would query marketplace API
        # For now, search local cache
        results = []

        for tool_file in self.cache_dir.glob("*.json"):
            if tool_file.name == "installed_tools.json":
                continue

            try:
                with open(tool_file, "r") as f:
                    tool = json.load(f)

                # Apply filters
                if query and query.lower() not in tool["name"].lower():
                    continue

                if tags and not any(t in tool.get("tags", []) for t in tags):
                    continue

                results.append(
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "author": tool["author"],
                        "version": tool["version"],
                        "tags": tool.get("tags", []),
                        "published_at": tool.get("published_at"),
                    }
                )

                if len(results) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Failed to read tool file {tool_file}: {e}")
                continue

        return results

    def install_tool(self, tool_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Install a tool from the marketplace.

        Args:
            tool_name: Tool name
            version: Optional specific version

        Returns:
            Installation result
        """
        # Find tool
        if version:
            tool_file = self.cache_dir / f"{tool_name}_v{version}.json"
        else:
            # Find latest version
            tool_files = list(self.cache_dir.glob(f"{tool_name}_v*.json"))
            if not tool_files:
                return {"success": False, "error": f"Tool {tool_name} not found"}
            tool_file = sorted(tool_files)[-1]  # Latest version

        if not tool_file.exists():
            return {"success": False, "error": f"Tool {tool_name} version {version} not found"}

        try:
            with open(tool_file, "r") as f:
                tool = json.load(f)

            # Verify integrity
            code_hash = hashlib.sha256(tool["code"].encode()).hexdigest()
            if code_hash != tool["code_hash"]:
                return {"success": False, "error": "Tool integrity check failed"}

            # Install (save to installed registry)
            self.installed_tools[tool_name] = {
                "version": tool["version"],
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "code": tool["code"],
                "description": tool["description"],
            }

            self._save_installed_tools()

            logger.info(f"Installed tool: {tool_name} v{tool['version']}")

            return {
                "success": True,
                "tool_name": tool_name,
                "version": tool["version"],
                "message": "Tool installed successfully",
            }

        except Exception as e:
            logger.error(f"Failed to install tool: {e}")
            return {"success": False, "error": str(e)}

    def uninstall_tool(self, tool_name: str) -> bool:
        """
        Uninstall a tool.

        Args:
            tool_name: Tool name

        Returns:
            True if successful
        """
        if tool_name in self.installed_tools:
            del self.installed_tools[tool_name]
            self._save_installed_tools()
            logger.info(f"Uninstalled tool: {tool_name}")
            return True
        return False

    def get_installed_tools(self) -> List[Dict[str, Any]]:
        """Get list of installed tools."""
        return [
            {
                "name": name,
                "version": info["version"],
                "installed_at": info["installed_at"],
                "description": info.get("description", ""),
            }
            for name, info in self.installed_tools.items()
        ]

    def rate_tool(self, tool_name: str, rating: int, review: Optional[str] = None) -> bool:
        """
        Rate a tool.

        Args:
            tool_name: Tool name
            rating: Rating (1-5)
            review: Optional review text

        Returns:
            True if successful
        """
        # In production, would POST to marketplace API
        logger.info(f"Rated tool {tool_name}: {rating}/5")
        return True

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """
        Get tool statistics.

        Args:
            tool_name: Tool name

        Returns:
            Tool statistics
        """
        # In production, would query marketplace API
        return {"name": tool_name, "total_installs": 0, "average_rating": 0.0, "review_count": 0}
