# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Custom tool creation framework for user-defined tools.
"""

import sys
import logging
from typing import Type, Dict, Any, Optional, Callable, List
from pydantic import BaseModel, Field, create_model

if sys.version_info < (3, 14):
    try:
        from langchain.tools import BaseTool as _LangChainBaseTool
    except Exception:
        _LangChainBaseTool = object
else:
    _LangChainBaseTool = object
BaseTool = _LangChainBaseTool if isinstance(_LangChainBaseTool, type) else object

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for custom user-defined tools.
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Type[BaseTool]] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, tuple],  # {field_name: (type, description)}
        execute_fn: Callable[[Dict[str, Any]], str],
    ) -> Type[BaseTool]:
        """
        Register a custom tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: Input schema as {field_name: (type, description)}
            execute_fn: Function to execute the tool

        Returns:
            Created tool class
        """
        # Create Pydantic model for input
        fields = {}
        for field_name, (field_type, field_desc) in input_schema.items():
            fields[field_name] = (field_type, Field(description=field_desc))

        InputModel = create_model(f"{name}Input", **fields)

        base_tool_class = BaseTool if isinstance(BaseTool, type) else object

        # Create tool class
        class CustomTool(base_tool_class):
            name: str = ""
            description: str = ""
            args_schema: Type[BaseModel] = InputModel

            def _run(self, **kwargs) -> str:
                """Execute the tool."""
                try:
                    return execute_fn(kwargs)
                except Exception as e:
                    return f"ERROR: Tool execution failed: {str(e)}"

            async def _arun(self, **kwargs) -> str:
                """Async execution not supported."""
                raise NotImplementedError("Async execution not supported")

        CustomTool.name = name
        CustomTool.description = description

        # Register tool
        self.tools[name] = CustomTool
        logger.info(f"Registered custom tool: {name}")

        return CustomTool

    def get_tool(self, name: str) -> Optional[Type[BaseTool]]:
        """Get a registered tool."""
        return self.tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return list(self.tools.keys())

    def create_instance(self, name: str) -> Optional[BaseTool]:
        """Create an instance of a registered tool."""
        tool_class = self.get_tool(name)
        if tool_class:
            return tool_class()
        return None


# Global registry
_global_registry = ToolRegistry()


def register_custom_tool(
    name: str, description: str, input_schema: Dict[str, tuple], execute_fn: Callable[[Dict[str, Any]], str]
) -> Type[BaseTool]:
    """
    Register a custom tool globally.

    Example:
        def my_tool_fn(inputs):
            query = inputs["query"]
            return f"Processed: {query}"

        register_custom_tool(
            name="my_custom_tool",
            description="Does something custom",
            input_schema={
                "query": (str, "The query to process")
            },
            execute_fn=my_tool_fn
        )

    Args:
        name: Tool name
        description: Tool description
        input_schema: Input schema
        execute_fn: Execution function

    Returns:
        Created tool class
    """
    return _global_registry.register(name, description, input_schema, execute_fn)


def get_custom_tool(name: str) -> Optional[BaseTool]:
    """Get a custom tool instance."""
    return _global_registry.create_instance(name)


def list_custom_tools() -> List[str]:
    """List all custom tools."""
    return _global_registry.list_tools()


# Example custom tools


def create_citation_formatter_tool():
    """Create a citation formatting tool."""

    def format_citation(inputs: Dict[str, Any]) -> str:
        """Format a citation in various styles."""
        authors = inputs.get("authors", [])
        title = inputs.get("title", "")
        year = inputs.get("year", "")
        style = inputs.get("style", "apa")

        if style == "apa":
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += ", et al."
            return f"{author_str} ({year}). {title}."
        elif style == "mla":
            if authors:
                return f'{authors[0]}. "{title}." {year}.'
            return f'"{title}." {year}.'
        else:
            return f"{', '.join(authors)}. {title}. {year}."

    return register_custom_tool(
        name="format_citation",
        description="Format a citation in APA, MLA, or Chicago style",
        input_schema={
            "authors": (list, "List of author names"),
            "title": (str, "Paper title"),
            "year": (str, "Publication year"),
            "style": (str, "Citation style (apa, mla, chicago)"),
        },
        execute_fn=format_citation,
    )


def create_keyword_extractor_tool():
    """Create a keyword extraction tool."""

    def extract_keywords(inputs: Dict[str, Any]) -> str:
        """Extract keywords from text."""
        text = inputs.get("text", "")
        max_keywords = inputs.get("max_keywords", 5)

        # Simple keyword extraction (in practice, use NLP)
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only longer words
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, _ in sorted_words[:max_keywords]]

        import json

        return json.dumps({"keywords": keywords})

    return register_custom_tool(
        name="extract_keywords",
        description="Extract keywords from text",
        input_schema={
            "text": (str, "Text to extract keywords from"),
            "max_keywords": (int, "Maximum number of keywords to extract"),
        },
        execute_fn=extract_keywords,
    )
