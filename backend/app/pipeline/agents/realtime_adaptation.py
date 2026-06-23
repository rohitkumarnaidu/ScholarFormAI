# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Real-time adaptation during processing.
"""
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Hard limits for adaptive parameters
_MIN_TIMEOUT = 10.0
_MAX_TIMEOUT = 1800.0
_MAX_ERRORS_BEFORE_STOP = 5


class RealTimeAdaptiveAgent:
    """
    Agent that adapts its strategy in real-time during processing.

    Features:
    - Monitor performance metrics live
    - Adjust strategy mid-processing
    - Dynamic timeout adjustment
    - Adaptive tool selection
    """

    def __init__(
        self,
        base_timeout: float = 60.0,
        adaptation_callback: Optional[Callable] = None,
    ):
        """
        Initialize real-time adaptive agent.

        Args:
            base_timeout: Base timeout in seconds (clamped to [10, 1800])
            adaptation_callback: Optional callback for adaptation events
        """
        if base_timeout <= 0:
            raise ValueError(f"base_timeout must be positive, got {base_timeout}")
        self.base_timeout = float(max(_MIN_TIMEOUT, min(_MAX_TIMEOUT, base_timeout)))
        self.adaptation_callback = adaptation_callback

        # Real-time metrics
        self.current_metrics: Dict[str, Any] = {
            "start_time": None,
            "elapsed_time": 0.0,
            "tools_executed": [],
            "errors_encountered": [],
            "current_strategy": "default",
        }

        # Adaptive parameters
        self.params: Dict[str, Any] = {
            "timeout": self.base_timeout,
            "retry_enabled": True,
            "tool_priority": [],
            "aggressive_mode": False,
        }

    def start_processing(self, document_id: str) -> None:
        """
        Start processing a document.

        Args:
            document_id: Document ID (non-empty string)
        """
        if not document_id:
            logger.warning("start_processing called with empty document_id.")
        self.current_metrics = {
            "document_id": str(document_id),
            "start_time": time.time(),
            "elapsed_time": 0.0,
            "tools_executed": [],
            "errors_encountered": [],
            "current_strategy": "default",
        }
        # Reset adaptive params for new document
        self.params = {
            "timeout": self.base_timeout,
            "retry_enabled": True,
            "tool_priority": [],
            "aggressive_mode": False,
        }
        logger.info("Started real-time adaptive processing for '%s'", document_id)

    def record_tool_execution(
        self,
        tool_name: str,
        duration: float,
        success: bool,
    ) -> None:
        """
        Record tool execution and adapt if needed.

        Args:
            tool_name: Name of executed tool
            duration: Execution duration in seconds
            success: Whether execution succeeded
        """
        if not tool_name:
            logger.warning("record_tool_execution called with empty tool_name; skipping.")
            return

        try:
            self.current_metrics["tools_executed"].append(
                {
                    "tool": tool_name,
                    "duration": float(duration),
                    "success": bool(success),
                    "timestamp": time.time(),
                }
            )

            if not success:
                self.current_metrics["errors_encountered"].append(
                    {
                        "tool": tool_name,
                        "timestamp": time.time(),
                    }
                )

            # Update elapsed time
            start = self.current_metrics.get("start_time")
            if start is not None:
                self.current_metrics["elapsed_time"] = time.time() - start

            # Trigger adaptation
            self._adapt_realtime()

        except Exception as exc:
            logger.error("Error in record_tool_execution('%s'): %s", tool_name, exc)

    def _adapt_realtime(self) -> None:
        """Adapt strategy based on current metrics. Never raises."""
        try:
            elapsed = float(self.current_metrics.get("elapsed_time", 0.0))
            error_count = len(self.current_metrics.get("errors_encountered", []))
            tools_executed = self.current_metrics.get("tools_executed", [])
            tool_count = len(tools_executed)
            current_timeout = float(self.params.get("timeout", self.base_timeout))

            # Adaptation 1: Timeout adjustment
            if elapsed > current_timeout * 0.7:
                if not self.params.get("aggressive_mode", False):
                    self.params["aggressive_mode"] = True
                    new_timeout = min(current_timeout * 1.5, _MAX_TIMEOUT)
                    self.params["timeout"] = new_timeout
                    self._notify_adaptation(
                        "timeout_extended",
                        {"new_timeout": new_timeout, "reason": "approaching_timeout"},
                    )

            # Adaptation 2: Error handling
            if error_count >= 2:
                if self.current_metrics.get("current_strategy") != "fallback":
                    self.current_metrics["current_strategy"] = "fallback"
                    self.params["retry_enabled"] = False
                    self._notify_adaptation(
                        "strategy_changed",
                        {"new_strategy": "fallback", "reason": "multiple_errors"},
                    )

            # Adaptation 3: Tool selection
            if tool_count > 0 and not self.params.get("tool_priority"):
                successful_tools: List[str] = [
                    t["tool"]
                    for t in tools_executed
                    if isinstance(t, dict) and t.get("success")
                ]
                if successful_tools:
                    self.params["tool_priority"] = successful_tools
                    self._notify_adaptation(
                        "tool_priority_set", {"priority": successful_tools}
                    )

        except Exception as exc:
            logger.error("Error in _adapt_realtime: %s", exc)

    def _notify_adaptation(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify about adaptation event. Never raises."""
        try:
            logger.info("Real-time adaptation: %s - %s", event_type, data)
            if callable(self.adaptation_callback):
                self.adaptation_callback(event_type, data)
        except Exception as exc:
            logger.error("Error in adaptation callback for event '%s': %s", event_type, exc)

    def should_continue(self) -> bool:
        """
        Check if processing should continue.

        Returns:
            True if should continue, False if timeout or too many errors
        """
        try:
            elapsed = float(self.current_metrics.get("elapsed_time", 0.0))
            timeout = float(self.params.get("timeout", self.base_timeout))
            error_count = len(self.current_metrics.get("errors_encountered", []))

            if elapsed > timeout:
                logger.warning(
                    "Timeout exceeded (%.1fs > %.1fs); stopping.", elapsed, timeout
                )
                return False

            if error_count > _MAX_ERRORS_BEFORE_STOP:
                logger.warning(
                    "Too many errors (%d > %d); stopping.",
                    error_count,
                    _MAX_ERRORS_BEFORE_STOP,
                )
                return False

            return True
        except Exception as exc:
            logger.error("Error in should_continue: %s", exc)
            return False

    def get_current_params(self) -> Dict[str, Any]:
        """Get a copy of the current adaptive parameters."""
        try:
            return dict(self.params)
        except Exception as exc:
            logger.error("Error in get_current_params: %s", exc)
            return {}

    def get_metrics(self) -> Dict[str, Any]:
        """Get a copy of the current metrics."""
        try:
            return dict(self.current_metrics)
        except Exception as exc:
            logger.error("Error in get_metrics: %s", exc)
            return {}

    def recommend_next_tool(self, available_tools: List[str]) -> Optional[str]:
        """
        Recommend next tool to execute.

        Args:
            available_tools: List of available tool names

        Returns:
            Recommended tool name, or None if no tools available
        """
        if not available_tools:
            return None
        try:
            priority = self.params.get("tool_priority", [])
            if priority:
                for tool in priority:
                    if tool in available_tools:
                        return tool
            return available_tools[0]
        except Exception as exc:
            logger.error("Error in recommend_next_tool: %s", exc)
            return available_tools[0] if available_tools else None
