# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Streaming callback handler for real-time agent updates.
"""

import logging
import sys
from collections.abc import Callable
from typing import Any

if sys.version_info < (3, 14):
    try:
        from langchain_core.agents import AgentAction, AgentFinish
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.outputs import LLMResult
    except Exception:
        BaseCallbackHandler = object  # type: ignore[assignment]
        AgentAction = Any  # type: ignore[assignment]
        AgentFinish = Any  # type: ignore[assignment]
        LLMResult = Any  # type: ignore[assignment]
else:
    BaseCallbackHandler = object  # type: ignore[assignment]
    AgentAction = Any  # type: ignore[assignment]
    AgentFinish = Any  # type: ignore[assignment]
    LLMResult = Any  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class StreamingAgentCallback(BaseCallbackHandler):
    """
    Callback handler for streaming agent decisions and tool executions.

    Provides real-time updates on:
    - LLM thinking process
    - Tool invocations
    - Agent decisions
    - Final results
    """

    def __init__(self, callback_fn: Callable | None = None):
        """
        Initialize streaming callback.

        Args:
            callback_fn: Optional function to call with updates
                        Signature: callback_fn(event_type: str, data: Dict)
        """
        self.callback_fn = callback_fn or self._default_callback
        self.events = []

    def _default_callback(self, event_type: str, data: dict):
        """Default callback that logs events."""
        logger.info(f"[{event_type}] {data}")
        self.events.append({"type": event_type, "data": data})

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Called when LLM starts."""
        self.callback_fn("llm_start", {"message": "Agent is thinking...", "prompt_count": len(prompts)})

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends."""
        self.callback_fn("llm_end", {"message": "Agent decision made", "generations": len(response.generations)})

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM errors."""
        self.callback_fn("llm_error", {"message": "LLM error occurred", "error": str(error)})

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when tool starts."""
        tool_name = serialized.get("name", "unknown")
        self.callback_fn(
            "tool_start",
            {
                "message": f"Executing tool: {tool_name}",
                "tool": tool_name,
                "input": input_str[:100],  # Truncate for display
            },
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when tool ends."""
        self.callback_fn(
            "tool_end",
            {
                "message": "Tool execution complete",
                "output_preview": output[:200],  # Truncate for display
            },
        )

    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when tool errors."""
        self.callback_fn("tool_error", {"message": "Tool execution failed", "error": str(error)})

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Called when agent takes an action."""
        self.callback_fn(
            "agent_action",
            {
                "message": f"Agent action: {action.tool}",
                "tool": action.tool,
                "tool_input": str(action.tool_input)[:100],
                "log": action.log[:200] if action.log else "",
            },
        )

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Called when agent finishes."""
        self.callback_fn(
            "agent_finish", {"message": "Agent processing complete", "output": str(finish.return_values)[:200]}
        )

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        """Called when chain starts."""
        self.callback_fn(
            "chain_start", {"message": "Starting processing chain", "chain": serialized.get("name", "unknown")}
        )

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Called when chain ends."""
        self.callback_fn("chain_end", {"message": "Processing chain complete"})

    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when chain errors."""
        self.callback_fn("chain_error", {"message": "Processing chain error", "error": str(error)})

    def get_events(self) -> list[dict]:
        """Get all recorded events."""
        return self.events

    def clear_events(self):
        """Clear recorded events."""
        self.events = []
